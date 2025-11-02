"""Python-based real time audio stem server.

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
from typing import Dict, Optional

import numpy as np
import pyaudio
import soundfile as sf
from pythonosc import dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer


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

            self.audio_data = audio_data
            self.sample_rate = sample_rate
            self.frames = len(audio_data)
            self.channels = audio_data.shape[1]
            self.loaded = True

            memory_mb = (self.frames * self.channels * 4) / (1024 * 1024)
            print(f"✅ Loaded {self.name} ({memory_mb:.1f} MB)")

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
    """Main audio server class managing audio playback and OSC interface."""

    def __init__(self, osc_port: int = 57120, audio_device: Optional[int] = None):
        self.osc_port = osc_port
        self.sample_rate = 44100
        self.chunk_size = 256
        self.channels = 2

        self.buffers: Dict[int, AudioBuffer] = {}
        self.active_players: Dict[int, StemPlayer] = {}

        self.deck_a_volume = 0.8
        self.deck_b_volume = 0.0
        self.master_volume = 0.8

        self.clock = TempoClock()

        self.pa = pyaudio.PyAudio()
        self.audio_device = audio_device
        self.stream: Optional[pyaudio.Stream] = None
        self.running = False

        self.osc_server: Optional[ThreadingOSCUDPServer] = None

        print("🎛️💾 PYTHON AUDIO SERVER INITIALIZING 💾🎛️")
        self.setup_audio()
        self.setup_osc()

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
            try:
                deck_a_mix = np.zeros((self.chunk_size, 2), dtype=np.float32)
                deck_b_mix = np.zeros((self.chunk_size, 2), dtype=np.float32)

                for buffer_id, player in list(self.active_players.items()):
                    if player.playing:
                        try:
                            chunk = player.get_audio_chunk(self.chunk_size)
                            if buffer_id < 1100:
                                deck_a_mix += chunk
                            else:
                                deck_b_mix += chunk
                        except Exception as exc:  # pragma: no cover - runtime diagnostic
                            print(f"⚠️  Error in player {buffer_id}: {exc}")
                            player.playing = False

                final_mix = (
                    deck_a_mix * self.deck_a_volume + deck_b_mix * self.deck_b_volume
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

        disp.map("/load_buffer", self.osc_load_buffer)
        disp.map("/play_stem", self.osc_play_stem)
        disp.map("/stop_stem", self.osc_stop_stem)
        disp.map("/stem_volume", self.osc_stem_volume)
        disp.map("/crossfade_levels", self.osc_crossfade_levels)
        disp.map("/get_status", self.osc_get_status)
        disp.map("/test_tone", self.osc_test_tone)
        disp.map("/mixer_cleanup", self.osc_mixer_cleanup)
        disp.map("/set_tempo", self.osc_set_tempo)

        self.osc_server = ThreadingOSCUDPServer(("localhost", self.osc_port), disp)
        print(f"🔌 OSC server listening on port {self.osc_port}")

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
            print(f"Deck A: {self.deck_a_volume:.2f}, Deck B: {self.deck_b_volume:.2f}")
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
        description="Python Audio Server - SuperCollider replacement"
    )
    parser.add_argument("--port", type=int, default=57120, help="OSC port (default: 57120)")
    parser.add_argument("--device", type=int, help="Audio device ID")
    parser.add_argument("--bpm", type=float, default=120.0, help="Initial tempo in BPM")

    args = parser.parse_args()

    server = PythonAudioServer(osc_port=args.port, audio_device=args.device)
    server.clock.bpm = args.bpm
    server_thread = server.start()

    if server_thread:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            server.stop()


if __name__ == "__main__":
    main()
