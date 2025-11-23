#!/bin/bash

# Setup script for Ubuntu 16.04 (AMD64)
# Installs Python 3.8 and all dependencies for CrowdStream services

set -e

echo "=== CrowdStream Setup for Ubuntu 16.04 (AMD64) ==="
echo ""

# Check if running on Ubuntu 16.04
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$VERSION_ID" != "16.04" ]; then
        echo "⚠️  Warning: This script is designed for Ubuntu 16.04"
        echo "   Detected: $PRETTY_NAME"
        echo ""
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

echo "Step 1: Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    software-properties-common \
    curl \
    git \
    build-essential

echo ""
echo "Step 2: Adding deadsnakes PPA for Python 3.8..."
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update

echo ""
echo "Step 3: Installing Python 3.8 and development tools..."
sudo apt-get install -y \
    python3.8 \
    python3.8-dev \
    python3.8-distutils \
    python3.8-venv

echo ""
echo "Step 4: Installing OpenCV system dependencies..."
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

echo ""
echo "Step 5: Installing pip for Python 3.8..."
curl https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
python3.8 /tmp/get-pip.py
rm /tmp/get-pip.py

echo ""
echo "Step 6: Upgrading pip and installing wheel..."
python3.8 -m pip install --upgrade pip setuptools wheel

echo ""
echo "Step 7: Creating virtual environments for services..."

# Dance Movement Detector
if [ -d "dance_movement_detector" ]; then
    echo "  - dance_movement_detector"
    cd dance_movement_detector
    python3.8 -m venv venv
    venv/bin/pip install --upgrade pip
    venv/bin/pip install -r requirements.txt
    cd ..
fi

# Dance Dashboard Alt
if [ -d "dance_dashboard_alt" ]; then
    echo "  - dance_dashboard_alt"
    cd dance_dashboard_alt
    python3.8 -m venv venv
    venv/bin/pip install --upgrade pip
    venv/bin/pip install -r requirements.txt
    cd ..
fi

# Cosmic Journey
if [ -d "cosmic_journey" ]; then
    echo "  - cosmic_journey"
    cd cosmic_journey
    python3.8 -m venv venv
    venv/bin/pip install --upgrade pip
    venv/bin/pip install -r requirements.txt
    cd ..
fi

echo ""
echo "Step 8: Creating logs directory..."
mkdir -p logs

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Python version:"
python3.8 --version
echo ""
echo "To start all services:"
echo "  ./start-all-services.sh"
echo ""
echo "Individual services:"
echo "  cd dance_dashboard_alt && venv/bin/python3 src/server.py"
echo "  cd cosmic_journey && venv/bin/python3 src/cosmic_server.py"
echo "  cd dance_movement_detector && venv/bin/python3 src/dance_movement_detector.py"
echo ""
echo "⚠️  Security Warning:"
echo "Ubuntu 16.04 reached End of Life in April 2021"
echo "Consider upgrading to Ubuntu 20.04 LTS or 22.04 LTS"
echo ""
