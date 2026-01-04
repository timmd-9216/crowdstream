# Dance Movement Detector - Configuration Guide

## Quick Start

Choose the configuration that best fits your needs:

### 🚀 Maximum Performance (~20-25 FPS)
Best for: Live performances with multiple dancers, when speed matters more than precision.

```bash
./start_detector_rpi.sh config/config_rpi_max_performance.json
```

### ⚖️ Balanced (~12-18 FPS) ⭐ RECOMMENDED
Best for: General use, good balance between speed and accuracy.

```bash
./start_detector_rpi.sh config/config_rpi_optimized.json
```

### 🎯 High Quality (~5-8 FPS)
Best for: Debugging, testing, when accuracy is critical.

```bash
./start_detector_rpi.sh config/config.json
```

---

## Configuration Files

### Location
All configuration files are in: `dance_movement_detector/config/`

### Available Configs

| File | FPS | CPU | Use Case |
|------|-----|-----|----------|
| `config_rpi_max_performance.json` | 20-25 | 40-50% | Live shows, many dancers |
| `config_rpi_optimized.json` | 12-18 | 50-70% | General use (recommended) |
| `config.json` | 5-8 | 80-100% | Testing, debugging |

---

## Configuration Parameters Explained

### Core Performance Settings

#### `model` - YOLO Model Selection
```json
"model": "yolov8n-pose.pt"
```

**Options**:
- `"yolov8n-pose.pt"` - Nano (fastest, recommended for Raspberry Pi)
- `"yolov8s-pose.pt"` - Small (slower but more accurate)
- `"yolov8m-pose.pt"` - Medium (too slow for Raspberry Pi)

**Impact**: 2-3x speed difference between nano and medium.

---

#### `imgsz` - Input Image Size
```json
"imgsz": 320
```

**Options**:
- `320` - Maximum speed, lower accuracy
- `416` - Balanced (recommended)
- `640` - High quality, slower

**Impact**: ~40% speed improvement (320 vs 640)

**Trade-off**: Smaller images = faster processing but may miss small movements or distant dancers.

---

#### `skip_frames` - Frame Skip Rate
```json
"skip_frames": 2
```

**Options**:
- `0` - Process every frame (smoothest, slowest)
- `1` - Process every 2nd frame (2x faster)
- `2` - Process every 3rd frame (3x faster)
- `3` - Process every 4th frame (4x faster, choppy)

**Impact**: Linear speedup (skip_frames=2 → 3x faster)

**Trade-off**: Higher values = faster but less smooth movement detection.

---

### Camera Settings

#### `camera_width`, `camera_height` - Camera Resolution
```json
"camera_width": 640,
"camera_height": 480
```

**Common Options**:
- `640x480` - VGA (fast, recommended)
- `1280x720` - HD (slower)
- `1920x1080` - Full HD (very slow on RPi)

**Impact**: ~20-30% speed improvement (640x480 vs 1280x720)

---

#### `camera_fps` - Camera Frame Rate
```json
"camera_fps": 15
```

**Options**:
- `15` - Lower frame rate (saves CPU)
- `30` - Standard frame rate
- `60` - High frame rate (only useful if you can process that fast)

**Tip**: No point setting higher than your processing speed can handle.

---

### Detection Settings

#### `conf_threshold` - Confidence Threshold
```json
"conf_threshold": 0.35
```

**Range**: `0.0` to `1.0`

**Recommendations**:
- `0.25` - Detect more people (more false positives)
- `0.35` - Balanced (recommended)
- `0.45` - Only high-confidence detections (fewer false positives)

**Impact**: Higher threshold = fewer detections = faster processing.

---

#### `max_det` - Maximum Detections
```json
"max_det": 5
```

**Options**:
- `3` - Small dance floor
- `5` - Medium space (recommended)
- `10` - Large space with many dancers

**Impact**: ~10-15% speed improvement per detection reduced.

---

