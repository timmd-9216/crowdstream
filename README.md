# CrowdStream - Real-Time Movement Detection and Visualization System

A complete system for detecting dancer movement using YOLO v8, with real-time visualization, monitoring dashboard, and interactive audio mixing.

## 🎯 Launch Performance - Quick Start

**To launch a complete performance, run these two commands:**

### 1. Detector de Movimiento y Visuales

```bash
./scripts/perfo-start.sh
```

This starts:
- 🤖 **Movement Detector** - Detects people and analyzes movement
- 💀 **Skeleton Visualizer** (`cosmic_skeleton`) - Real-time visualization
- 📊 **Monitoring Dashboard** (`movement_dashboard`) - Statistics and graphs

**Available Interfaces:**
- 📊 **Dashboard**: http://localhost:8082
- 💀 **Skeleton Visualizer**: http://localhost:8091

### 2. Mezcla de Audio que Evoluciona según Movimiento

```bash
./scripts/audio-mix-start.sh
```

This starts:
- 🎛️ **Audio Server** - Mixing engine with EQ filters
- 🎵 **Interactive Mixer** - Receives OSC movement messages and adjusts mix in real-time based on dancer movement

**Ports:**
- Audio Server OSC: 57122
- Movement OSC: 57120 (receives from detector)

---

## 🚀 Installation

### Virtual Environment Installation

Each service has its own virtual environment. To install all of them:

```bash
./scripts/setup-all-venvs.sh
```

This script creates virtual environments for:
- `movement_dashboard/venv` - Monitoring dashboard
- `visualizers/cosmic_skeleton/venv` - Skeleton visualizer
- `visualizers/skeleton_visualizer/venv` - Alternative skeleton visualizer
- `visualizers/cosmic_journey/venv` - Cosmic journey visualizer
- `visualizers/space_visualizer/venv` - Space visualizer
- `dance_movement_detector/venv` - Movement detector
- `audio-mixer/venv` - Audio mixer

Each service can also be installed individually by running `./install.sh` inside its directory (for `audio-mixer` use `./scripts/audio-mixer-install.sh`).

### Stopping All Services

```bash
./scripts/kill-all-services.sh  # Stops detector, visualizers, and dashboard
./scripts/kill_audio.sh         # Stops audio mixer
```

### Docker Deployment

To run all services in Docker containers:

```bash
cd docker
./docker-start.sh
```

Or from the project root:

```bash
./docker/docker-start.sh
```

See [docker/README.md](docker/README.md) for detailed Docker documentation.

## 📁 System Components

### 1. 🤖 Movement Detector (`dance_movement_detector/`)
- Detects people using YOLO v8 Pose
- Analyzes movement of arms, legs, and head
- **Bounding box normalization**: Movement is normalized by bounding box size, making it independent of camera distance
- Sends data via OSC to multiple destinations

**OSC Output Port**: Sends to ports 5005, 5007, and 57120

**Normalized Movement:**
- Movement values are relative to person size (normalized)
- Independent of camera distance
- Typical values: 0.0 (no movement) to 0.6+ (very intense movement)

### 2. 📊 Dashboard (`movement_dashboard/`)
- Real-time statistics visualization
- Historical graphs with Chart.js
- Accumulated statistics
- Implemented with FastAPI and native WebSockets

**Ports**: OSC 5005, Web 8082

### 3. 💀 Visualizers (`visualizers/`)
All visualizers are organized in the `visualizers/` folder:

- **`cosmic_skeleton/`** - Cosmic skeleton visualization (port 8091)
- **`skeleton_visualizer/`** - Basic skeleton visualizer (port 8093)
- **`cosmic_journey/`** - 3D cosmic journey (port 8091)
- **`space_visualizer/`** - 3D space visualization with Three.js (port 8090)
- **`blur_skeleton_visualizer/`** - Skeleton with blur effect (port 8092)
- **`cosmic_skeleton_standalone/`** - Skeleton with integrated detector (port 8094)

All receive OSC movement messages and react in real-time.

### 4. 🎵 Audio Mixer (`audio-mixer/`)
- Interactive audio mixer that receives movement messages
- **Automatic BPM adjustment** based on detected movement
- Adjusts EQ filters (low/mid/high) based on movement
- Mixes multiple tracks with smooth transitions
- EQ filters with smooth interpolation (50ms default)

