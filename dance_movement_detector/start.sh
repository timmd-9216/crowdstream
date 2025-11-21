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
echo "  - Config: config/multi_destination.json"
echo "  - Message interval: 1 second"
echo "  - OSC destinations:"
echo "    • 127.0.0.1:5005 (Dashboard)"
echo "    • 127.0.0.1:5006 (Space Visualizer)"
echo "    • 127.0.0.1:5007 (Skeleton Visualizer)"
echo "    • 127.0.0.1:5008 (Cosmic Skeleton Visualizer)"
echo "  - Video source: Webcam (0)"
echo ""
echo "Usage examples:"
echo "  ./start.sh                           # Use webcam with multi-destination"
echo "  ./start.sh --video video.mp4         # Use video file"
echo "  ./start.sh --interval 5              # Send messages every 5 seconds"
echo "  ./start.sh --no-display              # Run without video display"
echo "  ./start.sh --config config/config.json  # Use single destination"
echo ""

# Run the detector with multi-destination config by default
python3 src/dance_movement_detector.py --config config/multi_destination.json "$@"
