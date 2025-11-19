#!/bin/bash

# Service Controller - Startup Script

# Change to script directory
cd "$(dirname "$0")"

echo "=== Service Controller ==="
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
echo "Starting Service Controller..."
echo "Default settings:"
echo "  - Web interface port: 8000"
echo "  - Configuration: config/services.json"
echo "  - Base directory: .."
echo ""
echo "Usage examples:"
echo "  ./start.sh                           # Use defaults"
echo "  ./start.sh --port 9000               # Use different port"
echo "  ./start.sh --config custom.json      # Use custom config"
echo ""
echo "Open your browser to: http://localhost:8000"
echo ""

# Run the service controller with any passed arguments
python3 src/service_manager.py "$@"
