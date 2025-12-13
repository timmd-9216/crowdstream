"""Python-based real time audio stem server.

# TEST COMMENT: edit connection verified

This module exposes an OSC controllable audio engine that loads stems
into memory and mixes them into two virtual decks that can be crossfaded.

It is designed as a lightweight replacement for a SuperCollider setup the
project previously relied on.  The implementation focuses on determinism
and real-time safe sections where possible while still remaining within a
pure Python environment.
"""

from __future__ import annotations

import argparse
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Any, Tuple

import numpy as np
import pyaudio
import soundfile as sf
from pythonosc import dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer


# --- Lightweight 3-band deck filter ---
class _ThreeBand:
    """Very lightweight 3‑band (low/mid/high) per‑deck tone filter.
    Low = one‑pole low‑pass @ 200 Hz, High = one‑pole high‑pass @ 2000 Hz,
    Mid = residual (x - low - high). Gains are linear 0..1 (or higher if desired).
    This keeps minimal state per channel and runs fast on 256‑sample chunks.
    """

    def __init__(self, sample_rate: int, low_hz: float = 200.0, high_hz: float = 2000.0):
        self.fs = float(sample_rate)
        # one‑pole coefficients
        self._alp_low = np.exp(-2.0 * np.pi * low_hz / self.fs)
        self._alp_high = np.exp(-2.0 * np.pi * high_hz / self.fs)
        # state per channel
        self._lp_prev = np.zeros(2, dtype=np.float32)
        self._hp_prev = np.zeros(2, dtype=np.float32)
        self._x_prev = np.zeros(2, dtype=np.float32)
        # user gains
        self.low_gain = 1.0
        self.mid_gain = 1.0
        self.high_gain = 1.0

    def set_gain(self, band: str, value: float) -> None:
        b = (band or "").strip().lower()
        v = float(value)
        if b.startswith("lo"):
            self.low_gain = v
        elif b.startswith("mi"):
            self.mid_gain = v
        elif b.startswith("hi"):
            self.high_gain = v
        else:
            raise ValueError(f"Unknown band '{band}' (expected 'low'|'mid'|'high')")

    def process(self, x: np.ndarray) -> np.ndarray:
        if x.size == 0:
            return x
        out = np.empty_like(x)
        # copy states locally for speed
        lp_prev = self._lp_prev.astype(np.float32)
        hp_prev = self._hp_prev.astype(np.float32)
        x_prev = self._x_prev.astype(np.float32)
        a_lp = float(self._alp_low)
        a_hp = float(self._alp_high)
        lg = float(self.low_gain)
        mg = float(self.mid_gain)
        hg = float(self.high_gain)
        # sample‑wise update per channel (256 frames per buffer; cheap)
        for n in range(x.shape[0]):
            xnL = x[n, 0]
            xnR = x[n, 1]
            # low‑pass yL[n] = (1-a)*x + a*yL[n-1]
            lpL = (1.0 - a_lp) * xnL + a_lp * lp_prev[0]
            lpR = (1.0 - a_lp) * xnR + a_lp * lp_prev[1]
            # high‑pass yH[n] = a*(yH[n-1] + x - x[n-1])
            hpL = a_hp * (hp_prev[0] + xnL - x_prev[0])
            hpR = a_hp * (hp_prev[1] + xnR - x_prev[1])
            midL = xnL - lpL - hpL
            midR = xnR - lpR - hpR
            out[n, 0] = lg * lpL + mg * midL + hg * hpL
            out[n, 1] = lg * lpR + mg * midR + hg * hpR
            # update state
            lp_prev[0] = lpL; lp_prev[1] = lpR
            hp_prev[0] = hpL; hp_prev[1] = hpR
            x_prev[0] = xnL; x_prev[1] = xnR
        # write back
        self._lp_prev[:] = lp_prev
        self._hp_prev[:] = hp_prev
        self._x_prev[:] = x_prev
        return out


class TempoClock:
    """High precision clock used to keep stems in sync."""

    def __init__(self, bpm: float = 120.0):
        self._bpm = bpm
        self._start_time = time.perf_counter()
        self._lock = threading.RLock()

    @property
    def bpm(self) -> float:
        with self._lock:
            return self._bpm

    @bpm.setter
    def bpm(self, value: float) -> None:
        if value <= 0:
            raise ValueError("Tempo must be positive")
        with self._lock:
            self._bpm = value
            self._start_time = time.perf_counter()

    def reset(self) -> None:
        with self._lock:
            self._start_time = time.perf_counter()

    def beat_position(self) -> float:
        with self._lock:
            elapsed = time.perf_counter() - self._start_time
            return elapsed * (self._bpm / 60.0)


class AudioBuffer:
    """Represents an audio buffer with playback capabilities."""

    def __init__(self, file_path: str | Path, buffer_id: int, name: str = ""):
        self.buffer_id = buffer_id
        self.name = name or Path(file_path).stem
        self.file_path = str(file_path)
        self.audio_data: Optional[np.ndarray] = None
        self.sample_rate: int = 44100
        self.channels: int = 2
        self.frames: int = 0
        self.loaded = False

        self.load_audio()

    def load_audio(self) -> None:
        """Load audio file into memory."""
        try:
            audio_data, sample_rate = sf.read(self.file_path, dtype=np.float32)

            if audio_data.ndim == 1:
                audio_data = np.column_stack((audio_data, audio_data))
            elif audio_data.shape[1] == 1:
                audio_data = np.tile(audio_data, (1, 2))

            # --- Ensure buffer matches engine sample rate (prevents pitch/time stretch) ---
            target_sr = 44100
            if sample_rate != target_sr:
                try:
                    # Linear resample per channel
                    n_src = audio_data.shape[0]
                    n_dst = int(round(n_src * target_sr / sample_rate))
                    x_src = np.linspace(0.0, n_src - 1, num=n_src, endpoint=True, dtype=np.float64)
                    x_dst = np.linspace(0.0, n_src - 1, num=n_dst, endpoint=True, dtype=np.float64)
                    resampled = np.empty((n_dst, 2), dtype=np.float32)
                    # channel 0
                    resampled[:, 0] = np.interp(x_dst, x_src, audio_data[:, 0]).astype(np.float32)
                    # channel 1
                    resampled[:, 1] = np.interp(x_dst, x_src, audio_data[:, 1]).astype(np.float32)
                    audio_data = resampled
                    sample_rate = target_sr
                    print(f"↻ Resampled '{self.name}' {n_src}@{self.sample_rate}→{n_dst}@{target_sr}")
                except Exception as _res_exc:
                    print(f"⚠️  Resample failed ({_res_exc}); continuing with original rate {sample_rate} Hz")

            self.audio_data = audio_data
            self.sample_rate = sample_rate
            self.frames = len(audio_data)
            self.channels = audio_data.shape[1]
            self.loaded = True

            memory_mb = (self.frames * self.channels * 4) / (1024 * 1024)
            print(f"✅ Loaded {self.name} ({memory_mb:.1f} MB) @ {self.sample_rate} Hz")

        except Exception as exc:  # pragma: no cover - runtime diagnostic
            print(f"❌ Load failed: {self.name} - {exc}")
            self.loaded = False


