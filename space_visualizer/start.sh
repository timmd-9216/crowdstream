#!/bin/bash

# Space Journey Visualizer - Startup Script

# Change to script directory
cd "$(dirname "$0")"

echo "=== Space Journey Visualizer ==="
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
echo "Starting space visualizer..."
echo "Default settings:"
echo "  - OSC listening port: 5005"
echo "  - Web visualizer port: 8090"
echo "  - Visualizer URL: http://localhost:8090"
echo ""
echo "Usage examples:"
echo "  ./start.sh                           # Use defaults"
echo "  ./start.sh --osc-port 7000           # Listen on different OSC port"
echo "  ./start.sh --web-port 9090           # Use different web port"
echo ""
echo "Movement mapping:"
echo "  - Total movement → Travel speed"
echo "  - Arm movement → Color intensity"
echo "  - Leg movement → Warp drive effect"
echo "  - Head movement → Camera rotation"
echo "  - Person count → Star density"
echo ""
echo "Open your browser to: http://localhost:8090"
echo ""

# Run the visualizer server with any passed arguments
python3 src/visualizer_server.py "$@"
