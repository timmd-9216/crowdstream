# Track Section Exporter (`struct_loader.py`)

A DJ-focused utility to extract **mix-ready audio sections** from tracks using
precomputed structure JSONs, with **accurate BPM handling via Rekordbox** and
full **debug visibility** through a rich CSV output.

This tool is designed to answer one practical question:

> *“Give me consistent, tempo-aligned sections I can actually mix.”*

---

## What this script does

- Loads **track structure JSONs** (segments, beats, cues)
- Optionally **overrides BPM using Rekordbox XML** (`AverageBpm`)
- Filters tracks by **BPM range** and **musical key**
- Computes:
  - intro cue (`ini_cue`)
  - section boundaries counted *after* the intro
- Exports **sectioned WAV files**
  - cropped from `ini_cue → end_cue`
  - **tempo-adjusted to a target BPM**
- Writes a **debug-friendly CSV** with:
  - raw cues
  - adjusted cues
  - original vs sectioned durations
  - exact output file paths

## Usage

### Example: export sections at a target BPM using Rekordbox BPM

```bash
python struct_loader.py \
  --bpm 122.5 --delta 2 --key "Gm,Cm" \
  --rekordbox-xml /Users/xaviergonzalez/Documents/repos/crowdstream/track_data_rekordbox.xml \
  --csv-out selected.csv \
  --parts-dir parts_temp
```

This command:

- Selects tracks within **±2 BPM of 122.5**
- Filters by musical key **Gm OR Cm**
- Uses **Rekordbox `AverageBpm`** (from the XML) instead of BPM stored in the JSONs
- Exports **sectioned WAV files** cropped from `ini_cue` to `end_cue`
- Tempo-aligns all exported sections to the **target BPM**
- Writes a detailed CSV (`selected.csv`) with:
  - original cues (`ini_cue`, `begin_cue`, `end_cue`)
  - adjusted cues (`begin_cue_adj`, `end_cue_adj`)
  - original vs sectioned durations (for debugging)

#### Important notes

- BPM values stored in the track JSON files may be inaccurate.
- When `--rekordbox-xml` is provided, BPM is overridden **in memory only** using Rekordbox’s `AverageBpm`.
- The JSON files on disk are **not modified**.
- The CSV is intended as a debugging and verification tool; if
  `duration_sectioned ≈ duration_orig / speed`, the tempo alignment worked.

---

## Requirements

- Python **3.10+**
- `ffmpeg` available **to Python**

Check that Python can see ffmpeg:

```bash
python -c "import shutil; print(shutil.which('ffmpeg'))"
```
