# 🌌 Cosmic Skeleton Standalone

Standalone cosmic skeleton visualizer with integrated YOLO pose detection. No external detector needed!

## Features

- ✨ **Standalone**: Runs YOLO pose detection internally
- 🌌 **Cosmic visuals**: Beautiful space-themed skeleton rendering
- 👥 **Multi-person**: Tracks and displays multiple people side-by-side
- ⚡ **Optimized**: Configurable for Raspberry Pi 4 performance
- 🎨 **Real-time**: Live camera feed with instant detection

## Quick Start

### 1. Install

```bash
./install.sh
```

### 2. Run

```bash
./start.sh
```

Access the visualizer at: `http://localhost:8094`

## Usage

### Basic

```bash
./start.sh
```

### Custom port

```bash
./start.sh --port 8095
```

### Optimize for speed (Raspberry Pi)

```bash
./start.sh --imgsz 320
```

### Use video file instead of webcam

```bash
./start.sh --source /path/to/video.mp4
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `--port` | 8094 | Web server port |
| `--source` | 0 | Video source (0=webcam, or path to file) |
| `--imgsz` | 416 | YOLO input size (320=fast, 416=balanced, 640=accurate) |

## Performance Tuning

For Raspberry Pi 4:

```bash
# Fastest (lower quality)
./start.sh --imgsz 320

# Balanced (recommended)
./start.sh --imgsz 416

# Best quality (slower)
./start.sh --imgsz 640
```

## Architecture

Unlike the regular `cosmic_skeleton` which requires an external detector:

```
cosmic_skeleton:         [detector] --OSC--> [visualizer] --WebSocket--> [browser]
cosmic_skeleton_standalone:  [YOLO + visualizer] --WebSocket--> [browser]
```

This standalone version:
- Runs YOLO detection internally
- No OSC communication needed
- Single process = simpler deployment
- Perfect for standalone installations

## Comparison

| Feature | cosmic_skeleton | cosmic_skeleton_standalone |
|---------|----------------|---------------------------|
| External detector needed | ✅ Yes | ❌ No |
| OSC communication | ✅ Yes | ❌ No |
| Processes | 2+ | 1 |
| Setup complexity | Medium | Low |
| Use case | Multi-service | Standalone |

## Troubleshooting

### No video showing

Check camera permissions and that device `/dev/video0` exists:

```bash
ls -l /dev/video*
```

### Low FPS on Raspberry Pi

Reduce image size:

```bash
./start.sh --imgsz 320
```

### Port already in use

Use a different port:

```bash
./start.sh --port 8095
```

## Dependencies

- Python 3.8+
- OpenCV
- Ultralytics YOLO
- FastAPI
- Uvicorn

All automatically installed via `./install.sh`
