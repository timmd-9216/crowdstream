# Crowdstream - Real-Time Audio Server & DJ Tools

## Audio Server (`audio_server.py`)

A Python-based real-time audio engine with OSC control, designed as a lightweight replacement for SuperCollider.

### Quick Start

```bash
# Basic usage (default buffer size optimized for Raspberry Pi)
python audio_server.py

# Custom buffer size
python audio_server.py --buffer-size 512

# With pre-loaded tracks
python audio_server.py --a track1.wav --b track2.wav
```

### Audio Stability on Raspberry Pi

If you experience **ALSA underrun warnings** or **audio glitches**, the buffer size controls the stability/latency tradeoff:

```bash
# Most stable (recommended for Raspberry Pi 4)
python audio_server.py --buffer-size 1024  # 23ms latency

# Balanced (good for Raspberry Pi 5 or desktop)
python audio_server.py --buffer-size 512   # 12ms latency

# Lowest latency (requires powerful CPU)
python audio_server.py --buffer-size 256   # 6ms latency
```

**See [AUDIO_BUFFER_SIZE_TUNING.md](AUDIO_BUFFER_SIZE_TUNING.md)** for detailed tuning guide.

### Recent Fixes

- **Race condition fix**: `/start_group` now waits for buffers to load before starting playback ([details](AUDIO_SERVER_RACE_CONDITION_FIX.md))
- **Enhanced error logging**: Detailed file-not-found diagnostics ([details](ERROR_LOGGING_IMPROVEMENTS.md))
- **Buffer size tuning**: Configurable latency/stability tradeoff

---

## Track Section Exporter (`struct_loader.py`)

A DJ-focused utility to extract **mix-ready audio sections** from tracks using
precomputed structure JSONs, with **accurate BPM handling via Rekordbox** and
full **debug visibility** through a rich CSV output.

This tool is designed to answer one practical question:

> *"Give me consistent, tempo-aligned sections I can actually mix."*

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

### Setup

```bash
bash scripts/install.sh
source .venv/bin/activate
```

### Example: export sections at a target BPM using Rekordbox BPM

```bash
python struct_loader.py \
  --bpm 122.5 --delta 2 --key "Gm,Cm" \
  --rekordbox-xml ./track_data_rekordbox.xml \
  --csv-out selected.csv \
  --parts-dir parts_temp \
  --audio-dir ../stems/dj
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
- Uses the default struct directory at `<repo_root>/../stems/dj/struct`; override by passing a path argument before any flags if needed.
- Uses WAVs from `<repo_root>/../stems/dj` by default (override with `--audio-dir`). Paths inside the JSONs are rebased by filename.
- Many structs have no `key` field; omit `--key` unless you’ve populated keys (e.g., via Rekordbox Tonality).

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
