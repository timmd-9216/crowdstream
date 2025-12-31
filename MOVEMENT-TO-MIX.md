# Movement To Mix

This document describes how movement OSC messages influence mixing and track selection in `mixer_tracks.py`.

## OSC inputs and mapping

- OSC base address: `/dance` (as used by `dance_movement_detector`).
- Expected addresses:
  - `/dance/head`, `/dance/head_movement`
  - `/dance/legs`, `/dance/legs_movement`
  - `/dance/arms`, `/dance/arms_movement`
  - `/dance/*movement` (wildcard; parses head/legs/arms in the address)
- Each message is expected to include a single float value:
  - `0.0..1.0` preferred
  - `0..100` accepted and normalized to `0.0..1.0`

## Movement -> EQ

Movement is applied continuously as EQ updates:

- legs -> low band
- arms -> mid band
- head -> high band

Values are scaled to `0..50` and sent as:

```
/deck_eq_all <deck> <low> <mid> <high>
```

The mixer prints a message when it applies EQ:

- `🎚️ Applied movement EQ: low=.. mid=.. high=.. (avg over 5 msgs: head=.. arms=.. legs=..)`

## Movement trend -> track selection

After the first 60 seconds, the mixer computes a baseline average movement from that initial minute. It then watches the last 60 seconds:

- If the last-60s average >= baseline + 0.02, **prefer high BPM**.
- If the last-60s average <= baseline - 0.02, **prefer normal BPM**.

This directly affects which tracks are chosen next.

## High-energy selection (rule 1)

"More moved" tracks are chosen using BPM:

- The 70th percentile BPM in the CSV is used as the threshold.
- High-energy pool = tracks with `bpm >= threshold`.

When prefer-high is ON, the mixer prefers this pool.

## Avoid short sections (rule 3)

To avoid short sections:

- `duration_sectioned` is used when present.
- Otherwise, section duration is `end_cue_adj - begin_cue_adj`.
- A minimum duration is computed as `0.9 * median(section_duration)`.
- Tracks below this minimum are skipped.

## Runtime scheduling

The mixer now selects tracks dynamically instead of precomputing the full playlist:

- Tracks are chosen just before their `/cue` time.
- Crossfades are still driven by the current track’s `begin_cue_adj` and `end_cue_adj`.
- `playlist_operational.csv` is written at the end using the actual track order.

## Ports and conflicts

The detector sends OSC to port `57120` by default. The mixer listens for movement on that port. The audio engine should use a different port to avoid conflicts (e.g. `57122`).

Example run (from `losdones-start.sh`):

```
python audio_server.py --port 57122 &
python mixer_tracks.py --host 127.0.0.1 --port 57122 --movement-port 57120 &
```

## Tempo adjustment from movement

The mixer sends `/set_tempo` to the audio server to slowly shift BPM based on movement:

- Base tempo: 120 BPM by default (`--tempo-base`).
- Range: +/-10 BPM (`--tempo-range`).
- If movement is high, tempo drifts up toward base+range.
- If movement is low, tempo drifts down toward base-range.
- Tempo changes are gradual (default 0.2 BPM every 30s).
