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
import argparse, time
from pathlib import Path

# Search roots for audio material (stems + generated parts)
SEARCH_ROOTS = [
    Path(__file__).resolve().parent.parent / "stems",
    Path(__file__).resolve().parent / "parts_temp",
]

# --- Default tracks (resolved at runtime against SEARCH_ROOTS) ---
TRACK_A = "../stems/dj/12678406_Mystery_(Tale Of Us & Mathame Remix).wav"
TRACK_B = "../stems/dj/17563740_On Me_(Extended Mix).wav"

BPM = 122.0
BEATS_PER_SEC = BPM / 60.0  # 2.0
BEAT_SEC = 1.0 / BEATS_PER_SEC  # 0.5 s/beat
OFFSET_B = 0.13  # Deck B content offset (seconds)

# Beat window for the bass sweep: 8..16
BEAT_START = 8
BEAT_END = 16

# Convert beats to absolute seconds (no offset)
T_START = OFFSET_B + BEAT_START * BEAT_SEC  # 0 + 8*~0.4878 ≈ 3.90
T_END = OFFSET_B + BEAT_END * BEAT_SEC      # 0 + 16*~0.4878 ≈ 7.80

def main():
    parser = argparse.ArgumentParser(description="Mixer: cue A & B then start together (sample-tight) with EQ automation.")
    parser.add_argument("--host", default="127.0.0.1", help="Engine host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=57120, help="Engine OSC port (default: 57120)")
    parser.add_argument("--start-in", type=float, default=0.5, help="Seconds after reset to start both decks together (default: 0.5)")
    parser.add_argument("--preflight-only", action="store_true", help="Scan and resolve tracks, then exit without sending OSC.")
    args = parser.parse_args()

    client = SimpleUDPClient(args.host, args.port)
    send = lambda addr, *payload: (client.send_message(addr, payload), print(f"→ {addr} {payload}", flush=True))

    def scan_wavs(roots):
        wavs = {}
        for root in roots:
            root = Path(root).expanduser()
            if not root.exists():
                continue
            for p in root.rglob("*.wav"):
                wavs[p.name] = p
        return wavs

    wav_index = scan_wavs(SEARCH_ROOTS)

    def resolve(path_str: str) -> Path | None:
        p = Path(path_str).expanduser()
        if p.is_file():
            return p
        if p.name in wav_index:
            return wav_index[p.name]
        return None

    res_a = resolve(TRACK_A)
    res_b = resolve(TRACK_B)
    print(f"📂 Found {len(wav_index)} WAVs across search roots {', '.join(str(r) for r in SEARCH_ROOTS)}")
    print(f"🎚️  Track A: {TRACK_A} -> {res_a}")
    print(f"🎚️  Track B: {TRACK_B} -> {res_b}")

    if not res_a or not res_b:
        print("❌ Missing required track(s); aborting.")
        return

    if args.preflight_only:
        return

    # === EQ constraint config ===
    SUM_BUDGET = 50   # A_band + B_band must be <= 50 (50% = flat)
    CAP = 35          # Non-linear cap per deck per band (<= 35%)
    BASE_SPLIT = 35   # Neutral split per band (A=25, B=25)

    def enforce_pair(a_desired: int, b_desired: int, cap: int = CAP, budget: int = SUM_BUDGET) -> tuple[int,int]:
        a = min(cap, max(0, int(a_desired)))
        b = min(cap, max(0, int(b_desired)))
        s = a + b
        if s <= budget:
            return a, b
        if s == 0:
            return 0, 0
        a_scaled = int(round(a * budget / s))
        b_scaled = int(round(b * budget / s))
        if a_scaled + b_scaled > budget:
            if a_scaled >= b_scaled:
                a_scaled -= 1
            else:
                b_scaled -= 1
        return a_scaled, b_scaled

    def set_pair(band: str, a_target: int, b_target: int):
        a_val, b_val = enforce_pair(a_target, b_target)
        send("/deck_eq", "A", band, a_val)
        send("/deck_eq", "B", band, b_val)

    def set_all_pairs(a_low: int, b_low: int, a_mid: int, b_mid: int, a_high: int, b_high: int):
        set_pair("low", a_low, b_low)
        set_pair("mid", a_mid, b_mid)
        set_pair("high", a_high, b_high)

    # Reset, set levels/EQ, cue both, then start together
    send("/reset", [])
    # Start with full deck volumes for A/B
    send("/deck_levels", 1.0, 1.0, 0.0, 0.0)
    send("/deck_eq_all", "A", 50, 50, 50)
    send("/deck_eq_all", "B", 50, 50, 50)

    # Cue both decks at position 0.0 (load + arm without starting)
    send("/cue", "A", str(res_a), 0.0)
    send("/cue", "B", str(res_b), 0.0)

    # Start A at t = start_in, and B at t = start_in + OFFSET_B (time‑offset start)
    # Cue both at position 0.0 so the timeline delta is visible in the server logs
    send("/start_group", args.start_in, "A")
    send("/start_group", args.start_in + OFFSET_B, "B")

    # === Post-start modulation: square-length EQ cycles ===
    import random, math

    def eq_all(deck, l, m, h):
        send("/deck_eq_all", deck, int(l), int(m), int(h))

    def eq(deck, band, val):
        send("/deck_eq", deck, band, int(val))

    def wait_beats(n_beats: int):
        time.sleep(BEAT_SEC * n_beats)

    # Ensure both decks are at complementary base split at the moment of launch
    set_all_pairs(BASE_SPLIT, BASE_SPLIT, BASE_SPLIT, BASE_SPLIT, BASE_SPLIT, BASE_SPLIT)

    # Square block sizes in beats (descend first to hit natural tension points)
    SQUARES_DESC = [64, 32, 16, 8, 4, 2]

    # Helper to craft tension → resolution within a block
    def tension_block(deck_lead: str, beats: int):
        other = "B" if deck_lead == "A" else "A"
        # Tension: cut mids/highs on the lead deck, open other highs; keep lows neutral
        steps = max(4, min(12, beats))
        for i in range(steps):
            t = (i + 1) / steps
            cut = 50 - int(round(40 * t))           # 50 → 10 (leader reduced)
            other_fill = SUM_BUDGET - min(CAP, cut) # partner complements up to budget
            other_fill = min(CAP, max(0, other_fill))
            # mids pair (leader vs other)
            if deck_lead == "A":
                set_pair("mid", cut, other_fill)
            else:
                set_pair("mid", other_fill, cut)
            # highs pair (same idea)
            if deck_lead == "A":
                set_pair("high", cut, other_fill)
            else:
                set_pair("high", other_fill, cut)
            # keep lows neutral split
            set_pair("low", BASE_SPLIT, BASE_SPLIT)
            wait_beats(max(1, beats // steps))
        # Micro resolve: bring both mids/highs towards neutral split
        set_pair("mid", BASE_SPLIT, BASE_SPLIT)
        set_pair("high", BASE_SPLIT, BASE_SPLIT)

    def resolve_block(beats: int):
        # Ease mids/highs toward base split, keep lows neutral
        steps = max(4, min(12, beats))
        for i in range(steps):
            t = (i + 1) / steps
            v = BASE_SPLIT - int(round(5 * (1 - t)))  # ease to 25
            set_pair("mid", v, v)
            set_pair("high", v, v)
            set_pair("low", BASE_SPLIT, BASE_SPLIT)
            wait_beats(max(1, beats // steps))

    def low_swap_pulse(beats: int):
        # Briefly swing lows around the neutral split using pairs (sum stays 50, each ≤ CAP)
        steps = max(2, min(8, beats))
        for i in range(steps):
            t = (i + 1) / steps
            delta = int(round(10 * t))  # swing up to ±10 around 25 → (15,35)
            a_low = BASE_SPLIT - delta
            b_low = BASE_SPLIT + delta
            set_pair("low", a_low, b_low)
            wait_beats(max(1, beats // steps))
        # return to neutral split
        set_pair("low", BASE_SPLIT, BASE_SPLIT)

    # Cycle plan: start with big blocks (tension), then climb back (release)
    sequences = [SQUARES_DESC, list(reversed(SQUARES_DESC))]

    print("🎛️ Kicking off square-length EQ cycles (2/4/8/16/32/64)…", flush=True)

    # Run two macro cycles (~ sums of squares in beats)
    for macro_idx, seq in enumerate(sequences):
        for beats in seq:
            # Alternate leader between A and B each block
            leader = "A" if ((macro_idx + beats) % 2 == 0) else "B"
            print(f"🧱 Block: {beats} beats — leader {leader}", flush=True)
            # Micro-tension first half
            tension_block(leader, beats // 2 or 1)
            # Optional spice: on shorter blocks do a pulse, on longer do extra tension
            if beats <= 8:
                low_swap_pulse(max(2, beats // 2))
            else:
                tension_block(leader, max(4, beats // 4))
            # Resolve on the remainder
            resolve_block(max(2, beats // 2))

    # Final resolve honoring complementary split (no 6 filters full)
    # Lows neutral 25/25, mids complementary, highs neutral 25/25
    set_pair("low", BASE_SPLIT, BASE_SPLIT)
    set_pair("mid", 30, 20)
    set_pair("high", BASE_SPLIT, BASE_SPLIT)
    print("✅ Square-cycle EQ journey complete.", flush=True)

    print(f"✅ Cued A & B. Start A in {args.start_in:.3f}s, B in {(args.start_in + OFFSET_B):.3f}s (Δ={OFFSET_B:.3f}s).", flush=True)

if __name__ == "__main__":
    main()
