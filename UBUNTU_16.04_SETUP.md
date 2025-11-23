# Ubuntu 16.04 Setup Guide (Without Docker)

## Quick Start

```bash
# Run the automated setup script
./setup-ubuntu-16.04.sh

# Start all services
./start-all-services.sh
```

## What the Setup Script Does

1. **Installs Python 3.8** from deadsnakes PPA (Ubuntu 16.04 has Python 3.5 by default)
2. **Installs system dependencies** for OpenCV, NumPy, and video processing
3. **Creates virtual environments** for each service
4. **Installs Python packages** with versions compatible with Ubuntu 16.04

## Manual Installation

If you prefer manual control:

### Step 1: Install Python 3.8

```bash
sudo apt-get update
sudo apt-get install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.8 python3.8-dev python3.8-distutils python3.8-venv
```

### Step 2: Install System Dependencies

```bash
sudo apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgstreamer1.0-0 \
    libavcodec-ffmpeg56 \
    libavformat-ffmpeg56 \
    libswscale-ffmpeg3 \
    libgtk2.0-0 \
    libatlas-base-dev \
    gfortran
```

### Step 3: Install pip

```bash
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3.8 get-pip.py
rm get-pip.py
```

### Step 4: Setup Each Service

**Dance Movement Detector:**
```bash
cd dance_movement_detector
python3.8 -m venv venv
venv/bin/pip install -r requirements.txt
cd ..
```

**Dance Dashboard Alt:**
```bash
cd dance_dashboard_alt
python3.8 -m venv venv
venv/bin/pip install -r requirements.txt
cd ..
```

**Cosmic Journey:**
```bash
cd cosmic_journey
python3.8 -m venv venv
venv/bin/pip install -r requirements.txt
cd ..
```

## Package Versions (Ubuntu 16.04 Compatible)

All `requirements.txt` files have been updated with compatible versions:

### Core ML Libraries
- **ultralytics**: 8.0.196 (YOLOv8 for pose detection)
- **opencv-python-headless**: 4.5.5.64 (last version for glibc 2.23)
- **numpy**: 1.21.6 (compatible with Python 3.8 + old glibc)
- **torch**: 1.13.1 (CPU only)
- **torchvision**: 0.14.1

### Web Frameworks
- **fastapi**: 0.95.2
- **uvicorn**: 0.22.0
- **flask**: 2.3.3
- **flask-socketio**: 5.3.0

### Communication
- **python-osc**: 1.8.3 (OSC protocol support)
- **python-socketio**: 5.9.0

## Starting Services

### All Services at Once
```bash
./start-all-services.sh
```

This starts:
- **Dashboard**: http://localhost:8082 (OSC: 5005)
- **Cosmic Journey**: http://localhost:8091 (OSC: 5007)
- **Detector**: Sends to all OSC ports

### Individual Services

**Dashboard:**
```bash
cd dance_dashboard_alt
venv/bin/python3 src/server.py --osc-port 5005 --web-port 8082
```

**Cosmic Journey:**
```bash
cd cosmic_journey
venv/bin/python3 src/cosmic_server.py --osc-port 5007 --web-port 8091
```

**Movement Detector:**
```bash
cd dance_movement_detector
venv/bin/python3 src/dance_movement_detector.py --config config/multi_destination.json
```

## Stopping Services

```bash
./kill-all-services.sh
```

Or manually:
```bash
pkill -f "dance_movement_detector.py"
pkill -f "cosmic_server.py"
pkill -f "server.py"
```

## Viewing Logs

```bash
tail -f logs/dashboard_alt.log
tail -f logs/cosmic.log
tail -f logs/detector.log
```

## Troubleshooting

### Camera Not Working

```bash
# Check camera device
ls -la /dev/video*

# Test camera access
cd dance_movement_detector
venv/bin/python3 -c "import cv2; print(cv2.VideoCapture(0).read())"
```

### Import Errors

```bash
# Verify Python version
python3.8 --version  # Should be 3.8.x

# Check installed packages
cd dance_movement_detector
venv/bin/pip list

# Reinstall if needed
venv/bin/pip install --force-reinstall -r requirements.txt
```

### OpenCV Issues

If you see `libGL.so` errors:
```bash
sudo apt-get install -y libgl1-mesa-glx libglib2.0-0
```

If camera shows blank screen:
```bash
sudo apt-get install -y libgstreamer1.0-0 libavcodec-ffmpeg56
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8082
lsof -i :8091

# Kill specific process
kill <PID>

# Or use the kill script
./kill-all-services.sh
```

### YOLO Model Download Fails

Models are downloaded automatically on first run to `~/.cache/ultralytics/`

If download fails:
```bash
# Pre-download manually
cd dance_movement_detector
venv/bin/python3 -c "from ultralytics import YOLO; YOLO('yolov8n-pose.pt')"
```

## Performance Notes

On Ubuntu 16.04 with older libraries:
- **Startup time**: ~20-30% slower than modern systems
- **Inference speed**: ~15-25% slower (older PyTorch/OpenCV)
- **Memory usage**: Similar to modern systems
- **Stability**: Good for long-running services

## System Requirements

- **OS**: Ubuntu 16.04 (Xenial) AMD64
- **RAM**: Minimum 4GB, recommended 8GB
- **CPU**: x86_64 with SSE4.2 support
- **Camera**: USB webcam or built-in camera
- **Disk**: ~2GB for all dependencies

## Security Warning

⚠️ **Ubuntu 16.04 reached End of Life on April 30, 2021**

- No security updates available through standard channels
- Only use in isolated/trusted networks
- Consider Ubuntu ESM (Extended Security Maintenance) if available
- Plan migration to Ubuntu 20.04 LTS or 22.04 LTS

## Upgrading from Ubuntu 16.04

When ready to upgrade:

```bash
# Backup your data first!

# Upgrade to 18.04 first (required intermediate step)
sudo do-release-upgrade

# Then to 20.04
sudo do-release-upgrade

# Finally to 22.04 (current LTS)
sudo do-release-upgrade
```

After upgrade, you can use the original `requirements.txt` versions with newer packages.

## Differences from Modern Setup

| Component | Modern | Ubuntu 16.04 | Impact |
|-----------|--------|--------------|--------|
| Python | 3.11 | 3.8 | Some features unavailable |
| OpenCV | 4.8+ | 4.5.5 | Missing newer algorithms |
| NumPy | 1.24+ | 1.21 | Slower operations |
| PyTorch | 2.0+ | 1.13 | Older model format |
| FastAPI | 0.110+ | 0.95 | No automatic docs updates |

## Getting Help

If you encounter issues:

1. Check logs in `logs/` directory
2. Verify Python 3.8 is being used: `python3.8 --version`
3. Ensure all system dependencies are installed
4. Try reinstalling in a fresh virtual environment
5. Check camera permissions and access

## Next Steps

After successful installation:

1. Test camera: Open http://localhost:8082
2. View visualizer: Open http://localhost:8091
3. Monitor logs: `tail -f logs/*.log`
4. Adjust configuration in `dance_movement_detector/config/multi_destination.json`
