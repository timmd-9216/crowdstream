#!/bin/bash

# Start All Dance Movement Services
# Starts detector, dashboard, and visualizer with correct port configuration

echo "=== Starting All Dance Movement Services ==="
echo ""

# Change to script directory
cd "$(dirname "$0")"

# Kill any existing services first
echo "Stopping any existing services..."
./kill-all-services.sh
sleep 2

echo ""
echo "=== Starting Services ==="
echo ""

# Start Dashboard (OSC: 5005, Web: 8081)
echo "Starting Dashboard..."
cd dance_dashboard
if [ -d "venv" ]; then
    venv/bin/python3 src/dashboard_server.py --osc-port 5005 --web-port 8081 > ../logs/dashboard.log 2>&1 &
else
    python3 src/dashboard_server.py --osc-port 5005 --web-port 8081 > ../logs/dashboard.log 2>&1 &
fi
DASHBOARD_PID=$!
echo "  Dashboard started (PID: $DASHBOARD_PID) on http://localhost:8081"
cd ..
sleep 2

# Start Visualizer (OSC: 5006, Web: 8090)
echo "Starting Space Visualizer..."
cd space_visualizer
if [ -d "venv" ]; then
    venv/bin/python3 src/visualizer_server.py --osc-port 5006 --web-port 8090 > ../logs/visualizer.log 2>&1 &
else
    python3 src/visualizer_server.py --osc-port 5006 --web-port 8090 > ../logs/visualizer.log 2>&1 &
fi
VISUALIZER_PID=$!
echo "  Visualizer started (PID: $VISUALIZER_PID) on http://localhost:8090"
cd ..
sleep 2

# Start Detector (sends to both ports)
echo "Starting Movement Detector..."
cd dance_movement_detector
if [ -d "venv" ]; then
    venv/bin/python3 src/dance_movement_detector.py --config config/multi_destination.json > ../logs/detector.log 2>&1 &
else
    python3 src/dance_movement_detector.py --config config/multi_destination.json > ../logs/detector.log 2>&1 &
fi
DETECTOR_PID=$!
echo "  Detector started (PID: $DETECTOR_PID)"
cd ..
sleep 2

echo ""
echo "=== All Services Started ==="
echo ""
echo "📊 Dashboard:   http://localhost:8081  (OSC: 5005)"
echo "🌌 Visualizer:  http://localhost:8090  (OSC: 5006)"
echo "🤖 Detector:    Sending to both OSC ports"
echo ""
echo "Process IDs:"
echo "  Dashboard:  $DASHBOARD_PID"
echo "  Visualizer: $VISUALIZER_PID"
echo "  Detector:   $DETECTOR_PID"
echo ""
echo "To view logs:"
echo "  tail -f logs/dashboard.log"
echo "  tail -f logs/visualizer.log"
echo "  tail -f logs/detector.log"
echo ""
echo "To stop all services:"
echo "  ./kill-all-services.sh"
echo ""
