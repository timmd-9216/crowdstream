#!/bin/bash

# Setup script for NVIDIA Jetson TX1
# Ubuntu 16.04 with Python 3.5.2 (default system Python)

set -e

echo "=== CrowdStream Setup for Jetson TX1 ==="
echo ""

# Detect if running on Jetson
JETSON_MODEL=""
if [ -f /etc/nv_tegra_release ]; then
    echo "✓ Detected NVIDIA Jetson device"
    JETSON_MODEL=$(cat /etc/nv_tegra_release | head -1)
    echo "  $JETSON_MODEL"
elif [ -f /proc/device-tree/model ]; then
    MODEL=$(cat /proc/device-tree/model)
    if [[ $MODEL == *"Jetson"* ]]; then
        echo "✓ Detected Jetson device: $MODEL"
        JETSON_MODEL=$MODEL
    fi
fi

echo ""
echo "Python version check:"
python3 --version

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if [[ "$PYTHON_VERSION" != "3.5" ]]; then
    echo "⚠️  Warning: This script is optimized for Python 3.5.2"
    echo "   Detected: Python $PYTHON_VERSION"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "Step 1: Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    python3-setuptools \
    curl \
    git \
    build-essential \
    pkg-config

echo ""
echo "Step 2: Installing OpenCV and system dependencies..."
# Jetson TX1 uses libopencv4tegra from NVIDIA repo (not python3-opencv)
sudo apt-get install -y \
    libopencv4tegra \
    libopencv4tegra-dev \
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
    gfortran \
    libjpeg8-dev \
    libpng12-dev \
    libtiff5-dev \
    || echo "⚠️  Some packages may not be available, continuing..."

echo ""
echo "Step 3: Upgrading pip for Python 3.5..."
# Use older pip compatible with Python 3.5
sudo -H python3 -m pip install --upgrade "pip<21.0"
sudo -H python3 -m pip install --upgrade setuptools wheel

echo ""
echo "Step 4: Installing PyTorch for Jetson..."
# Check if PyTorch is already installed
if python3 -c "import torch" 2>/dev/null; then
    echo "  ✓ PyTorch already installed"
    python3 -c "import torch; print(f'  PyTorch version: {torch.__version__}')"
else
    echo "  ⚠️  PyTorch not found. Manual installation required."
    echo ""
    echo "  Download PyTorch wheel for Jetson TX1 from:"
    echo "  https://forums.developer.nvidia.com/t/pytorch-for-jetson/72048"
    echo ""
    echo "  Install with:"
    echo "    wget https://nvidia.box.com/shared/static/xxx.whl"
    echo "    pip3 install torch-1.1.0-*.whl"
    echo ""
    read -p "Skip PyTorch installation and continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "Step 5: Creating virtual environments for services..."

# Dance Movement Detector
if [ -d "dance_movement_detector" ]; then
    echo "  - dance_movement_detector"
    cd dance_movement_detector
    python3 -m venv venv --system-site-packages
    source venv/bin/activate
    pip install --upgrade "pip<21.0"
    echo "    Installing requirements..."
    pip install -r requirements.txt || echo "⚠️  Some packages failed, check requirements manually"
    deactivate
    cd ..
fi

# Dance Dashboard Alt (Flask-based for Python 3.5)
if [ -d "dance_dashboard_alt" ]; then
    echo "  - dance_dashboard_alt"
    cd dance_dashboard_alt
    python3 -m venv venv --system-site-packages
    source venv/bin/activate
    pip install --upgrade "pip<21.0"
    echo "    Installing requirements..."
    pip install -r requirements.txt || echo "⚠️  Some packages failed, check requirements manually"
    deactivate
    cd ..
fi

# Cosmic Journey
if [ -d "cosmic_journey" ]; then
    echo "  - cosmic_journey"
    cd cosmic_journey
    python3 -m venv venv --system-site-packages
    source venv/bin/activate
    pip install --upgrade "pip<21.0"
    echo "    Installing requirements..."
    pip install -r requirements.txt || echo "⚠️  Some packages failed, check requirements manually"
    deactivate
    cd ..
fi

echo ""
echo "Step 6: Creating logs directory..."
mkdir -p logs

echo ""
echo "Step 7: Checking camera access..."
if [ -e /dev/video0 ]; then
    echo "  ✓ Camera device found: /dev/video0"
    ls -l /dev/video0
else
    echo "  ⚠️  No camera found at /dev/video0"
    echo "  Available video devices:"
    ls -l /dev/video* 2>/dev/null || echo "  None"
fi

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "System Information:"
echo "  Platform: $(uname -m)"
echo "  Kernel: $(uname -r)"
echo "  Python: $(python3 --version)"
if [ -n "$JETSON_MODEL" ]; then
    echo "  Jetson: $JETSON_MODEL"
fi
echo ""
echo "To start all services:"
echo "  ./start-all-services.sh"
echo ""
echo "Individual services:"
echo "  cd dance_dashboard_alt && venv/bin/python3 src/server.py"
echo "  cd cosmic_journey && venv/bin/python3 src/cosmic_server.py"
echo "  cd dance_movement_detector && venv/bin/python3 src/dance_movement_detector.py"
echo ""
echo "Performance Tips for Jetson TX1:"
echo "  - Use CUDA-accelerated OpenCV when possible"
echo "  - Enable NVP model (sudo nvpmodel -m 0)"
echo "  - Monitor temperature (tegrastats)"
echo "  - Use onboard camera for better performance"
echo ""