#### `history_frames` - Movement History
```json
"history_frames": 5
```

**Options**:
- `3` - Minimal (fastest, less smooth movement data)
- `5` - Balanced (recommended)
- `10` - Maximum (smoother but slower)

**Impact**: ~5-10% speed improvement (3 vs 10)

**Trade-off**: Fewer frames = less accurate movement calculations.

---

### Display Settings

#### `show_video` - Video Display
```json
"show_video": false
```

**CRITICAL**: Set to `false` on headless Raspberry Pi.

**Impact**: ~30% CPU reduction when disabled.

**When to enable**:
- MacOS/Desktop for debugging
- Never on headless Raspberry Pi

---

### OSC Settings

#### `osc_destinations` - Multiple OSC Targets
```json
"osc_destinations": [
  {
    "host": "127.0.0.1",
    "port": 5005,
    "description": "Cosmic Skeleton Visualizer"
  },
  {
    "host": "192.168.1.100",
    "port": 8000,
    "description": "Remote Server"
  }
]
```

**Multiple destinations**: Sends same data to all targets.

**Single destination** (backward compatibility):
```json
"osc_host": "127.0.0.1",
"osc_port": 5005
```

---

#### `message_interval` - Update Frequency
```json
"message_interval": 10.0
```

**Options**:
- `5.0` - Update every 5 seconds (more frequent)
- `10.0` - Update every 10 seconds (recommended)
- `30.0` - Update every 30 seconds (less frequent)

**Note**: This is for movement statistics, not keypoint data (which sends every processed frame).

---

## Creating Custom Configurations

### Example: Ultra-Fast Mode for 30+ FPS
```json
{
  "model": "yolov8n-pose.pt",
  "imgsz": 256,
  "skip_frames": 3,
  "camera_width": 640,
  "camera_height": 360,
  "camera_fps": 15,
  "conf_threshold": 0.5,
  "max_det": 2,
  "history_frames": 2,
  "show_video": false
}
```

**Result**: ~30-35 FPS but very low quality detection.

---

### Example: Quality Mode for MacOS
```json
{
  "model": "yolov8s-pose.pt",
  "imgsz": 640,
  "skip_frames": 0,
  "camera_width": 1280,
  "camera_height": 720,
  "camera_fps": 30,
  "conf_threshold": 0.25,
  "max_det": 10,
  "history_frames": 10,
  "show_video": true
}
```

**Result**: ~15-20 FPS on MacOS with excellent accuracy.

---

## Tuning Tips

### If FPS is Too Low
1. ✅ Decrease `imgsz` (416 → 320)
2. ✅ Increase `skip_frames` (1 → 2)
3. ✅ Set `show_video: false`
4. ✅ Reduce `camera_width` and `camera_height`
5. ✅ Reduce `max_det` (5 → 3)
6. ✅ Reduce `history_frames` (5 → 3)

### If Detection is Inaccurate
1. ✅ Increase `imgsz` (320 → 416)
2. ✅ Decrease `conf_threshold` (0.35 → 0.25)
3. ✅ Decrease `skip_frames` (2 → 1)
4. ✅ Increase camera resolution
5. ✅ Use better model (`yolov8s-pose.pt`)

### If Temperature is Too High (>80°C)
1. ✅ Use `config_rpi_max_performance.json`
2. ✅ Add active cooling (fan)
3. ✅ Reduce `camera_fps`
4. ✅ Increase `skip_frames`

---

## Testing Configurations

### Quick Test
```bash
# Run for 30 seconds and observe FPS
python src/dance_movement_detector.py --config config/test_config.json --no-display
# Press Ctrl+C after 30 seconds
```

### Monitor Performance
```bash
# Terminal 1: Run detector
./start_detector_rpi.sh config/config_rpi_max_performance.json

# Terminal 2: Monitor CPU
htop

# Terminal 3: Monitor temperature
watch -n 2 vcgencmd measure_temp
```

