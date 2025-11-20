#!/bin/bash

# Dance Movement Dashboard - Startup Script

# Change to script directory
cd "$(dirname "$0")"

echo "=== Dance Movement Dashboard ==="
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
echo "Starting dashboard server..."
echo "Default settings:"
echo "  - OSC listening port: 5005"
echo "  - Web dashboard port: 8081"
echo "  - Dashboard URL: http://localhost:8081"
echo ""
echo "Usage examples:"
echo "  ./start.sh                           # Use defaults (OSC: 5005, Web: 8081)"
echo "  ./start.sh --osc-port 5005 --web-port 8081  # Specify ports explicitly"
echo "  ./start.sh --osc-port 7000           # Listen on different OSC port"
echo "  ./start.sh --web-port 9090           # Use different web port"
echo "  ./start.sh --history 200             # Keep 200 data points in history"
echo ""
echo "Open your browser to: http://localhost:8081"
echo ""

# Run the dashboard server with any passed arguments
python3 src/dashboard_server.py "$@"
