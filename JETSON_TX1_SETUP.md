# Jetson TX1 Setup Guide (Python 3.5.2)

## Hardware Specifications
- **Board**: NVIDIA Jetson TX1
- **OS**: Ubuntu 16.04 LTS (L4T)
- **Python**: 3.5.2 (system default)
- **Architecture**: ARM64 (aarch64)
- **GPU**: NVIDIA Maxwell (256 CUDA cores)

## Quick Start

```bash
# Run the automated setup script
./setup-jetson-tx1.sh

# Start all services
./start-all-services.sh
```

## Important Notes

### Using System Packages

The virtual environments are created with `--system-site-packages` to use Jetson's pre-installed optimized packages:

- **NumPy**: Pre-installed and optimized for ARM64
- **OpenCV**: CUDA-accelerated (libopencv4tegra)

**Do NOT install numpy or opencv-python via pip** - they will fail to compile or be much slower than the system versions.

## Important: Ultralytics Limitation

⚠️ **Ultralytics YOLOv8 requires Python 3.7+**, which is not available on Jetson TX1's default Ubuntu 16.04.

### Alternatives:

1. **Use OpenCV DNN module** (recommended for Jetson TX1)
2. **Use older YOLO versions** (YOLOv3/v4 via darknet)
3. **Use TensorRT** optimized models
4. **Upgrade to JetPack 4.6+** on compatible Jetson (not TX1)

## Package Version Changes

All `requirements.txt` files have been updated for Python 3.5.2 compatibility:

### Core Libraries (Python 3.5.2 Compatible)

| Package | Version | Notes |
|---------|---------|-------|
| numpy | 1.18.5 | Last version for Python 3.5 |
| opencv-python | 4.2.0.32 | Last version for Python 3.5 |
| python-osc | 1.7.4 | OSC protocol support |
| pillow | 6.2.2 | Image processing |
| flask | 1.1.4 | Web framework |
| flask-socketio | 4.3.2 | WebSocket support |
| python-socketio | 4.6.1 | Socket.IO client/server |
| werkzeug | 1.0.1 | WSGI utilities |
| jinja2 | 2.11.3 | Template engine |

### PyTorch on Jetson TX1

PyTorch must be installed manually from NVIDIA:

1. **Download PyTorch wheel** from NVIDIA forums:
   - https://forums.developer.nvidia.com/t/pytorch-for-jetson/72048
   - Use PyTorch 1.1.0 for best compatibility

2. **Install manually**:
```bash
wget https://nvidia.box.com/shared/static/xxx.whl
pip3 install torch-1.1.0-*.whl
pip3 install torchvision-0.3.0-*.whl
```

## Installation Steps

### Option 1: Automated Setup (Recommended)

```bash
./setup-jetson-tx1.sh
```

This script will:
1. Check Jetson device detection
2. Install system dependencies
3. Install pip and required packages
4. Create virtual environments
5. Install service dependencies
6. Set up logging directory

### Option 2: Manual Installation

#### Step 1: Update System

```bash
sudo apt-get update
sudo apt-get upgrade
```

#### Step 2: Install System Dependencies

```bash
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    python3-setuptools \
    python3-opencv \
    libopencv-dev \
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

#### Step 3: Upgrade pip

```bash
# Use pip<21.0 for Python 3.5 compatibility
python3 -m pip install --upgrade "pip<21.0"
python3 -m pip install --upgrade setuptools wheel
```

#### Step 4: Install Service Dependencies

**Dance Movement Detector:**
```bash
cd dance_movement_detector
python3 -m venv venv --system-site-packages
venv/bin/pip install --upgrade "pip<21.0"
venv/bin/pip install -r requirements.txt
cd ..
```

**Dance Dashboard Alt:**
```bash
cd dance_dashboard_alt
python3 -m venv venv --system-site-packages
venv/bin/pip install --upgrade "pip<21.0"
venv/bin/pip install -r requirements.txt
cd ..
```

**Cosmic Journey:**
```bash
cd cosmic_journey
python3 -m venv venv --system-site-packages
venv/bin/pip install --upgrade "pip<21.0"
venv/bin/pip install -r requirements.txt
cd ..
```

#### Step 5: Create Logs Directory

```bash
mkdir -p logs
```

## Running Services

### Start All Services

```bash
./start-all-services.sh
```

This starts:
- **Dashboard**: http://<jetson-ip>:8082 (OSC: 5005)
- **Cosmic Journey**: http://<jetson-ip>:8091 (OSC: 5007)
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

### Stop Services

```bash
./kill-all-services.sh
```

## Performance Optimization

### 1. Enable Max Performance Mode

```bash
# Set to max performance (NVP Model 0)
sudo nvpmodel -m 0

# Set CPU and GPU to max clock
sudo jetson_clocks
```

### 2. Monitor System Resources

```bash
# Real-time stats
tegrastats

