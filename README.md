# Track Section Exporter (`struct_loader.py`)

A DJ-focused utility to extract **mix-ready audio sections** from tracks using
precomputed structure JSONs, with **accurate BPM handling via Rekordbox** and
full **debug visibility** through a rich CSV output.

This tool is designed to answer one practical question:

> *“Give me consistent, tempo-aligned sections I can actually mix.”*


## Example: export sections at a target BPM using Rekordbox BPM

```bash
python struct_loader.py \
  --bpm 122.5 --delta 2 --key "Gm,Cm" \
  --rekordbox-xml /Users/xaviergonzalez/Documents/repos/crowdstream/track_data_rekordbox.xml \
  --csv-out selected.csv \
  --parts-dir parts_temp´´´
  
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

---

## Requirements

- Python **3.10+**
- `ffmpeg` available **to Python**

Check that Python can see ffmpeg:

```bash
python -c "import shutil; print(shutil.which('ffmpeg'))"
