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

### Movement-Based BPM Control

The audio server supports **automatic BPM adjustment based on detected movement**. This creates an adaptive musical experience where tempo responds to audience/performer activity.

#### How It Works

The system uses **threshold-based BPM targets** with smooth transitions (~30 seconds):

| Movement Level | Threshold | Target BPM |
|----------------|-----------|------------|
| Very very low  | < 2%      | 110 BPM    |
| Very low       | 2-5%      | 113 BPM    |
| Low            | 5-10%     | 115 BPM    |
| Medium-low     | 10-15%    | 118 BPM    |
| High           | ≥ 15%     | 118→130 BPM (progressive) |

#### Behavior

- **Low movement** → BPM gradually decreases in steps: 118 → 115 → 113 → 110
- **High movement** → BPM progressively increases up to 130 BPM
- **All transitions** take approximately 30 seconds for smooth, musical changes
- **Base BPM** starts at 120 BPM

#### Configuration

Both `audio_server.py` and `mixer_tracks.py` share this logic. The movement data is received via OSC on port 57122 from the dance movement detector.

```bash
# Movement-based BPM is enabled by default
python audio_server.py --port 57122
```

#### Requirements for Time-Stretch

For BPM changes to actually affect audio playback speed, you need:

1. **pyrubberband** (Python package - included in requirements.txt)
2. **rubberband** (system library)

```bash
# macOS
brew install rubberband

# Ubuntu/Debian
sudo apt-get install rubberband-cli

# Raspberry Pi
sudo apt-get install rubberband-cli
```

Without rubberband, BPM changes will only affect the internal clock but not the actual audio playback speed.

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

---

## Troubleshooting

### Performance Issues with Real-Time EQ Filters

If you experience **audio glitches, stuttering, or high CPU usage** when EQ filters are enabled:

**Raspberry Pi:**
- EQ filters are **disabled by default** on Raspberry Pi for performance
- Real-time EQ processing can cause audio dropouts and exceed CPU budget
- If you enabled them with `--enable-filters` and experience issues, disable them:
  ```bash
  # Remove --enable-filters flag from scripts/audio-mix-start.sh
  python audio_server.py --port 57122  # Without --enable-filters
  ```
- For better performance, use optimized filters (requires scipy):
  ```bash
  python audio_server.py --port 57122 --optimized-filters
  ```

**Mac M1:**
- EQ filters are **disabled by default** on Mac M1 for performance
- Real-time EQ processing can cause audio dropouts and high CPU usage (80-100%)
- To disable filters:
  ```bash
  python audio_server.py --port 57122  # Filters disabled by default on M1
  ```
- If you need EQ control, consider:
  - Using external hardware EQs
  - Using software EQs outside the audio server
  - Upgrading to M2 Pro/Max/Ultra (filters enabled by default)

**General Recommendations:**
- Monitor CPU usage: `top` or `htop` to verify impact
- Use filters only on more powerful systems (M2 Pro/Max, desktop CPUs)
- Increase buffer size if using filters: `--buffer-size 2048` (higher latency but more stable)
- Consider alternatives: External hardware EQs or software EQs outside the audio server

**Performance Testing:**
```bash
# Without filters (baseline)
python audio_server.py --port 57122
# Monitor CPU: should be < 30% on desktop, < 50% on RPi

# With filters
python audio_server.py --port 57122 --enable-filters
# Monitor CPU: may spike to 80-100% on RPi/M1
```

See [docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md) for more detailed troubleshooting information.