# Temperature monitoring
watch -n 1 cat /sys/devices/virtual/thermal/thermal_zone*/temp
```

### 3. Use Onboard Camera

For better performance, use the onboard CSI camera instead of USB:

```python
# In config/multi_destination.json
"video_source": "nvcamerasrc ! video/x-raw(memory:NVMM), width=1280, height=720, framerate=30/1 ! nvvidconv ! video/x-raw, format=BGRx ! videoconvert ! appsink"
```

### 4. Optimize OpenCV

Use CUDA-accelerated OpenCV (pre-installed on Jetson):

```bash
# Check CUDA support
python3 -c "import cv2; print(cv2.getBuildInformation())"
```

## Troubleshooting

### Camera Not Working

```bash
# Check camera devices
ls -l /dev/video*

# Test CSI camera
gst-launch-1.0 nvcamerasrc ! nvoverlaysink

# Test USB camera
v4l2-ctl --list-devices
```

### Out of Memory

Jetson TX1 has 4GB RAM. If running out of memory:

```bash
# Reduce model size
# Use smaller YOLO models or reduce batch size

# Add swap space
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Python Package Installation Fails

```bash
# Use --no-cache-dir to reduce memory usage
pip3 install --no-cache-dir package_name

# Install from system packages when available
sudo apt-get install python3-<package>
```

### OpenCV Import Error

```bash
# Use system OpenCV (already optimized for Jetson)
python3 -c "import cv2; print(cv2.__version__)"

# If using venv, ensure --system-site-packages flag
```

### Thermal Throttling

If system throttles due to heat:

```bash
# Add cooling (fan/heatsink)
# Monitor temperature
watch -n 1 cat /sys/devices/virtual/thermal/thermal_zone*/temp

# If over 80°C, reduce performance
sudo nvpmodel -m 1
```

## Jetson-Specific Features

### Using CUDA

For CUDA-accelerated inference:

```python
import torch
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")
```

### Using TensorRT

For maximum performance, convert models to TensorRT:

```bash
# Install TensorRT (should be pre-installed)
dpkg -l | grep tensorrt

# Use torch2trt for conversion
# https://github.com/NVIDIA-AI-IOT/torch2trt
```

### Using VPI (Vision Programming Interface)

```bash
# Install VPI SDK
sudo apt-get install nvidia-vpi

# Use for accelerated CV operations
# https://docs.nvidia.com/vpi/
```

## Alternative YOLO Implementations

Since Ultralytics doesn't support Python 3.5, use alternatives:

### Option 1: OpenCV DNN with YOLO

```python
import cv2

# Load YOLO model
net = cv2.dnn.readNet("yolov4.weights", "yolov4.cfg")
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
```

### Option 2: Darknet

```bash
git clone https://github.com/AlexeyAB/darknet
cd darknet
# Edit Makefile: GPU=1, CUDNN=1, OPENCV=1
make
```

### Option 3: TensorRT YOLO

Use NVIDIA's optimized implementations:
- https://github.com/NVIDIA-AI-IOT/deepstream_python_apps

## Docker Alternative

For containerized deployment:

```bash
# Build for ARM64
docker build --platform linux/arm64 -t crowdstream-jetson .

# Run with GPU support
docker run --runtime nvidia --network host \
  --device /dev/video0 \
  crowdstream-jetson
```

## Network Access

Access services from other devices:

```bash
# Find Jetson IP
ip addr show

# Access from browser
http://<jetson-ip>:8082  # Dashboard
http://<jetson-ip>:8091  # Cosmic Journey
```

## System Information

Check your Jetson setup:

```bash
# JetPack version
cat /etc/nv_tegra_release

# CUDA version
nvcc --version

# Python version
python3 --version

# Available memory
free -h

# Disk space
df -h
```

## Upgrade Considerations

Jetson TX1 is EOL. Consider upgrading to:
- **Jetson Nano** (similar price, better support)
- **Jetson Xavier NX** (better performance)
- **Jetson Orin Nano** (latest, best performance)

These support JetPack 5.x+ with Python 3.8+ and modern libraries.

## Performance Expectations

On Jetson TX1:
- **YOLO Inference**: 5-10 FPS (with TensorRT optimization)
- **OpenCV Processing**: 15-30 FPS (with CUDA)
- **Python 3.5 Limitations**: Many modern libraries unavailable
- **Memory**: 4GB RAM (tight for ML workloads)

## Resources

- NVIDIA Jetson Forums: https://forums.developer.nvidia.com/c/agx-autonomous-machines/jetson-embedded-systems/
- JetsonHacks: https://jetsonhacks.com/
- PyTorch for Jetson: https://forums.developer.nvidia.com/t/pytorch-for-jetson/72048
- TensorRT: https://developer.nvidia.com/tensorrt

## Security Note

⚠️ **Jetson TX1 uses Ubuntu 16.04 which reached EOL in April 2021**

- No security updates available
- Use only in trusted networks
- Consider upgrading to newer Jetson with JetPack 5.x+
