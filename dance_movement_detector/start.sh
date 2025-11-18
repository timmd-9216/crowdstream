#!/bin/bash

# Dance Movement Detector - Startup Script

# Change to script directory
cd "$(dirname "$0")"

echo "=== Dance Movement Detector ==="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo ""
echo "Starting dance movement detector..."
echo "Default settings:"
echo "  - Message interval: 10 seconds"
echo "  - OSC destination: 127.0.0.1:5005"
echo "  - Video source: Webcam (0)"
echo ""
echo "Usage examples:"
echo "  ./start.sh                           # Use webcam with defaults"
echo "  ./start.sh --video video.mp4         # Use video file"
echo "  ./start.sh --interval 5              # Send messages every 5 seconds"
echo "  ./start.sh --osc-host 192.168.1.100  # Send to different host"
echo "  ./start.sh --no-display              # Run without video display"
echo ""

# Run the detector with any passed arguments
python3 src/dance_movement_detector.py "$@"