**Movement-Based BPM Control:**

| Movement Level | Threshold | Target BPM |
|----------------|-----------|------------|
| Very very low  | < 2%      | 105 BPM    |
| Very low       | 2-5%      | 110 BPM    |
| Low            | 5-10%     | 115 BPM    |
| Medium-low     | 10-15%    | 118 BPM    |
| High           | ≥ 15%     | 118→130 BPM (progressive) |

- **Low movement** → BPM gradually decreases: 118 → 115 → 113 → 110
- **High movement** → BPM progressively increases up to 130 BPM
- **Transitions** take ~30 seconds for smooth, musical changes

**Ports**: 
- Audio Server OSC: 57122
- Movement OSC: 57120 (receives from detector)

## 🎯 Data Flow

```
📹 Camera/Video
    ↓
🤖 YOLO v8 Detector
    ↓ (OSC Messages)
    ├─→ Port 5005 → 📊 Dashboard (8082)
    ├─→ Port 5007 → 💀 Skeleton Visualizers (8091, 8093)
    └─→ Port 57120 → 🎵 Audio Mixer (57122)
```

## ⚙️ Port Configuration

**Why does each service need its own OSC port?**

Only one service can listen on a port at a time. Therefore:
- Dashboard listens on OSC port **5005**
- Visualizers listen on OSC port **5007**
- Audio Mixer listens on OSC port **57120**
- Detector **sends to all** simultaneously

| Service | OSC Port (input) | Web Port (output) |
|---------|------------------|-------------------|
| Dashboard | 5005 | 8082 |
| Skeleton Visualizers | 5007 | 8091, 8093 |
| Audio Mixer | 57120 | - |
| Detector | Sends to multiple ports | - |

## 📚 Additional Documentation

- [docs/README_SISTEMA_COMPLETO.md](docs/README_SISTEMA_COMPLETO.md) - Complete system documentation (Spanish)
- [docs/QUICK_START.md](docs/QUICK_START.md) - Quick start guide
- [docs/MAPPING_CONFIG.md](docs/MAPPING_CONFIG.md) - Visual mapping configuration
- [docs/RASPBERRY_PI_SETUP.md](docs/RASPBERRY_PI_SETUP.md) - Raspberry Pi setup
- Each component has its own README in its directory

## 🔧 Troubleshooting

### "Address already in use"
```bash
./scripts/kill-all-services.sh
# Wait 2 seconds
./scripts/perfo-start.sh
```

### Detector not detecting movement
- Verify camera is working
- Check `logs/detector.log`
- Try with `--show-video` to see detections

### Dashboard/Visualizer not updating
- Verify WebSocket connection (green indicator in UI)
- Check that detector is sending to correct ports
- Check `logs/` for errors

### View running processes
```bash
ps aux | grep -E "(detector|dashboard|visualizer|audio)" | grep -v grep
```

### View ports in use
```bash
lsof -i:5005
lsof -i:5007
lsof -i:57120
lsof -i:8082
lsof -i:8091
```

### Performance issues with real-time EQ filters

If you experience **audio glitches, stuttering, or high CPU usage** when EQ filters are enabled:

**Raspberry Pi:**
- EQ filters are **disabled by default** on Raspberry Pi for performance
- If you enabled them with `--enable-filters` and experience issues, disable them:
  ```bash
  # Remove --enable-filters flag from audio-mix-start.sh
  python audio_server.py --port 57122  # Without --enable-filters
  ```

**Mac M1:**
- EQ filters are **disabled by default** on Mac M1 for performance
- Real-time EQ processing can cause audio dropouts and high CPU usage
- To disable filters:
  ```bash
  python audio_server.py --port 57122  # Filters disabled by default on M1
  ```

**General recommendations:**
- Use filters only on more powerful systems (M2 Pro/Max, desktop CPUs)
- If you need EQ control, consider using external hardware or software EQs
- Monitor CPU usage: `top` or `htop` to verify impact
- Increase buffer size if using filters: `--buffer-size 2048` (higher latency but more stable)

## 📜 License

Academic project - FIUBA Seminar

## 🔗 Links

- YOLO v8: https://docs.ultralytics.com/
- Three.js: https://threejs.org/
- Chart.js: https://www.chartjs.org/
- python-osc: https://pypi.org/project/python-osc/
- FastAPI: https://fastapi.tiangolo.com/

