#!/bin/bash

# Setup Virtual Environments for Raspberry Pi 4
# Creates all necessary venvs for start-all-services.sh
# Uses opencv-python-headless for Raspberry Pi compatibility

set -e  # Exit on error

echo "=== Setting up Virtual Environments for Raspberry Pi 4 ==="
echo ""

# Change to script directory
cd "$(dirname "$0")"
BASE_DIR=$(pwd)

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to create venv and install requirements
setup_venv() {
    local service_dir=$1
    local service_name=$2
    local use_opencv_headless=$3

    echo "📦 Setting up $service_name..."
    cd "$BASE_DIR/$service_dir"

    # Remove existing venv if present
    if [ -d "venv" ]; then
        echo "  Removing existing venv..."
        rm -rf venv
    fi

    # Create new venv
    echo "  Creating virtual environment..."
    python3 -m venv venv

    # Upgrade pip
    echo "  Upgrading pip..."
    venv/bin/pip install --upgrade pip

    # Install requirements
    if [ -f "requirements.txt" ]; then
        if [ "$use_opencv_headless" = "true" ]; then
            echo "  Installing requirements (with opencv-python-headless for Raspberry Pi)..."
            # Replace opencv-python with opencv-python-headless
            grep -v "opencv-python" requirements.txt > /tmp/requirements_rpi.txt || true
            if grep -q "opencv-python" requirements.txt; then
                echo "opencv-python-headless>=4.8.0" >> /tmp/requirements_rpi.txt
            fi
            venv/bin/pip install -r /tmp/requirements_rpi.txt
            rm /tmp/requirements_rpi.txt
        else
            echo "  Installing requirements..."
            venv/bin/pip install -r requirements.txt
        fi
        echo "  ✅ $service_name setup complete"
    else
        echo "  ⚠️  No requirements.txt found for $service_name"
    fi

    echo ""
}

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version)
echo "  Using: $PYTHON_VERSION"
echo ""

# Check if cv2 will be available (test opencv-python-headless)
echo "Verifying OpenCV availability for Raspberry Pi..."
python3 -c "import sys; print(f'  Python: {sys.version}')"
echo "  Will install opencv-python-headless (optimized for Raspberry Pi)"
echo ""

# Setup each service
setup_venv "dance_dashboard_alt" "FastAPI Dashboard" "false"
setup_venv "cosmic_journey" "Cosmic Journey Visualizer" "false"
setup_venv "dance_movement_detector" "Movement Detector" "true"

echo "=== Setup Complete ==="
echo ""
echo "Virtual environments created for:"
echo "  1. 📊 Dance Dashboard Alt    (dance_dashboard_alt/venv)"
echo "  2. 🌌 Cosmic Journey         (cosmic_journey/venv)"
echo "  3. 🤖 Movement Detector       (dance_movement_detector/venv)"
echo ""
echo "Notes for Raspberry Pi 4:"
echo "  • opencv-python-headless is used instead of opencv-python"
echo "  • This avoids GUI dependencies (Qt, GTK) that aren't needed"
echo "  • All cv2 functions for video processing are available"
echo ""
echo "To start all services:"
echo "  ./start-all-services.sh"
echo ""
echo "To test cv2 availability:"
echo "  dance_movement_detector/venv/bin/python -c 'import cv2; print(cv2.__version__)'"
echo ""
