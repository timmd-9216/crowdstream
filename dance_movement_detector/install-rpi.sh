#!/bin/bash

# Install dependencies for Movement Detector on Raspberry Pi
# Uses opencv-python-headless for Raspberry Pi compatibility

set -e

echo "🤖 Installing Movement Detector dependencies for Raspberry Pi..."
cd "$(dirname "$0")"

# Remove existing venv if present
if [ -d "venv" ]; then
    echo "  Removing existing venv..."
    rm -rf venv
fi

# Create venv
echo "  Creating virtual environment..."
python3 -m venv venv

# Upgrade pip
echo "  Upgrading pip..."
venv/bin/pip install --upgrade pip

# Install requirements with opencv-python-headless
if [ -f "requirements.txt" ]; then
    echo "  Installing requirements (with opencv-python-headless)..."
    # Replace opencv-python with opencv-python-headless
    grep -v "opencv-python" requirements.txt > /tmp/requirements_rpi.txt || true
    if grep -q "opencv-python" requirements.txt; then
        echo "opencv-python-headless>=4.8.0" >> /tmp/requirements_rpi.txt
    fi
    venv/bin/pip install -r /tmp/requirements_rpi.txt
    rm /tmp/requirements_rpi.txt
    echo "  ✅ Installation complete"
else
    echo "  ⚠️  No requirements.txt found"
    exit 1
fi

echo ""
echo "Virtual environment ready at: venv/"
echo "To activate: source venv/bin/activate"
echo ""
echo "Testing cv2 availability..."
venv/bin/python -c "import cv2; print(f'  OpenCV version: {cv2.__version__}')"
echo ""