class StemPlayer:
    """Individual stem player with rate, volume, and position control."""

    def __init__(
        self,
        buffer: AudioBuffer,
        rate: float = 1.0,
        volume: float = 0.8,
        start_pos: float = 0.0,
        loop: bool = True,
    ):
        self.buffer = buffer
        self.rate = rate
        self.volume = volume
        self.loop = loop
        self.playing = False
        self.position = int(start_pos * buffer.frames) if buffer.loaded else 0
        self.original_position = self.position

    def get_audio_chunk(self, chunk_size: int) -> np.ndarray:
        """Retrieve next audio chunk for playback respecting playback rate."""
        if not self.buffer.loaded or not self.playing or self.buffer.audio_data is None:
            # Detailed debug when returning silence
            if self.buffer.loaded and self.playing and self.buffer.audio_data is None:
                print(f"⚠️  Buffer {self.buffer.buffer_id} loaded but audio_data is None!")
            return np.zeros((chunk_size, 2), dtype=np.float32)

        output = np.zeros((chunk_size, 2), dtype=np.float32)
        samples_needed = chunk_size
        output_pos = 0

        # Pre-calculate rate increments for vectorised slicing.
        rate = max(self.rate, 0.01)

        while samples_needed > 0 and self.playing:
            available = self.buffer.frames - self.position
            if available <= 0:
                if self.loop:
                    # Log loop wrap for debugging: end -> start
                    try:
                        print(f"🔁 Loop wrap: {self.buffer.name} (buffer {self.buffer.buffer_id}) end {self.buffer.frames} → start 0")
                    except Exception:
                        pass
                    self.position = 0
                    available = self.buffer.frames
                else:
                    break

            step = min(samples_needed, int(available / rate) or available)
            if step <= 0:
                break

            end_pos = self.position + int(step * rate)
            indices = np.linspace(self.position, end_pos, step, endpoint=False)
            indices = indices.astype(np.int64).clip(0, self.buffer.frames - 1)
            audio_chunk = self.buffer.audio_data[indices]
            audio_chunk *= self.volume

            output[output_pos : output_pos + step] = audio_chunk
            self.position = end_pos
            output_pos += step
            samples_needed -= step

        return output