---

## Configuration Comparison Table

| Parameter | Max Performance | Balanced | High Quality |
|-----------|----------------|----------|--------------|
| **model** | yolov8n | yolov8n | yolov8n |
| **imgsz** | 320 | 416 | 640 |
| **skip_frames** | 2 | 1 | 0 |
| **camera_res** | 640x480 | 640x480 | 1280x720 |
| **camera_fps** | 15 | 15 | 30 |
| **max_det** | 3 | 5 | 10 |
| **conf_threshold** | 0.4 | 0.35 | 0.25 |
| **history_frames** | 3 | 5 | 10 |
| **show_video** | false | false | true/false |
| **Expected FPS (RPi4)** | 20-25 | 12-18 | 5-8 |
| **CPU Usage** | 40-50% | 50-70% | 80-100% |
| **Accuracy** | Low-Medium | Medium-High | High |

---

## Command-Line Overrides

You can override config file settings from the command line:

```bash
# Override video source
python src/dance_movement_detector.py \
  --config config/config_rpi_optimized.json \
  --video /path/to/video.mp4

# Override OSC settings
python src/dance_movement_detector.py \
  --config config/config_rpi_optimized.json \
  --osc-host 192.168.1.100 \
  --osc-port 8000

# Override message interval
python src/dance_movement_detector.py \
  --config config/config_rpi_optimized.json \
  --interval 5.0

# Force display off
python src/dance_movement_detector.py \
  --config config/config.json \
  --no-display
```

---

## Troubleshooting

### Config file not found
```bash
# Check config file exists
ls -la config/

# Use absolute path
python src/dance_movement_detector.py \
  --config /home/hordia/dev/crowdstream-audio/dance_movement_detector/config/config_rpi_optimized.json
```

### Settings not taking effect
1. Check JSON syntax (use `jq` to validate):
   ```bash
   jq . config/config_rpi_optimized.json
   ```

2. Restart the detector after changing config

3. Check for typos in parameter names (case-sensitive)

### Performance still poor
1. Make sure you're using the right config:
   ```bash
   # Should see "Using config: config/config_rpi_max_performance.json"
   ./start_detector_rpi.sh config/config_rpi_max_performance.json
   ```

2. Check system resources:
   ```bash
   # Temperature
   vcgencmd measure_temp

   # Throttling
   vcgencmd get_throttled
   # 0x0 = good, anything else = throttling

   # Memory
   free -h
   ```

---

## Best Practices

1. ✅ **Start with balanced config**, then adjust
2. ✅ **Always disable display on headless** Raspberry Pi
3. ✅ **Use version control** for custom configs
4. ✅ **Document changes** in config comments
5. ✅ **Test thoroughly** before live shows
6. ✅ **Monitor temperature** during long runs
7. ✅ **Keep configs in sync** across machines

---

## Example Workflow

### For Live Performance

```bash
# 1. Test setup with balanced config
./start_detector_rpi.sh config/config_rpi_optimized.json

# 2. If smooth, great! If not, switch to max performance
./start_detector_rpi.sh config/config_rpi_max_performance.json

# 3. Run for 5 minutes, monitor temperature
watch -n 2 vcgencmd measure_temp

# 4. If stable, you're good to go!
```

### For Development/Testing

```bash
# On MacOS: Use quality mode with display
python src/dance_movement_detector.py \
  --config config/config.json

# On Raspberry Pi: Use balanced mode without display
./start_detector_rpi.sh config/config_rpi_optimized.json
```

---

## Summary

- **3 pre-made configs** for different use cases
- **Max Performance**: 20-25 FPS, lower accuracy
- **Balanced**: 12-18 FPS, good accuracy (recommended)
- **High Quality**: 5-8 FPS, best accuracy
- **Easy to switch**: Just change config file parameter
- **All settings documented** with impact and trade-offs

Choose the config that matches your needs, or create a custom one using this guide as reference!
