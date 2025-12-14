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
import argparse, time, csv, random, wave
from pathlib import Path

BPM_REF = 122.5  # Reference only; not used for playback timing.

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

def main():
    parser = argparse.ArgumentParser(
        description="Mixer: pick two sectioned tracks from a CSV and start them with a scheduled offset."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Engine host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=57120, help="Engine OSC port (default: 57120)")
    parser.add_argument("--start-in", type=float, default=0.5, help="Seconds after reset to start Track A (default: 0.5)")
    parser.add_argument(
        "--csv",
        default="/Users/xaviergonzalez/Documents/repos/crowdstream/selected26.csv",
        help="CSV produced by struct_loader.py (default: selected_new.csv in repo).",
    )
    parser.add_argument("--seed", type=int, default=None, help="Optional RNG seed for reproducible random selection.")
    parser.add_argument(
        "--xfade-steps",
        type=int,
        default=40,
        help="Number of steps for the low/high-pass transition (default: 40).",
    )
    args = parser.parse_args()

    rows = _read_selected_csv(args.csv)

    # Keep only rows whose begin_cue_adj AND end_cue_adj are close to a bar (0) or half-bar (±2 beats)
    kept: list[dict] = []
    dropped: list[dict] = []

    for r in rows:
        bca = _row_begin_cue_adj(r)
        if bca is None:
            dropped.append(r)
            continue

        eca = _row_end_cue_adj(r)
        if eca is None:
            dropped.append(r)
            continue

        ok_b, delta_b, kind_b = _is_bar_or_half_bar(bca, BPM_REF)
        ok_e, delta_e, kind_e = _is_bar_or_half_bar(eca, BPM_REF)

        if ok_b and ok_e:
            kept.append(r)
            name = Path(r.get("path", r.get("part_file", "")) or "").name
            label_b = "bar (0 beats)" if kind_b == "bar" else "half‑bar (±2 beats)"
            label_e = "bar (0 beats)" if kind_e == "bar" else "half‑bar (±2 beats)"
            print(f"🎵 Grid‑aligned [begin={label_b}, end={label_e}]: {name}  Δbegin={delta_b:+.3f} beats, Δend={delta_e:+.3f} beats")
        else:
            dropped.append(r)

    if dropped:
        sample = [Path(d.get("path", d.get("part_file", "")) or "").name for d in dropped[:5]]
        print(f"⚠️ Dropped {len(dropped)} row(s) not aligned on begin/end (bar 0 or half‑bar ±2) (sample: {sample})")

    rows = kept
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