class PythonAudioServer:
    def _print_all_messages(self, address: str, *args: object) -> None:
        """Print every OSC message received (for debugging)."""
        try:
            print(f"📡 OSC MESSAGE: {address} {args}")
        except Exception as exc:
            print(f"❌ Error printing OSC message: {exc}")
    """Main audio server class managing audio playback and OSC interface."""
    # Buffer ID ranges by deck:
    #   A:  100–1099
    #   B: 1100–2099
    #   C: 2100–3099
    #   D: 3100–4099

    def __init__(self, osc_port: int = 57120, audio_device: Optional[int] = None):
        self.osc_port = osc_port
        self.sample_rate = 44100
        self.chunk_size = 256
        self.channels = 2

        self.buffers: Dict[int, AudioBuffer] = {}
        self.active_players: Dict[int, StemPlayer] = {}

        self.deck_a_volume = 1.0
        self.deck_b_volume = 1.0
        self.deck_c_volume = 1.0
        self.deck_d_volume = 1.0
        self.master_volume = 0.8

        # Per‑deck 3‑band tone filters (low/mid/high)
        self._filters: Dict[str, _ThreeBand] = {
            'A': _ThreeBand(self.sample_rate),
            'B': _ThreeBand(self.sample_rate),
            'C': _ThreeBand(self.sample_rate),
            'D': _ThreeBand(self.sample_rate),
        }

        self.clock = TempoClock()
        # Meter / clock print configuration
        self.meter_beats = 4  # beats per bar (e.g., 4 for 4/4)
        self.print_clock = False
        self._last_printed_whole_beat = None

        # Wall-clock reference (seconds since server start)
        self._t0 = time.perf_counter()

        # Track first actual start times per deck (server-relative seconds)
        self._deck_actual_start: Dict[str, float] = {}

        # Armed (cued) decks ready to start together
        self._armed: Dict[str, int] = {}

        # DJ EQ feel: depth of cut at 0% (in dB)
        self._eq_max_cut_db = 24.0

        self.pa = pyaudio.PyAudio()
        self.audio_device = audio_device
        self.stream: Optional[pyaudio.Stream] = None
        self.running = False

        self.osc_server: Optional[ThreadingOSCUDPServer] = None

        print("🎛️💾 PYTHON AUDIO SERVER INITIALIZING 💾🎛️")
        self.setup_audio()
        self.setup_osc()

    def _now(self) -> float:
        """Seconds since server start (perf_counter-based)."""
        return time.perf_counter() - self._t0

    def setup_audio(self) -> None:
        """Initialise PyAudio stream."""
        try:
            stream_kwargs = dict(
                format=pyaudio.paFloat32,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.chunk_size,
            )
            if self.audio_device is not None:
                stream_kwargs["output_device_index"] = self.audio_device

            self.stream = self.pa.open(**stream_kwargs)
            print(f"🔊 Audio stream opened: {self.sample_rate}Hz, {self.chunk_size} samples")
            self.running = True

            self.audio_thread = threading.Thread(target=self.audio_loop, daemon=True)
            self.audio_thread.start()
        except Exception as exc:  # pragma: no cover - runtime diagnostic
            print(f"❌ Failed to open audio stream: {exc}")

    def audio_loop(self) -> None:
        """Audio processing loop that mixes all active players."""
        while self.running:
            # --- Beat-based watch printing (reference unit for control) ---
            try:
                if self.print_clock:
                    beat_pos = self.clock.beat_position()  # continuous beats since start
                    whole_beat = int(beat_pos)
                    if whole_beat != self._last_printed_whole_beat:
                        self._last_printed_whole_beat = whole_beat
                        bar_index = (whole_beat // self.meter_beats) + 1  # 1-based
                        beat_in_bar = (whole_beat % self.meter_beats) + 1  # 1..meter_beats
                        bar_phase = (beat_pos / self.meter_beats) % 1.0  # 0..1 within bar
                        beat_phase = beat_pos % 1.0  # 0..1 within current beat
                        # This line is the "watch": deterministic units for mapping controls
                        print(f"⏱ bar={bar_index} beat={beat_in_bar} bar_phase={bar_phase:.3f} beat_phase={beat_phase:.3f} bpm={self.clock.bpm:.2f}")
            except Exception:
                pass
            try:
                deck_a_mix = np.zeros((self.chunk_size, 2), dtype=np.float32)
                deck_b_mix = np.zeros((self.chunk_size, 2), dtype=np.float32)
                deck_c_mix = np.zeros((self.chunk_size, 2), dtype=np.float32)
                deck_d_mix = np.zeros((self.chunk_size, 2), dtype=np.float32)

                for buffer_id, player in list(self.active_players.items()):
                    if player.playing:
                        try:
                            chunk = player.get_audio_chunk(self.chunk_size)
                            if 100 <= buffer_id < 1100:
                                deck_a_mix += chunk
                            elif 1100 <= buffer_id < 2100:
                                deck_b_mix += chunk
                            elif 2100 <= buffer_id < 3100:
                                deck_c_mix += chunk
                            else:
                                deck_d_mix += chunk
                        except Exception as exc:  # pragma: no cover - runtime diagnostic
                            print(f"⚠️  Error in player {buffer_id}: {exc}")
                            player.playing = False
                # Apply per‑deck 3‑band filters before deck volume and master
                try:
                    deck_a_mix = self._filters['A'].process(deck_a_mix)
                    deck_b_mix = self._filters['B'].process(deck_b_mix)
                    deck_c_mix = self._filters['C'].process(deck_c_mix)
                    deck_d_mix = self._filters['D'].process(deck_d_mix)
                except Exception as _fexc:
                    print(f"⚠️  Filter process error: {_fexc}")

                final_mix = (
                    deck_a_mix * self.deck_a_volume +
                    deck_b_mix * self.deck_b_volume +
                    deck_c_mix * self.deck_c_volume +
                    deck_d_mix * self.deck_d_volume
                ) * self.master_volume
                final_mix = np.tanh(final_mix * 0.9) * 0.9

                if self.stream and self.stream.is_active():
                    self.stream.write(final_mix.astype(np.float32).tobytes())

                time.sleep(0.001)
            except Exception as exc:  # pragma: no cover - runtime diagnostic
                print(f"❌ Audio loop error: {exc}")
                time.sleep(0.1)

    def setup_osc(self) -> None:
        """Setup OSC server mirroring the SuperCollider API."""
        disp = dispatcher.Dispatcher()
        disp.set_default_handler(self._print_all_messages)

        disp.map("/load_buffer", self.osc_load_buffer)
        disp.map("/play_stem", self.osc_play_stem)
        disp.map("/stop_stem", self.osc_stop_stem)
        disp.map("/stem_volume", self.osc_stem_volume)
        disp.map("/crossfade_levels", self.osc_crossfade_levels)
        disp.map("/deck_levels", self.osc_deck_levels)      # /deck_levels [volA, volB, volC, volD]
        disp.map("/deck_filter", self.osc_deck_filter)   # /deck_filter deck band value
        disp.map("/deck_eq", self.osc_deck_eq)           # /deck_eq deck band percent(0..100)
        disp.map("/deck_eq_all", self.osc_deck_eq_all)   # /deck_eq_all deck low mid high (percents)
        disp.map("/get_status", self.osc_get_status)
        disp.map("/test_tone", self.osc_test_tone)
        disp.map("/mixer_cleanup", self.osc_mixer_cleanup)
        disp.map("/set_tempo", self.osc_set_tempo)
        disp.map("/set_meter", self.osc_set_meter)          # /set_meter [beats_per_bar]
        disp.map("/print_clock", self.osc_print_clock)      # /print_clock [0|1]
        disp.map("/dummy", self.osc_dummy)
        disp.map("/schedule_c_at", self.osc_schedule_c_at)  # /schedule_c_at [abs_seconds_from_start]
        # Minimal “dummy DJ” API for timed control relative to server t0
        disp.map("/reset", self.osc_reset)               # /reset -> set t0 = now
        disp.map("/play", self.osc_play)                 # /play deck path start_at
        disp.map("/fade", self.osc_fade)                 # /fade deck start_at [duration]

        disp.map("/cue", self.osc_cue)                   # /cue deck path [start_pos]
        disp.map("/start_group", self.osc_start_group)   # /start_group start_at deck1 deck2 ...

        # Start OSC server - try IPv6 first, then IPv4
        # self.osc_server = ThreadingOSCUDPServer(("127.0.0.1", self.osc_port), disp)
        self.osc_server = ThreadingOSCUDPServer(("0.0.0.0", self.osc_port), disp)
        print(f"🔌 OSC server listening on port {self.osc_port}")

    def _deck_to_range(self, deck: str) -> Tuple[int, int]:
        deck = (deck or "").strip().upper()
        if deck == "A":
            return (100, 1100)
        if deck == "B":
            return (1100, 2100)
        if deck == "C":
            return (2100, 3100)
        if deck == "D":
            return (3100, 4100)
        raise ValueError(f"Unknown deck '{deck}'")

    def _deck_label_from_buffer_id(self, buffer_id: int) -> Optional[str]:
        if 100 <= buffer_id < 1100:
            return "A"
        if 1100 <= buffer_id < 2100:
            return "B"
        if 2100 <= buffer_id < 3100:
            return "C"
        if 3100 <= buffer_id < 4100:
            return "D"
        return None

    def _deck_volume_get_set(self, deck: str, new_val: Optional[float] = None) -> float:
        d = (deck or "").strip().upper()
        if d == "A":
            if new_val is not None:
                self.deck_a_volume = float(new_val)
            return self.deck_a_volume
        if d == "B":
            if new_val is not None:
                self.deck_b_volume = float(new_val)
            return self.deck_b_volume
        if d == "C":
            if new_val is not None:
                self.deck_c_volume = float(new_val)
            return self.deck_c_volume
        if d == "D":
            if new_val is not None:
                self.deck_d_volume = float(new_val)
            return self.deck_d_volume
        raise ValueError(f"Unknown deck '{deck}'")

    def _load_if_needed(self, buffer_id: int, path: str, name: str) -> None:
        # Load (or reload) buffer if not present or pointing to a different file
        buf = self.buffers.get(buffer_id)
        if buf is None or Path(getattr(buf, "file_path", "")) != Path(path):
            if buf is not None and buffer_id in self.active_players:
                try:
                    self.active_players[buffer_id].playing = False
                    del self.active_players[buffer_id]
                except Exception:
                    pass
            self.osc_load_buffer("/load_buffer", buffer_id, path, name)

    def _schedule_at(self, abs_time: float, fn: Any) -> None:
        delay = max(0.0, abs_time - self._now())
        threading.Timer(delay, fn).start()

    def osc_reset(self, address: str, *args: object) -> None:
        """Set server time-zero to 'now' for relative scheduling."""
        self._t0 = time.perf_counter()
        self.clock.reset()
        print("⏱️  /reset -> t0 set to 0.0 (relative clock reset)")

    def osc_play(self, address: str, *args: object) -> None:
        """/play deck path start_at  (start_at is seconds relative to t0)"""
        try:
            deck = str(args[0])
            path = str(args[1])
            start_at = float(args[2])
            lo, hi = self._deck_to_range(deck)
            buffer_id = lo  # choose base id per deck
            name = f"Deck{deck.upper()}"
            self._load_if_needed(buffer_id, path, name)
            # Convert relative to absolute using internal t0 reference
            abs_time = (time.perf_counter() - self._t0) + start_at
            def _start():
                self.osc_play_stem("/play_stem", buffer_id, 1.0, 0.8, 1, 0.0)
                print(f"▶️  /play {deck.upper()} TRIGGER @ rel={start_at:.3f}s (abs={self._now():.6f}s) → {Path(path).name}")
            self._schedule_at(abs_time, _start)
            print(f"🗓️  queued /play {deck} @ {start_at:.3f}s (abs={abs_time:.3f}s) — tip: use /cue + /start_group for sample-tight starts")
        except Exception as exc:
            print(f"❌ Error in /play: {exc}")

    def osc_cue(self, address: str, *args: object) -> None:
        """Cue (load + arm) a deck without starting playback.
        Usage: /cue deck path [start_pos]
        """
        try:
            deck = str(args[0]).strip().upper()
            path = str(args[1])
            start_pos = float(args[2]) if len(args) > 2 else 0.0
            lo, hi = self._deck_to_range(deck)
            buffer_id = lo
            name = f"Deck{deck}"
            print(f"🔍 /cue {deck} → loading buffer_id={buffer_id}, path={path}")
            self._load_if_needed(buffer_id, path, name)
            # Create/replace a non‑playing player at desired start_pos
            buf = self.buffers.get(buffer_id)
            if buf is None:
                print(f"❌ /cue {deck} failed: buffer {buffer_id} not in self.buffers after load")
                return
            if not buf.loaded:
                print(f"❌ /cue {deck} failed: buffer {buffer_id} loaded=False")
                return
            player = StemPlayer(buf, rate=1.0, volume=0.8, start_pos=start_pos, loop=True)
            player.playing = False
            self.active_players[buffer_id] = player
            self._armed[deck] = buffer_id
            print(f"🧷 Cued {deck} → {Path(path).name} @pos {start_pos:.3f} (buffer {buffer_id})")
            print(f"   📋 self._armed now: {self._armed}")
            print(f"   📋 self.active_players keys: {list(self.active_players.keys())}")
        except Exception as exc:
            print(f"❌ Error in /cue: {exc}")
            import traceback
            traceback.print_exc()

    def osc_start_group(self, address: str, *args: object) -> None:
        """Start multiple cued decks at the same time (single callback).
        Usage: /start_group start_at deck1 deck2 ...   (start_at is seconds relative to t0)
        Also accepts: /start_group deck1 deck2 ... start_at
        """
        try:
            if not args or len(args) < 2:
                raise ValueError("need start_at and at least one deck")
            # Flexible parsing: detect the float among args
            start_at = None
            decks: list[str] = []
            for a in args:
                try:
                    v = float(a)
                    start_at = v
                except Exception:
                    decks.append(str(a).strip().upper())
            if start_at is None:
                raise ValueError("missing start_at")
            if not decks:
                raise ValueError("no decks provided")
            abs_time = (time.perf_counter() - self._t0) + float(start_at)

            def _start_all():
                t_call = self._now()
                print(f"🔍 _start_all callback firing at t={t_call:.6f}s")
                print(f"   📋 self._armed: {self._armed}")
                print(f"   📋 self.active_players: {list(self.active_players.keys())}")
                for d in decks:
                    if d not in ("A","B","C","D"):
                        print(f"⚠️  Unknown deck '{d}' in /start_group")
                        continue
                    # Resolve buffer id: prefer armed, else base deck id with existing player
                    bid = self._armed.get(d)
                    print(f"🔍 Deck {d}: bid from _armed = {bid}")
                    if bid is None:
                        lo, hi = self._deck_to_range(d)
                        print(f"🔍 Deck {d}: searching active_players in range [{lo}, {hi})")
                        # pick existing active player in range if present
                        for cand in range(lo, hi):
                            if cand in self.active_players:
                                bid = cand
                                print(f"🔍 Deck {d}: found active player at buffer {bid}")
                                break
                    if bid is None:
                        print(f"❌ Deck {d} not armed and no active player")
                        print(f"   📋 _armed keys: {list(self._armed.keys())}")
                        print(f"   📋 active_players keys: {list(self.active_players.keys())}")
                        continue
                    pl = self.active_players.get(bid)
                    if pl is None:
                        print(f"❌ No player for deck {d} (buffer {bid})")
                        print(f"   📋 active_players: {list(self.active_players.keys())}")
                        continue
                    # Reset to cued position and flip playing on
                    # (avoid race if already playing)
                    pl.playing = True
                    self._deck_actual_start[d] = t_call
                    print(f"🎬 Group START Deck {d} @ t={t_call:.6f}s (buffer {bid})")
                # If A & B are in the set, print their delta
                if 'A' in self._deck_actual_start and 'B' in self._deck_actual_start:
                    d_ms = (self._deck_actual_start['B'] - self._deck_actual_start['A']) * 1000.0
                    print(f"⏱️  Group A↔B start delta: {d_ms:+.2f} ms (B - A)")

            self._schedule_at(abs_time, _start_all)
            print(f"🗓️  queued /start_group {decks} @ {float(start_at):.3f}s (abs={abs_time:.3f}s)")
        except Exception as exc:
            print(f"❌ Error in /start_group: {exc}")
            import traceback
            traceback.print_exc()

    def osc_fade(self, address: str, *args: object) -> None:
        """/fade deck start_at [duration] — linear ramp deck volume to 0 over duration."""
        try:
            deck = str(args[0])
            start_at = float(args[1])
            duration = float(args[2]) if len(args) > 2 else 2.0
            start_abs = (time.perf_counter() - self._t0) + start_at

            def _ramp():
                try:
                    v0 = self._deck_volume_get_set(deck)
                    steps = max(1, int(duration * 20))  # 20 Hz ramp
                    if duration <= 0:
                        self._deck_volume_get_set(deck, 0.0)
                        print(f"🎚️  /fade {deck} immediate -> 0.00")
                        return
                    for i in range(steps):
                        t = (i + 1) / steps
                        v = (1.0 - t) * v0
                        self._deck_volume_get_set(deck, v)
                        time.sleep(duration / steps)
                    self._deck_volume_get_set(deck, 0.0)
                    print(f"🎚️  /fade {deck} done (dur {duration:.2f}s)")
                except Exception as e:
                    print(f"❌ fade ramp error: {e}")

            self._schedule_at(start_abs, _ramp)
            print(f"🗓️  queued /fade {deck} @ {start_at:.3f}s (dur {duration:.2f}s)")
        except Exception as exc:
            print(f"❌ Error in /fade: {exc}")

    def osc_deck_levels(self, address: str, *args: object) -> None:
        """Set per-deck levels independently - /deck_levels [volA, volB, volC, volD]."""
        try:
            a = float(args[0]) if len(args) > 0 else self.deck_a_volume
            b = float(args[1]) if len(args) > 1 else self.deck_b_volume
            c = float(args[2]) if len(args) > 2 else self.deck_c_volume
            d = float(args[3]) if len(args) > 3 else self.deck_d_volume
            self.deck_a_volume, self.deck_b_volume, self.deck_c_volume, self.deck_d_volume = a, b, c, d
            print(f"🎚️  Deck levels → A:{a:.2f} B:{b:.2f} C:{c:.2f} D:{d:.2f}")
        except Exception as exc:
            print(f"❌ Error setting deck levels: {exc}")

    def osc_deck_filter(self, address: str, *args: object) -> None:
        """Set per‑deck tone control band: /deck_filter deck band value
        deck ∈ {A,B,C,D}, band ∈ {low, mid, high}, value is linear gain (0..1 typical).
        """
        try:
            deck = str(args[0]).strip().upper()
            band = str(args[1]).strip().lower()
            value = float(args[2])
            if deck not in self._filters:
                raise ValueError(f"Unknown deck '{deck}'")
            # clamp value defensively
            if not np.isfinite(value):
                value = 0.0
            value = max(0.0, float(value))
            self._filters[deck].set_gain(band, value)
            # Diagnostic: clarify value is linear gain (not percent)
            print(f"🎛️  /deck_filter {deck} {band} -> {value:.3f} (linear gain; if you meant percent, use /deck_eq)")
        except Exception as exc:
            print(f"❌ Error in /deck_filter: {exc}")

    def _cut_only_gain_from_percent(self, percent: float, max_cut_db: float = 24.0) -> float:
        """Map 0..100% knob (DJ style) to linear gain with CUT ONLY behavior.
        50% = 0 dB (flat), 0% = HARD KILL (0.0 gain), (0,50]% maps to −max_cut_db..0 dB.
        Values >50% are treated as flat (no boost yet).
        """
        try:
            p = float(percent)
        except Exception:
            p = 50.0
        if not np.isfinite(p):
            p = 50.0
        # Hard kill at 0%
        if p <= 0.0:
            return 0.0
        # Flat for >=50%
        if p >= 50.0:
            return 1.0
        # normalize 0..50 → (0,1]
        x = max(0.0, min(50.0, p)) / 50.0
        # Map x∈(0,1] to dB∈[−max_cut_db, 0]
        db = (x - 1.0) * float(max_cut_db)
        return float(10.0 ** (db / 20.0))

    def osc_deck_eq(self, address: str, *args: object) -> None:
        """DJ-style EQ control (cut-only for now): /deck_eq deck band percent
        deck∈{A,B,C,D}; band∈{low,mid,high}; percent 0..100 with 50=flat, 0=deep cut.
        Values above 50 are treated as flat (no boost yet).
        """
        try:
            deck = str(args[0]).strip().upper()
            band = str(args[1]).strip().lower()
            percent = float(args[2])
            if deck not in self._filters:
                raise ValueError(f"Unknown deck '{deck}'")
            gain = self._cut_only_gain_from_percent(percent, self._eq_max_cut_db)
            self._filters[deck].set_gain(band, gain)
            print(f"🎛️  /deck_eq {deck} {band} {percent:.1f}% → gain {gain:.3f}")
        except Exception as exc:
            print(f"❌ Error in /deck_eq: {exc}")

    def osc_deck_eq_all(self, address: str, *args: object) -> None:
        """Set all three EQ bands for a deck at once (percents): /deck_eq_all deck low mid high
        Each value 0..100, with 50=flat; 0=hard kill; >50 treated as flat for now.
        """
        try:
            deck = str(args[0]).strip().upper()
            if deck not in self._filters:
                raise ValueError(f"Unknown deck '{deck}'")
            low_p = float(args[1])
            mid_p = float(args[2])
            high_p = float(args[3])
            lg = self._cut_only_gain_from_percent(low_p, self._eq_max_cut_db)
            mg = self._cut_only_gain_from_percent(mid_p, self._eq_max_cut_db)
            hg = self._cut_only_gain_from_percent(high_p, self._eq_max_cut_db)
            self._filters[deck].set_gain('low', lg)
            self._filters[deck].set_gain('mid', mg)
            self._filters[deck].set_gain('high', hg)
            print(f"🎛️  /deck_eq_all {deck} L:{low_p:.1f}%→{lg:.3f} M:{mid_p:.1f}%→{mg:.3f} H:{high_p:.1f}%→{hg:.3f}")
        except Exception as exc:
            print(f"❌ Error in /deck_eq_all: {exc}")

    def osc_dummy(self, address: str, *args: object) -> None:
        try:
            now = time.perf_counter()
            args_str = " ".join(map(str, args)) if args else "(no args)"
            print(f"📨 Dummy OSC received at {now:.3f}s | {args_str}")
            # Optional: interpret a simple command form to schedule C
            if args and str(args[0]).lower() == "schedule_c_at":
                x = float(args[1])
                self.osc_schedule_c_at("/schedule_c_at", x)
        except Exception as exc:
            print(f"❌ Error in /dummy: {exc}")

    def osc_schedule_c_at(self, address: str, *args: object) -> None:
        """Schedule Deck C (buffer 2100) to start at absolute time X (seconds since server start).
        Usage: /schedule_c_at [X]
        """
        try:
            if not args:
                raise ValueError("missing absolute time X")
            abs_x = float(args[0])
            now = self._now()
            delay = max(0.0, abs_x - now)
            if 2100 not in self.buffers:
                print("❌ Deck C (buffer 2100) not loaded; load it first.")
                return
            def _play():
                try:
                    self.osc_play_stem("", 2100, 1.0, 0.8, 1, 0.0)
                    print(f"⏩ Deck C started at t={self._now():.3f}s (scheduled for {abs_x:.3f}s)")
                except Exception as exc:
                    print(f"❌ Scheduled Deck C failed: {exc}")
            print(f"🗓️  Deck C will start at X={abs_x:.3f}s (now={now:.3f}s, delay={delay:.3f}s)")
            threading.Timer(delay, _play).start()
        except Exception as exc:
            print(f"❌ Error in /schedule_c_at: {exc}")
    def osc_set_meter(self, address: str, *args: object) -> None:
        """Set beats per bar for the clock watch - /set_meter [beats_per_bar]."""
        try:
            beats = int(args[0])
            if beats <= 0:
                raise ValueError("beats_per_bar must be positive")
            self.meter_beats = beats
            print(f"🧭 Meter set to {beats}/4 (beats per bar = {beats})")
        except Exception as exc:
            print(f"❌ Error setting meter: {exc}")

    def osc_print_clock(self, address: str, *args: object) -> None:
        """Enable/disable beat watch printing - /print_clock [0|1]."""
        try:
            flag = int(args[0]) if args else 1
            self.print_clock = bool(flag)
            state = 'ON' if self.print_clock else 'OFF'
            print(f"⏺  Clock watch printing {state}")
        except Exception as exc:
            print(f"❌ Error toggling clock printing: {exc}")

    def osc_load_buffer(self, address: str, *args: object) -> None:
        """Load audio buffer - /load_buffer [buffer_id, file_path, stem_name]."""
        try:
            buffer_id = int(args[0])
            file_path = Path(str(args[1]))
            stem_name = str(args[2]) if len(args) > 2 else file_path.stem

            if buffer_id in self.buffers:
                print(f"Freed buffer {buffer_id}")
                del self.buffers[buffer_id]

            if buffer_id in self.active_players:
                self.active_players[buffer_id].playing = False
                del self.active_players[buffer_id]

            if not file_path.exists():
                raise FileNotFoundError(file_path)

            self.buffers[buffer_id] = AudioBuffer(file_path, buffer_id, stem_name)
        except Exception as exc:  # pragma: no cover - runtime diagnostic
            print(f"❌ Error loading buffer: {exc}")

    def osc_play_stem(self, address: str, *args: object) -> None:
        """Play stem - /play_stem [buffer_id, rate, volume, loop, start_pos]."""
        try:
            buffer_id = int(args[0])
            rate = float(args[1]) if len(args) > 1 else 1.0
            volume = float(args[2]) if len(args) > 2 else 0.8
            loop = bool(int(args[3])) if len(args) > 3 else True
            start_pos = float(args[4]) if len(args) > 4 else 0.0

            if buffer_id not in self.buffers:
                print(f"❌ Buffer {buffer_id} not loaded")
                return

            buffer = self.buffers[buffer_id]
            if not buffer.loaded:
                print(f"❌ Buffer {buffer_id} not ready")
                return

            if buffer_id in self.active_players:
                self.active_players[buffer_id].playing = False

            player = StemPlayer(buffer, rate, volume, start_pos, loop)
            player.playing = True
            self.active_players[buffer_id] = player

            # Log actual deck start time and A↔B delta
            deck_lbl = self._deck_label_from_buffer_id(buffer_id)
            t_now = self._now()
            if deck_lbl:
                # Record/update the most recent start time for this deck
                self._deck_actual_start[deck_lbl] = t_now
                print(f"🎬 Deck {deck_lbl} START @ t={t_now:.6f}s")
                # If both A and B have started at least once, print delta (B - A)
                if 'A' in self._deck_actual_start and 'B' in self._deck_actual_start:
                    d_ms = (self._deck_actual_start['B'] - self._deck_actual_start['A']) * 1000.0
                    print(f"⏱️  A↔B start delta: {d_ms:+.2f} ms (B - A)")

            print(f"▶️  Playing buffer {buffer_id}, rate: {rate:.3f}")
        except Exception as exc:  # pragma: no cover - runtime diagnostic
            print(f"❌ Error playing stem: {exc}")

    def osc_stop_stem(self, address: str, *args: object) -> None:
        """Stop stem playback."""
        try:
            buffer_id = int(args[0])
            if buffer_id in self.active_players:
                self.active_players[buffer_id].playing = False
                del self.active_players[buffer_id]
                print(f"⏹️  Stopped {buffer_id}")
        except Exception as exc:  # pragma: no cover - runtime diagnostic
            print(f"❌ Error stopping stem: {exc}")

    def osc_stem_volume(self, address: str, *args: object) -> None:
        """Set stem volume."""
        try:
            buffer_id = int(args[0])
            volume = float(args[1])
            if buffer_id in self.active_players:
                self.active_players[buffer_id].volume = volume
        except Exception as exc:  # pragma: no cover - runtime diagnostic
            print(f"❌ Error setting volume: {exc}")

    def osc_crossfade_levels(self, address: str, *args: object) -> None:
        """Set crossfade levels - /crossfade_levels [deck_a_vol, deck_b_vol]."""
        try:
            self.deck_a_volume = float(args[0])
            self.deck_b_volume = float(args[1])
            print(f"🎚️  A:{self.deck_a_volume:.2f} B:{self.deck_b_volume:.2f}")
        except Exception as exc:  # pragma: no cover - runtime diagnostic
            print(f"❌ Error setting crossfade: {exc}")

    def osc_get_status(self, address: str, *args: object) -> None:
        """Log server status to stdout."""
        try:
            print("=== PYTHON AUDIO SERVER ===")
            print(f"Sample Rate: {self.sample_rate} Hz")
            print(f"Tempo: {self.clock.bpm:.1f} BPM")
            print(f"Beat Position: {self.clock.beat_position():.2f}")
            print(f"Buffers loaded: {len(self.buffers)}")
            active = len([p for p in self.active_players.values() if p.playing])
            print(f"Active players: {active}")
            print(f"Decks → A:{self.deck_a_volume:.2f} B:{self.deck_b_volume:.2f} C:{self.deck_c_volume:.2f} D:{self.deck_d_volume:.2f}")
        except Exception as exc:  # pragma: no cover - runtime diagnostic
            print(f"❌ Error getting status: {exc}")

    def osc_test_tone(self, address: str, *args: object) -> None:
        """Test tone (simplified - just acknowledgement)."""
        freq = args[0] if args else 440
        print(f"🎵 Test tone request: {freq} Hz")

    def osc_mixer_cleanup(self, address: str, *args: object) -> None:
        """Clean up all buffers and players."""
        try:
            for player in self.active_players.values():
                player.playing = False
            self.active_players.clear()
            self.buffers.clear()
            print("🧹 Cleaned")
        except Exception as exc:  # pragma: no cover - runtime diagnostic
            print(f"❌ Error cleaning up: {exc}")

    def osc_set_tempo(self, address: str, *args: object) -> None:
        """Adjust tempo of the internal clock - /set_tempo [bpm]."""
        try:
            bpm = float(args[0])
            self.clock.bpm = bpm
            print(f"⏱️  Tempo set to {bpm:.2f} BPM")
        except Exception as exc:  # pragma: no cover - runtime diagnostic
            print(f"❌ Error setting tempo: {exc}")

    def start(self) -> Optional[threading.Thread]:
        """Start the audio and OSC servers."""
        if self.stream and self.osc_server:
            self.stream.start_stream()
            print("🎛️💾 PYTHON AUDIO SERVER READY 💾🎛️")
            print(f"🔊 Audio: {self.sample_rate}Hz, {self.chunk_size} samples")
            print(f"🔌 OSC: localhost:{self.osc_port}")
            print("💡 Same OSC API as SuperCollider server")

            server_thread = threading.Thread(
                target=self.osc_server.serve_forever, daemon=True
            )
            server_thread.start()
            return server_thread

        print("❌ Failed to initialize audio server")
        return None

    def stop(self) -> None:
        """Stop the audio server and release resources."""
        self.running = False

        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:  # pragma: no cover - runtime diagnostic
                pass

        if self.osc_server:
            self.osc_server.shutdown()

        if self.pa:
            self.pa.terminate()

        print("👋 Python Audio Server stopped")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Python Audio Server - SuperCollider replacement (CLI v2)"
    )
    parser.add_argument("--cli-sentinel", action="store_true", help="Print CLI v2 sentinel and exit")
    parser.add_argument("--port", type=int, default=57120, help="OSC port (default: 57120)")
    parser.add_argument("--device", type=int, help="Audio device ID")
    parser.add_argument("--bpm", type=float, default=120.0, help="Initial tempo in BPM")
    parser.add_argument("--a", type=str, help="Path to audio file for Deck A (buffer 100)")
    parser.add_argument("--b", type=str, help="Path to audio file for Deck B (buffer 1100)")
    parser.add_argument("--rate", type=float, default=1.0, help="Playback rate for autoplay")
    parser.add_argument("--vol", type=float, default=0.8, help="Playback volume for autoplay")
    parser.add_argument("--ab", type=float, nargs=2, metavar=("A","B"), help="Crossfade levels for Deck A and Deck B (e.g., --ab 1.0 0.0)")
    parser.add_argument("--watch", action="store_true", help="Print beat-based watch (bar/beat/phase) once per beat")
    parser.add_argument("--meter", type=int, default=4, help="Beats per bar for the watch (default: 4)")
    # --- Dummy message simulation CLI flags ---
    parser.add_argument("--dummy_after", type=float, default=None, help="After N seconds, simulate receiving /dummy")
    parser.add_argument("--dummy_args", nargs="*", default=[], help="Optional args to include in the dummy message")
    parser.add_argument("--c", type=str, help="Path to audio file for Deck C (buffer 2100)")
    parser.add_argument("--c_at", type=float, default=None, help="Start Deck C after this many seconds (e.g., 8.0)")
    parser.add_argument("--c_preload", type=str, help="Preload Deck C file into buffer 2100 without starting")
    parser.add_argument("--d", type=str, help="Path to audio file for Deck D (buffer 3100)")
    parser.add_argument("--levels", type=float, nargs=4, metavar=("A","B","C","D"), help="Initial per-deck levels (e.g., --levels 1 1 1 1)")

    args = parser.parse_args()
    if args.cli_sentinel:
        print("✅ CLI v2 sentinel — this is the edited file being executed.")
        return

    server = PythonAudioServer(osc_port=args.port, audio_device=args.device)
    server.clock.bpm = args.bpm
    server.print_clock = bool(args.watch)
    server.meter_beats = int(args.meter) if args.meter and args.meter > 0 else 4
    server_thread = server.start()

    # Optionally simulate an incoming OSC message after a delay
    if args.dummy_after is not None:
        delay = max(0.0, float(args.dummy_after))
        def _fire_dummy():
            try:
                # Simulate as if an OSC client sent /dummy with args (strings)
                server.osc_dummy("/dummy", *args.dummy_args)
            except Exception as exc:
                print(f"❌ Dummy simulate failed: {exc}")
        print(f"🕒 Will simulate '/dummy' in {delay:.3f}s")
        threading.Timer(delay, _fire_dummy).start()

    # Optional: preload Deck C without starting
    if args.c_preload:
        try:
            server.osc_load_buffer("", 2100, args.c_preload, "DeckC")
            print(f"🗂️  Preloaded DeckC → {args.c_preload}")
        except Exception as exc:
            print(f"❌ Preload C failed: {exc}")

    # Optional quick autoplay from CLI
    if args.a or args.b or args.c or args.d or args.levels:
        # Set crossfade if provided
        if args.ab and len(args.ab) == 2:
            server.deck_a_volume = float(args.ab[0])
            server.deck_b_volume = float(args.ab[1])
            print(f"🎚️  Crossfade from CLI → A:{server.deck_a_volume:.2f} B:{server.deck_b_volume:.2f}")
        # Set initial per-deck levels if provided
        if args.levels and len(args.levels) == 4:
            server.deck_a_volume, server.deck_b_volume, server.deck_c_volume, server.deck_d_volume = [float(x) for x in args.levels]
            print(f"🎚️  Init levels → A:{server.deck_a_volume:.2f} B:{server.deck_b_volume:.2f} C:{server.deck_c_volume:.2f} D:{server.deck_d_volume:.2f}")
        # Load and play Deck A
        if args.a:
            try:
                server.osc_load_buffer("", 100, args.a, "DeckA")
                server.osc_play_stem("", 100, args.rate, args.vol, 1, 0.0)
            except Exception as exc:
                print(f"❌ Autoplay A failed: {exc}")
        # Load and play Deck B
        if args.b:
            try:
                server.osc_load_buffer("", 1100, args.b, "DeckB")
                server.osc_play_stem("", 1100, args.rate, args.vol, 1, 0.0)
            except Exception as exc:
                print(f"❌ Autoplay B failed: {exc}")
        # Load and (optionally) start Deck C relative to now
        if args.c:
            try:
                server.osc_load_buffer("", 2100, args.c, "DeckC")
                if args.c_at is not None:
                    # Start after N seconds from now
                    start_after = float(args.c_at)
                    def _start_c():
                        server.osc_play_stem("", 2100, args.rate, args.vol, 1, 0.0)
                        print("▶️  DeckC autoplay now")
                    print(f"🗓️  DeckC scheduled in +{start_after:.3f}s (relative)")
                    threading.Timer(start_after, _start_c).start()
                else:
                    print("ℹ️  DeckC loaded (not started); use /schedule_c_at X to start at absolute time.")
            except Exception as exc:
                print(f"❌ Autoplay C failed: {exc}")
        # Load and play Deck D
        if args.d:
            try:
                server.osc_load_buffer("", 3100, args.d, "DeckD")
                server.osc_play_stem("", 3100, args.rate, args.vol, 1, 0.0)
            except Exception as exc:
                print(f"❌ Autoplay D failed: {exc}")

    if server_thread:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            server.stop()


if __name__ == "__main__":
    main()
    def _print_all_messages(self, address: str, *args: object) -> None:
        """Print every OSC message received (for debugging)."""
        try:
            print(f"📡 OSC MESSAGE: {address} {args}")
        except Exception as exc:
            print(f"❌ Error printing OSC message: {exc}")