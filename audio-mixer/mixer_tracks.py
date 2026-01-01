# mixer.py
# Single-phase EQ move:
# Both decks play; B starts fully filtered (low/mid/high=0%);
# from beat 8 to beat 16, ramp B.low 0→50% while A.low 50→0%;
# final state: A plays mids/highs (low cut), B plays lows (mids/highs still cut).
#
# Timeline:
#   t = 0.00s: /play A (Pure Love)
#   t = 0.00s: /play B (Moth To A Flame – Adriatique Remix)
#   t = 3.90s .. 7.80s: Bass handoff (A.low 50→0, B.low 0→50); both decks audible
#
# Notes:
# - This sends /deck_eq <deck> <band> <value> (0..100). Your engine needs to handle it.
# - If /deck_eq is unhandled, messages are harmless no-ops.

from pythonosc.udp_client import SimpleUDPClient
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
import argparse, time, csv, random, wave, threading, socket
from collections import deque
from pathlib import Path

BPM_REF = 122.5  # Reference only; not used for playback timing.

# Single timing offset used everywhere: gives the engine time to preload before playback.
PRELOAD_OFFSET_SEC = 1.0

def _read_selected_csv(csv_path: str | Path) -> list[dict]:
    rows: list[dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if not row.get("part_file"):
                continue
            rows.append(row)
    return rows


def _pick_three_rows(rows: list[dict], seed: int | None = None) -> tuple[dict, dict, dict]:
    if len(rows) < 3:
        raise ValueError("CSV must contain at least 3 rows with part_file")
    rng = random.Random(seed)
    rows2 = list(rows)
    rng.shuffle(rows2)
    return rows2[0], rows2[1], rows2[2]


def _wav_duration_seconds(p: str | Path) -> float | None:
    try:
        with wave.open(str(p), "rb") as wf:
            return wf.getnframes() / float(wf.getframerate())
    except Exception:
        return None

def _is_bar_or_half_bar(seconds: float, bpm: float, tol_beats: float = 0.05) -> tuple[bool, float, str]:
    """Return (True, delta, kind) if begin_cue_adj is close to 0 or 2 beats modulo 4.

    kind is 'bar' (0 beats) or 'half' (2 beats).
    delta is the signed distance in beats from the matched grid point.
    """
    beats = float(seconds) * float(bpm) / 60.0
    beats_mod_4 = beats % 4.0

    # Distance to bar start (0 beats)
    d0 = beats_mod_4  # distance from 0
    if abs(d0) <= tol_beats or abs(d0 - 4.0) <= tol_beats:
        return True, d0 if abs(d0) <= tol_beats else d0 - 4.0, "bar"

    # Distance to half‑bar (2 beats)
    d2 = beats_mod_4 - 2.0
    if abs(d2) <= tol_beats:
        return True, d2, "half"

    return False, 0.0, ""



def _row_begin_cue_adj(row: dict) -> float | None:
    try:
        v = row.get("begin_cue_adj")
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None

# Helper: Parse end_cue_adj as float from row.
def _row_end_cue_adj(row: dict) -> float | None:
    try:
        v = row.get("end_cue_adj")
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None

 # Helper: Parse float value from a CSV row for a given key.
def _row_float(row: dict, key: str) -> float | None:
    try:
        v = row.get(key)
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def _row_section_duration(row: dict) -> float | None:
    v = _row_float(row, "duration_sectioned")
    if v is not None:
        return float(v)
    b = _row_begin_cue_adj(row)
    e = _row_end_cue_adj(row)
    if b is None or e is None:
        return None
    return float(e) - float(b)


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    if q <= 0.0:
        return min(values)
    if q >= 1.0:
        return max(values)
    vals = sorted(values)
    idx = int(round((len(vals) - 1) * q))
    return float(vals[idx])


def _prepare_selection_pools(rows: list[dict], seed: int | None) -> tuple[list[dict], list[dict], list[dict], float | None, float]:
    rng = random.Random(seed)
    durations = [d for r in rows if (d := _row_section_duration(r)) is not None and d > 0.0]
    median_duration = _percentile(durations, 0.5) or 0.0
    min_duration = max(0.0, 0.9 * float(median_duration))

    filtered = [r for r in rows if (_row_section_duration(r) is None or _row_section_duration(r) >= min_duration)]

    bpm_values = [b for r in filtered if (b := _row_float(r, "bpm")) is not None]
    bpm_threshold = _percentile(bpm_values, 0.7)

    available = list(filtered)
    rng.shuffle(available)

    high_pool: list[dict] = []
    for r in available:
        bpm = _row_float(r, "bpm")
        dur = _row_section_duration(r)
        if bpm_threshold is not None and bpm is not None and bpm >= bpm_threshold and dur is not None and dur >= min_duration:
            high_pool.append(r)

    normal_pool = [r for r in available if r not in high_pool]
    rng.shuffle(high_pool)
    rng.shuffle(normal_pool)

    return available, high_pool, normal_pool, bpm_threshold, min_duration


def _choose_next_row(
    high_mode: bool,
    available: list[dict],
    high_pool: list[dict],
    normal_pool: list[dict],
) -> dict | None:
    pool = high_pool if high_mode else normal_pool
    row = pool.pop() if pool else (available.pop() if available else None)
    if row is None:
        return None
    if row in available:
        available.remove(row)
    if row in high_pool:
        high_pool.remove(row)
    if row in normal_pool:
        normal_pool.remove(row)
    return row

# --- Diagnostics helpers for dropped rows ---
def _row_name(row: dict) -> str:
    p = row.get("path") or row.get("part_file") or ""
    return Path(p).name

def _alignment_diag(seconds: float | None, bpm: float) -> tuple[bool, str]:
    """Return (ok, message) for alignment of a cue time in seconds."""
    if seconds is None:
        return False, "missing"
    ok, delta, kind = _is_bar_or_half_bar(float(seconds), bpm)
    if not ok:
        beats = float(seconds) * float(bpm) / 60.0
        beats_mod_4 = beats % 4.0
        return False, f"offgrid: t={seconds:.3f}s beats={beats:.3f} mod4={beats_mod_4:.3f}"
    label = "bar" if kind == "bar" else "half"
    return True, f"ok:{label} Δ={delta:+.3f} beats (t={seconds:.3f}s)"


def _safe_float_from_row(row: dict, key: str, default: float | None = None) -> float | None:
    v = _row_float(row, key)
    return default if v is None else float(v)


def _deck_for_index(i: int) -> str:
    # Cycles through A, B, C, A, ...
    decks = ["A", "B", "C"]
    return decks[i % 3]



def build_playlist(rows: list[dict], seed: int | None, preload_offset: float = PRELOAD_OFFSET_SEC) -> list[dict]:
    """Return a shuffled playlist with operational timing columns.

    Columns (relative to global t=0):
      - deck: A/B/C cycling
      - load_at: when to send /cue for this row (preload window)
      - start_playing_at: when playback is expected to start (load_at + preload_offset)
      - next_song_cue: when to begin fade-out / transition to the next song
                       (start_playing_at + begin_cue_adj)
      - end_playing_at: when playback ends (start_playing_at + end_cue_adj)

    Definitions:
      - First row: load_at = 0.0; start_playing_at = preload_offset
      - For i>0: start_playing_at[i] = next_song_cue[i-1]
                load_at[i] = max(0, start_playing_at[i] - preload_offset)
    """
    if len(rows) < 1:
        return []

    rng = random.Random(seed)
    seq = list(rows)
    rng.shuffle(seq)

    playlist: list[dict] = []
    for i, r in enumerate(seq):
        b = float(_safe_float_from_row(r, "begin_cue_adj", default=0.0) or 0.0)
        e = float(_safe_float_from_row(r, "end_cue_adj", default=0.0) or 0.0)

        if i == 0:
            load_at = 0.0
            start_playing_at = float(preload_offset)
        else:
            start_playing_at = float(playlist[i - 1]["next_song_cue"])
            load_at = max(0.0, float(start_playing_at) - float(preload_offset))

        next_song_cue = float(start_playing_at) + float(b)
        end_playing_at = float(start_playing_at) + float(e)

        rr = dict(r)
        rr["deck"] = _deck_for_index(i)
        rr["load_at"] = float(load_at)
        rr["start_playing_at"] = float(start_playing_at)
        rr["next_song_cue"] = float(next_song_cue)
        rr["end_playing_at"] = float(end_playing_at)
        playlist.append(rr)

    return playlist


def _print_playlist(pl: list[dict], max_rows: int = 50) -> None:
    print("\n=== PLAYLIST (first rows) ===")
    n = min(len(pl), max_rows)
    for i in range(n):
        r = pl[i]
        name = _row_name(r)
        deck = r.get("deck")
        load_at = float(r.get("load_at", 0.0))
        sp = float(r.get("start_playing_at", 0.0))
        cue = float(r.get("next_song_cue", 0.0))
        en = float(r.get("end_playing_at", 0.0))
        b = float(_safe_float_from_row(r, "begin_cue_adj", default=0.0) or 0.0)
        e = float(_safe_float_from_row(r, "end_cue_adj", default=0.0) or 0.0)
        print(
            f"[{i:03d}] deck={deck} load_at={load_at:8.3f}s  start={sp:8.3f}s  cue_next={cue:8.3f}s  end={en:8.3f}s  "
            f"begin={b:7.3f}s  end={e:7.3f}s  {name}"
        )
    if len(pl) > n:
        print(f"... ({len(pl) - n} more)\n")


# --- Export playlist to CSV ---
def write_playlist_csv(pl: list[dict], out_csv: str | Path) -> None:
    """Write the computed playlist (including operational timing columns) to a CSV file."""
    out_csv = Path(out_csv)
    if not pl:
        # Still write a header-only CSV to be explicit
        out_csv.write_text("", encoding="utf-8")
        return

    # Prefer a stable, readable column order
    preferred = [
        "deck",
        "load_at",
        "start_playing_at",
        "next_song_cue",
        "end_playing_at",
        "path",
        "part_file",
        "bpm",
        "key",
        "target_bpm",
        "speed",
        "ini_cue",
        "begin_cue",
        "end_cue",
        "begin_cue_adj",
        "end_cue_adj",
        "begin_cue_adj_full",
        "end_cue_adj_full",
        "duration_orig",
        "duration_sectioned",
    ]

    # Include any extra columns present in the rows (at the end)
    extras: list[str] = []
    for r in pl:
        for k in r.keys():
            if k not in preferred and k not in extras:
                extras.append(k)

    fieldnames = [k for k in preferred if any(k in r for r in pl)] + extras

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in pl:
            w.writerow({k: r.get(k, "") for k in fieldnames})

    print(f"\n✅ Wrote playlist CSV: {out_csv}")

def main():
    parser = argparse.ArgumentParser(
        description="Mixer: pick two sectioned tracks from a CSV and start them with a scheduled offset."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Engine host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=57120, help="Engine OSC port (default: 57120)")
    parser.add_argument(
        "--csv",
        default="track_data_Cm-Gm_122-d3.csv",
        help="CSV produced by struct_loader.py (default: track_data_Bm-Em_122-d3.csv in repo).",
    )
    parser.add_argument(
        "--preload-offset",
        type=float,
        default=PRELOAD_OFFSET_SEC,
        help="Seconds between /cue and expected playback start (default: 1.0).",
    )
    parser.add_argument("--seed", type=int, default=None, help="Optional RNG seed for reproducible random selection.")
    parser.add_argument(
        "--xfade-steps",
        type=int,
        default=40,
        help="Number of steps for the low/high-pass transition (default: 40).",
    )
    parser.add_argument(
        "--print-playlist",
        action="store_true",
        help="Print the computed shuffled playlist timing table and exit (debug).",
    )
    parser.add_argument(
        "--playlist-csv",
        default="playlist_operational.csv",
        help="Write the computed operational playlist to this CSV file (default: playlist_operational.csv).",
    )
    parser.add_argument(
        "--movement-host",
        default="0.0.0.0",
        help="Host to bind movement OSC listener (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--movement-port",
        type=int,
        default=57120,
        help="Port to bind movement OSC listener (default: 57120; matches detector config)",
    )
    parser.add_argument(
        "--movement-interval",
        type=float,
        default=0.5,
        help="Interval (s) at which movement-driven updates are sent (default: 0.5)",
    )
    parser.add_argument(
        "--tempo-base",
        type=float,
        default=120.0,
        help="Reference tempo in BPM for movement-based adjustments (default: 120.0)",
    )
    parser.add_argument(
        "--tempo-range",
        type=float,
        default=10.0,
        help="Max BPM shift up/down from base based on movement (default: 10.0)",
    )
    parser.add_argument(
        "--tempo-scale",
        type=float,
        default=20.0,
        help="BPM change per 1.0 movement delta (default: 20.0)",
    )
    parser.add_argument(
        "--tempo-step",
        type=float,
        default=0.2,
        help="BPM step size per tempo update (default: 0.2)",
    )
    parser.add_argument(
        "--tempo-interval",
        type=float,
        default=30.0,
        help="Seconds between tempo updates (default: 30.0)",
    )
    parser.add_argument(
        "--movement-threshold",
        type=float,
        default=0.02,
        help="Average movement delta needed to trigger high/low mode (default: 0.02)",
    )
    args = parser.parse_args()

    rows = _read_selected_csv(args.csv)

    # Keep only rows missing cues; keep off-grid, just track stats.
    kept: list[dict] = []
    dropped: list[dict] = []
    drop_reasons = {"missing_begin": 0, "missing_end": 0, "begin_offgrid": 0, "end_offgrid": 0}
    dropped_detail: list[tuple[dict, str]] = []

    for r in rows:
        bca = _row_begin_cue_adj(r)
        eca = _row_end_cue_adj(r)

        ok_b, msg_b = _alignment_diag(bca, BPM_REF)
        ok_e, msg_e = _alignment_diag(eca, BPM_REF)

        if bca is None:
            drop_reasons["missing_begin"] += 1
            dropped.append(r)
            dropped_detail.append((r, f"begin_cue_adj missing; end={msg_e}"))
            continue
        if eca is None:
            drop_reasons["missing_end"] += 1
            dropped.append(r)
            dropped_detail.append((r, f"end_cue_adj missing; begin={msg_b}"))
            continue

        # Track off-grid stats, but do NOT drop for it
        if not ok_b:
            drop_reasons["begin_offgrid"] += 1
        if not ok_e:
            drop_reasons["end_offgrid"] += 1

        kept.append(r)
        if ok_b and ok_e:
            print(f"🎵 Grid-aligned: {_row_name(r)}  begin={msg_b}  end={msg_e}")
        else:
            print(f"⚠️ Off-grid (kept): {_row_name(r)}  begin={msg_b}  end={msg_e}")

    if dropped_detail:
        print(
            "⚠️ Dropped rows summary: "
            + ", ".join([f"{k}={v}" for k, v in drop_reasons.items()])
            + f" (total={len(dropped_detail)})"
        )
        # Print detailed diagnostics for the first N dropped rows
        N = min(30, len(dropped_detail))
        print(f"\n--- Dropped details (first {N}) ---")
        for row, reason in dropped_detail[:N]:
            print(f"  - {_row_name(row)} :: {reason}")

    rows = kept
    available, high_pool, normal_pool, bpm_threshold, min_duration = _prepare_selection_pools(rows, args.seed)
    if not available:
        print("⚠️ No usable rows after filtering; aborting.")
        return

    if bpm_threshold is not None:
        print(f"⚙️  High-energy pool: bpm >= {bpm_threshold:.2f}")
    if min_duration > 0.0:
        print(f"⚙️  Min section duration: {min_duration:.2f}s")

    if getattr(args, "print_playlist", False):
        playlist = build_playlist(
            available,
            seed=args.seed,
            preload_offset=float(args.preload_offset),
        )
        if playlist:
            r0 = playlist[0]
            print("\n=== FIRST ROW (operational columns) ===")
            print(
                f"deck={r0.get('deck')}  load_at={float(r0.get('load_at', 0.0)):.3f}s  start_playing_at={float(r0.get('start_playing_at', 0.0)):.3f}s  "
                f"next_song_cue={float(r0.get('next_song_cue', 0.0)):.3f}s  end_playing_at={float(r0.get('end_playing_at', 0.0)):.3f}s"
            )
        if args.playlist_csv:
            write_playlist_csv(playlist, args.playlist_csv)
        _print_playlist(playlist, max_rows=200)
        return

    # --- Playlist-driven scheduling (debug) ---
    client_host = args.host
    if client_host in ("0.0.0.0", "::"):
        client_host = "127.0.0.1"
    client = SimpleUDPClient(client_host, args.port)

    def send(addr, *payload):
        if len(payload) == 1 and isinstance(payload[0], (list, tuple)):
            payload = tuple(payload[0])
        client.send_message(addr, payload)
        print(f"→ {addr} {payload}  (sent by mixer clock)", flush=True)

    send("/reset", [])
    send("/set_tempo", float(args.tempo_base))
    print(f"🎚️ Tempo init -> {float(args.tempo_base):.2f} BPM")
    # Start from silence / flat EQ
    send("/deck_levels", 0.0, 0.0, 0.0, 0.0)
    send("/deck_eq_all", "A", 50, 50, 50)
    send("/deck_eq_all", "B", 50, 50, 50)
    send("/deck_eq_all", "C", 50, 50, 50)

    # --- Movement OSC receiver + updater ---
    movements: dict[str, float | None] = {"head": None, "legs": None, "arms": None}
    movement_seen = {"head": False, "legs": False, "arms": False}
    movements_lock = threading.Lock()
    stop_event = threading.Event()
    server = None
    last_sent: tuple[int, int, int] | None = None
    movement_samples: deque[tuple[float, float]] = deque()
    movement_mode = {"prefer_high": False}
    movement_baseline = {"avg": None}
    movement_start = time.monotonic()
    tempo_state = {
        "current": float(args.tempo_base),
        "target": float(args.tempo_base),
        "ramp_start": 0.0,
        "ramp_from": float(args.tempo_base),
        "ramp_to": float(args.tempo_base),
    }
    movement_report = {"last": 0.0}
    smooth_window = 5
    movement_buffers = {
        "head": deque(maxlen=smooth_window),
        "legs": deque(maxlen=smooth_window),
        "arms": deque(maxlen=smooth_window),
    }
    movement_msg_count = {"since_apply": 0}
    movement_apply_count = {"total": 0}

    def _clamp01(v: float) -> float:
        try:
            f = float(v)
        except Exception:
            return 0.0
        if f > 1.0 and f <= 100.0:
            f = f / 100.0
        if f < 0.0:
            return 0.0
        if f > 1.0:
            return 1.0
        return f

    def _infer_movement_name(address: str) -> str | None:
        tokens = []
        for chunk in address.lower().replace("-", "_").split("/"):
            tokens.extend(chunk.split("_"))
        if "head" in tokens:
            return "head"
        if "legs" in tokens or "leg" in tokens:
            return "legs"
        if "arms" in tokens or "arm" in tokens:
            return "arms"
        return None

    def _make_handler(name: str):
        def _handler(address, *args):
            # Expect first argument to be a float-like movement strength (0..1)
            if len(args) < 1:
                return
            v = _clamp01(args[0])
            with movements_lock:
                movements[name] = v
                movement_seen[name] = True
                movement_buffers[name].append(v)
                movement_msg_count["since_apply"] += 1
            # Raw movement messages are noisy; report only averaged updates.
        return _handler

    def _wildcard_handler(address, *args):
        name = _infer_movement_name(address)
        if not name or len(args) < 1:
            return
        v = _clamp01(args[0])
        with movements_lock:
            movements[name] = v
            movement_seen[name] = True
            movement_buffers[name].append(v)
            movement_msg_count["since_apply"] += 1
        # Raw movement messages are noisy; report only averaged updates.

    class ReuseAddrOSCUDPServer(ThreadingOSCUDPServer):
        allow_reuse_address = True

        def server_bind(self) -> None:
            if hasattr(socket, "SO_REUSEPORT"):
                try:
                    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except OSError:
                    pass
            super().server_bind()

    def start_movement_server(host: str, port: int):
        disp = Dispatcher()
        # Accept a few common address patterns
        disp.map("/dance/head", _make_handler("head"))
        disp.map("/dance/legs", _make_handler("legs"))
        disp.map("/dance/arms", _make_handler("arms"))
        disp.map("/dance/head_movement", _make_handler("head"))
        disp.map("/dance/legs_movement", _make_handler("legs"))
        disp.map("/dance/arms_movement", _make_handler("arms"))
        disp.map("/dance/*movement", _wildcard_handler)
        disp.map("/movement/head", _make_handler("head"))
        disp.map("/movement/legs", _make_handler("legs"))
        disp.map("/movement/arms", _make_handler("arms"))
        disp.map("/head", _make_handler("head"))
        disp.map("/legs", _make_handler("legs"))
        disp.map("/arms", _make_handler("arms"))

        server = ReuseAddrOSCUDPServer((host, port), disp)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        print(f"🕺 Movement OSC listener running on {host}:{port}")
        return server

    def movement_updater_thread(client: SimpleUDPClient, interval: float, stop_evt: threading.Event):
        nonlocal last_sent
        # Map movements -> EQ bands: legs -> low, arms -> mid, head -> high
        while not stop_evt.is_set():
            with movements_lock:
                head = movements.get("head")
                legs = movements.get("legs")
                arms = movements.get("arms")
                have_all = all(movement_seen.values())
                count_since_apply = movement_msg_count["since_apply"]
                head_buf = list(movement_buffers["head"])
                legs_buf = list(movement_buffers["legs"])
                arms_buf = list(movement_buffers["arms"])

            if not have_all or head is None or legs is None or arms is None:
                time.sleep(interval)
                continue

            now = time.monotonic()
            overall = (head + legs + arms) / 3.0
            with movements_lock:
                movement_samples.append((now, overall))
                # Keep the last 2 minutes of samples
                cutoff = now - 120.0
                while movement_samples and movement_samples[0][0] < cutoff:
                    movement_samples.popleft()

            if count_since_apply < smooth_window:
                time.sleep(interval)
                continue

            head_avg = sum(head_buf) / float(len(head_buf)) if head_buf else head
            legs_avg = sum(legs_buf) / float(len(legs_buf)) if legs_buf else legs
            arms_avg = sum(arms_buf) / float(len(arms_buf)) if arms_buf else arms

            # scale 0..1 -> 0..50
            high = int(round(50 * head_avg))
            low = int(round(50 * legs_avg))
            mid = int(round(50 * arms_avg))
            current = (low, mid, high)
            if last_sent is not None and current == last_sent:
                with movements_lock:
                    movement_msg_count["since_apply"] = 0
                time.sleep(interval)
                continue

            # Send gentle EQ updates for each deck (A/B/C)
            for deck in ("A", "B", "C"):
                try:
                    client.send_message("/deck_eq_all", [deck, low, mid, high])
                except Exception:
                    pass
            with movements_lock:
                movement_msg_count["since_apply"] = 0
                movement_apply_count["total"] += 1
                apply_count = movement_apply_count["total"]
            last_sent = current
            if apply_count % 5 == 0:
                print(
                    f"🎚️ Applied movement EQ: low={low} mid={mid} high={high} "
                    f"(avg over {smooth_window} msgs: head={head_avg:.3f} arms={arms_avg:.3f} legs={legs_avg:.3f})"
                )

            time.sleep(interval)

    def movement_trend_thread(check_interval: float, stop_evt: threading.Event):
        # After 60s, compare the last 60s average to the baseline (first minute).
        while not stop_evt.is_set():
            now = time.monotonic()
            with movements_lock:
                samples = list(movement_samples)
                baseline = movement_baseline["avg"]
                prefer_high = movement_mode["prefer_high"]
                tempo_base = float(args.tempo_base)
                tempo_range = float(args.tempo_range)
                tempo_scale = float(args.tempo_scale)
                threshold = float(args.movement_threshold)

            if baseline is None and now - movement_start >= 60.0 and samples:
                baseline_samples = [v for t, v in samples if t - movement_start <= 60.0]
                if baseline_samples:
                    baseline = sum(baseline_samples) / float(len(baseline_samples))
                    with movements_lock:
                        movement_baseline["avg"] = baseline
                    print(f"📊 Movement baseline (first 60s): {baseline:.3f}")

            if baseline is not None and samples:
                recent_samples = [v for t, v in samples if now - t <= 60.0]
                if recent_samples:
                    recent_avg = sum(recent_samples) / float(len(recent_samples))
                    with movements_lock:
                        last_report = float(movement_report["last"])
                    if recent_avg >= baseline + threshold and not prefer_high:
                        with movements_lock:
                            movement_mode["prefer_high"] = True
                        print(
                            f"⚡ Movement up: avg={recent_avg:.3f} baseline={baseline:.3f} -> prefer HIGH bpm"
                        )
                    elif recent_avg <= baseline - threshold and prefer_high:
                        with movements_lock:
                            movement_mode["prefer_high"] = False
                        print(
                            f"🐢 Movement low: avg={recent_avg:.3f} baseline={baseline:.3f} -> prefer NORMAL bpm"
                        )
                    delta = recent_avg - baseline
                    # Invert logic: more movement -> lower BPM, less movement -> higher BPM
                    # When delta is positive (movement increased), we want negative shift (lower BPM)
                    # When delta is negative (movement decreased), we want positive shift (higher BPM)
                    target_shift = max(-tempo_range, min(tempo_range, -delta * tempo_scale))
                    target = tempo_base + target_shift
                    with movements_lock:
                        prev_target = float(tempo_state["target"])
                        tempo_state["target"] = float(target)
                        current_bpm = float(tempo_state["current"])
                        if abs(target - prev_target) > 1e-6:
                            tempo_state["ramp_start"] = float(now)
                            tempo_state["ramp_from"] = float(current_bpm)
                            tempo_state["ramp_to"] = float(target)
                    if abs(target - prev_target) > 1e-6:
                        print(
                            f"🎛️ Tempo target -> {target:.2f} BPM (avg={recent_avg:.3f}, baseline={baseline:.3f})"
                        )
                    if now - last_report >= 30.0:
                        with movements_lock:
                            movement_report["last"] = float(now)
                            current_bpm = float(tempo_state["current"])
                        gap = target - current_bpm
                        delta = recent_avg - baseline
                        print("\n\n"
                              f"📈 Movement avg60={recent_avg:.3f} baseline={baseline:.3f} Δ={delta:+.3f} thr=±{threshold:.3f} "
                              f"tempo={current_bpm:.2f} target={target:.2f} gap={gap:+.2f}"
                              "\n\n")

            time.sleep(check_interval)

    def tempo_adjust_thread(update_interval: float, step_bpm: float, stop_evt: threading.Event):
        while not stop_evt.is_set():
            with movements_lock:
                target = float(tempo_state["target"])
                current = float(tempo_state["current"])
                ramp_start = float(tempo_state["ramp_start"])
                ramp_from = float(tempo_state["ramp_from"])
                ramp_to = float(tempo_state["ramp_to"])

            now = time.monotonic()
            ramp_duration = max(1.0, float(args.tempo_interval))
            if abs(target - current) < 1e-6:
                time.sleep(update_interval)
                continue

            if ramp_to != target:
                ramp_start = now
                ramp_from = current
                ramp_to = target
                with movements_lock:
                    tempo_state["ramp_start"] = float(ramp_start)
                    tempo_state["ramp_from"] = float(ramp_from)
                    tempo_state["ramp_to"] = float(ramp_to)

            progress = (now - ramp_start) / ramp_duration
            if progress < 0.0:
                progress = 0.0
            if progress > 1.0:
                progress = 1.0

            new_bpm = ramp_from + (ramp_to - ramp_from) * progress
            # Snap when close enough to avoid tiny oscillations
            if abs(new_bpm - target) < 0.01:
                new_bpm = target

            if abs(new_bpm - current) >= step_bpm or new_bpm == target:
                with movements_lock:
                    tempo_state["current"] = float(new_bpm)
                send("/set_tempo", float(new_bpm))
                print(f"🎚️ TEMPO STEP: {new_bpm:.2f} BPM (target={target:.2f})")

            time.sleep(update_interval)

    # Start server + updater
    try:
        server = start_movement_server(args.movement_host, args.movement_port)
        updater = threading.Thread(
            target=movement_updater_thread,
            args=(client, float(args.movement_interval), stop_event),
            daemon=True,
        )
        updater.start()
        trend = threading.Thread(
            target=movement_trend_thread,
            args=(5.0, stop_event),
            daemon=True,
        )
        trend.start()
        tempo_thread = threading.Thread(
            target=tempo_adjust_thread,
            args=(1.0, float(args.tempo_step), stop_event),
            daemon=True,
        )
        tempo_thread.start()
    except Exception as e:
        msg = str(e)
        if "Address already in use" in msg or "Errno 48" in msg:
            print("⚠️ Movement listener port in use. Either stop the other OSC server or use --movement-port to match a free port and update the detector config.")
        else:
            print(f"⚠️ Could not start movement listener/updater: {e}")

    def levels_for(decks: list[str], vols: dict[str, float]) -> tuple[float, float, float, float]:
        # Map A/B/C/D (D unused)
        return (
            float(vols.get("A", 0.0)),
            float(vols.get("B", 0.0)),
            float(vols.get("C", 0.0)),
            float(vols.get("D", 0.0)),
        )

    playlist: list[dict] = []

    def _append_playlist_row(row: dict, deck: str, load_at: float, start_at: float) -> None:
        b = float(_safe_float_from_row(row, "begin_cue_adj", default=0.0) or 0.0)
        e = float(_safe_float_from_row(row, "end_cue_adj", default=0.0) or 0.0)
        rr = dict(row)
        rr["deck"] = deck
        rr["load_at"] = float(load_at)
        rr["start_playing_at"] = float(start_at)
        rr["next_song_cue"] = float(start_at) + float(b)
        rr["end_playing_at"] = float(start_at) + float(e)
        playlist.append(rr)

    def _sleep_until(t_rel: float, t0: float) -> None:
        target = t0 + float(t_rel)
        now = time.monotonic()
        if target > now:
            time.sleep(target - now)

    # Crossfade config
    FADE_STEPS = 40  # smooth enough without spamming too hard
    vols: dict[str, float] = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0}

    t0 = time.monotonic()
    cur_index = 0
    cur_row = _choose_next_row(False, available, high_pool, normal_pool)
    if cur_row is None:
        print("⚠️ No tracks available to schedule.")
        return

    cur_deck = _deck_for_index(cur_index)
    cur_start = float(args.preload_offset)
    cur_load = max(0.0, cur_start - float(args.preload_offset))
    cur_begin = float(_safe_float_from_row(cur_row, "begin_cue_adj", default=0.0) or 0.0)
    cur_end = float(_safe_float_from_row(cur_row, "end_cue_adj", default=0.0) or 0.0)
    cur_cue = cur_start + cur_begin
    cur_end_at = cur_start + cur_end

    send("/cue", cur_deck, cur_row["part_file"], 0.0)
    _append_playlist_row(cur_row, cur_deck, cur_load, cur_start)

    _sleep_until(cur_start, t0)
    send("/start_group", 0.0, cur_deck)
    send("/deck_levels", 1.0, 0.0, 0.0, 0.0)
    vols[cur_deck] = 1.0

    while True:
        with movements_lock:
            prefer_high = movement_mode["prefer_high"]

        next_row = _choose_next_row(prefer_high, available, high_pool, normal_pool)
        if next_row is None:
            break

        next_deck = _deck_for_index(cur_index + 1)
        next_start = cur_cue
        next_load = max(0.0, next_start - float(args.preload_offset))
        next_begin = float(_safe_float_from_row(next_row, "begin_cue_adj", default=0.0) or 0.0)
        next_end = float(_safe_float_from_row(next_row, "end_cue_adj", default=0.0) or 0.0)
        next_cue = next_start + next_begin
        next_end_at = next_start + next_end

        _sleep_until(next_load, t0)
        send("/cue", next_deck, next_row["part_file"], 0.0)
        _append_playlist_row(next_row, next_deck, next_load, next_start)

        fade_dur = max(0.001, cur_end_at - cur_cue)
        started = False
        for s in range(FADE_STEPS + 1):
            a = s / FADE_STEPS
            t = cur_cue + a * fade_dur
            _sleep_until(t, t0)

            if not started and t >= cur_cue + 0.0005:
                send("/start_group", 0.0, next_deck)
                started = True

            out_v = 1.0 - a
            in_v = a
            lv = {**vols}
            lv[cur_deck] = out_v
            lv[next_deck] = in_v
            send("/deck_levels", levels_for(["A", "B", "C", "D"], lv))

            out_band = int(round(50 * (1.0 - a)))
            in_band = int(round(50 * a))
            send("/deck_eq_all", cur_deck, out_band, out_band, out_band)
            send("/deck_eq_all", next_deck, in_band, in_band, in_band)

        vols[cur_deck] = 0.0
        vols[next_deck] = 1.0
        send("/deck_levels", levels_for(["A", "B", "C", "D"], {**vols, cur_deck: 0.0, next_deck: 1.0}))

        cur_index += 1
        cur_row = next_row
        cur_deck = next_deck
        cur_start = next_start
        cur_begin = next_begin
        cur_end = next_end
        cur_cue = next_cue
        cur_end_at = next_end_at

    _sleep_until(cur_end_at + 0.001, t0)
    send("/deck_levels", 0.0, 0.0, 0.0, 0.0)

    # Finished scheduling; give movement updater a moment then stop it
    stop_event.set()
    try:
        if server is not None:
            server.shutdown()
            server.server_close()
    except Exception:
        pass

    if args.playlist_csv:
        write_playlist_csv(playlist, args.playlist_csv)

    print("✅ Scheduled adaptive playlist cue/start + crossfades (deck_levels + eq).")
    return

    row_a, row_b, row_c = _pick_three_rows(rows, seed=args.seed)

    track_a = row_a["part_file"]
    track_b = row_b["part_file"]
    track_c = row_c["part_file"]

    # Schedule starts exactly as:
    # A at start_in
    # B at start_in + begin_cue_adj(A)
    # C at start_in + begin_cue_adj(A) + begin_cue_adj(B)

    begin_a = _row_float(row_a, "begin_cue_adj") or 0.0
    begin_b = _row_float(row_b, "begin_cue_adj") or 0.0

    start_a = float(args.start_in)
    start_b = start_a + begin_a
    start_c = start_b + begin_b

    # Track B end (relative to the global timeline) for the B→C handoff window
    end_b = _row_float(row_b, "end_cue_adj")
    if end_b is None:
        raise ValueError("Track B row is missing end_cue_adj; cannot schedule B→C window")
    b_end_rel = start_b + float(end_b)

    # Compute end_a (Track A's end_cue_adj, in seconds)
    end_a = _row_float(row_a, "end_cue_adj") or None
    if end_a is None:
        raise ValueError("Track A row is missing end_cue_adj; cannot schedule filter transition.")

    dur_a = _wav_duration_seconds(track_a)
    dur_b = _wav_duration_seconds(track_b)
    dur_c = _wav_duration_seconds(track_c)

    print(f"🎛️ BPM_REF={BPM_REF} (reference only)")
    print(f"🎚️ Track A: {track_a}")
    print(f"🎚️ Track B: {track_b}")
    print(f"🎚️ Track C: {track_c}")
    print(f"⏱️ start_in (A start): {start_a:.3f} s")
    print(f"⏱️ begin_cue_adj(A): {begin_a:.3f} s")
    print(f"⏱️ begin_cue_adj(B): {begin_b:.3f} s")
    print(f"⏱️ B scheduled start: {start_b:.3f} s  [start_in + begin_cue_adj(A)]")
    print(f"⏱️ C scheduled start: {start_c:.3f} s  [start_in + begin_cue_adj(A) + begin_cue_adj(B)]")
    print(f"⏱️ B scheduled end: {b_end_rel:.3f} s  [B start + end_cue_adj(B)]")
    if dur_a is not None:
        print(f"⏱️ Track A duration: {dur_a:.2f} s")
    if dur_b is not None:
        print(f"⏱️ Track B duration: {dur_b:.2f} s")
    if dur_c is not None:
        print(f"⏱️ Track C duration: {dur_c:.2f} s")

    client = SimpleUDPClient(args.host, args.port)
    def send(addr, *payload):
        client.send_message(addr, payload)
        print(f"→ {addr} {payload}", flush=True)

    # Reset, set levels/EQ, cue both, then start together with offset
    send("/reset", [])
    # Set deck levels for A/B/C (D unused)
    send("/deck_levels", 1.0, 1.0, 1.0, 0.0)
    # Initial EQ:
    # - A full spectrum (flat)
    # - B fully filtered (silent) until we open its low band
    send("/deck_eq_all", "A", 50, 50, 50)
    send("/deck_eq_all", "B", 0, 0, 0)
    send("/deck_eq_all", "C", 0, 0, 0)

    # Cue both at position 0.0
    send("/cue", "A", track_a, 0.0)
    send("/cue", "B", track_b, 0.0)
    send("/cue", "C", track_c, 0.0)

    # Start A at start_a, B at start_b, C at start_c
    send("/start_group", start_a, "A")
    send("/start_group", start_b, "B")
    send("/start_group", start_c, "C")

    # Unified staged EQ handoffs: A→B and B→C
    t0 = time.monotonic()

    t_ab_start = start_b
    t_ab_end = start_a + end_a

    t_bc_start = start_c
    t_bc_end = b_end_rel

    t_start = min(t_ab_start, t_bc_start)
    t_end = max(t_ab_end, t_bc_end)

    if t_end <= t_start:
        print("⚠️ Transition window is empty; skipping filter ramp.")
    else:
        steps = max(2, int(args.xfade_steps))

        def clamp01(x: float) -> float:
            return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)

        def staged_p(alpha01: float) -> tuple[float, float, float]:
            # 3-phase: lows then mids then highs
            phase = alpha01 * 3.0
            p_low = clamp01(phase - 0.0)
            p_mid = clamp01(phase - 1.0)
            p_high = clamp01(phase - 2.0)
            return p_low, p_mid, p_high

        def progress(now_rel: float, start_rel: float, end_rel: float) -> float:
            if now_rel <= start_rel:
                return 0.0
            if now_rel >= end_rel:
                return 1.0
            return (now_rel - start_rel) / (end_rel - start_rel)

        for i in range(steps + 1):
            alpha = i / steps
            target_rel = t_start + (t_end - t_start) * alpha
            target_abs = t0 + target_rel

            now_abs = time.monotonic()
            if target_abs > now_abs:
                time.sleep(target_abs - now_abs)

            now_rel = target_rel

            # Compute handoff progresses
            pab = progress(now_rel, t_ab_start, t_ab_end)
            pbc = progress(now_rel, t_bc_start, t_bc_end)

            p_ab_low, p_ab_mid, p_ab_high = staged_p(pab)
            p_bc_low, p_bc_mid, p_bc_high = staged_p(pbc)

            # Deck A values (only affected by A→B)
            a_low = int(round(50 * (1.0 - p_ab_low)))
            a_mid = int(round(50 * (1.0 - p_ab_mid)))
            a_high = int(round(50 * (1.0 - p_ab_high)))

            # Deck C values (only affected by B→C)
            c_low = int(round(50 * p_bc_low))
            c_mid = int(round(50 * p_bc_mid))
            c_high = int(round(50 * p_bc_high))

            # Deck B values: opened by A→B then closed by B→C (when overlapping)
            b_low = int(round(50 * p_ab_low * (1.0 - p_bc_low)))
            b_mid = int(round(50 * p_ab_mid * (1.0 - p_bc_mid)))
            b_high = int(round(50 * p_ab_high * (1.0 - p_bc_high)))

            # Respect deck start times: before a deck starts, keep it muted
            if now_rel < start_a:
                a_low = a_mid = a_high = 0
            if now_rel < t_ab_start:  # before B starts
                b_low = b_mid = b_high = 0
            if now_rel < t_bc_start:  # before C starts
                c_low = c_mid = c_high = 0

            # --- Extra safety: explicit volume handoff ---
            a_level = 1.0 - pab
            c_level = pbc
            b_level = pab * (1.0 - pbc)

            if now_rel < start_a:
                a_level = 0.0
            if now_rel < t_ab_start:
                b_level = 0.0
            if now_rel < t_bc_start:
                c_level = 0.0

            a_level = 0.0 if a_level < 0.0 else (1.0 if a_level > 1.0 else a_level)
            b_level = 0.0 if b_level < 0.0 else (1.0 if b_level > 1.0 else b_level)
            c_level = 0.0 if c_level < 0.0 else (1.0 if c_level > 1.0 else c_level)

            send("/deck_levels", float(a_level), float(b_level), float(c_level), 0.0)

            # Apply EQ
            send("/deck_eq", "A", "low", a_low)
            send("/deck_eq", "A", "mid", a_mid)
            send("/deck_eq", "A", "high", a_high)

            send("/deck_eq", "B", "low", b_low)
            send("/deck_eq", "B", "mid", b_mid)
            send("/deck_eq", "B", "high", b_high)

            send("/deck_eq", "C", "low", c_low)
            send("/deck_eq", "C", "mid", c_mid)
            send("/deck_eq", "C", "high", c_high)

        print("✅ Completed staged handoffs: A→B and B→C.")

    print("✅ Started tracks A/B/C and ran staged filter handoffs A→B→C.")
    return

if __name__ == "__main__":
    main()
