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

echo "Starting FastAPI Dashboard..."
cd dance_dashboard_alt
if [ -d "venv" ]; then
    venv/bin/python3 src/server.py --osc-port 5005 --web-port 8082 > ../logs/dashboard_alt.log 2>&1 &
else
    python3 src/server.py --osc-port 5005 --web-port 8082 > ../logs/dashboard_alt.log 2>&1 &
fi
DASHBOARD_PID=$!
echo "  Dashboard (alt) started (PID: $DASHBOARD_PID) on http://localhost:8082"
cd ..
sleep 2

# Start Cosmic Journey Visualizer (OSC: 5007, Web: 8091)
echo "Starting Cosmic Journey Visualizer..."
cd cosmic_journey
if [ -d "venv" ]; then
    venv/bin/python3 src/cosmic_server.py --osc-port 5007 --web-port 8091 > ../logs/cosmic.log 2>&1 &
else
    python3 src/cosmic_server.py --osc-port 5007 --web-port 8091 > ../logs/cosmic.log 2>&1 &
fi
VISUALIZER_PID=$!
echo "  Cosmic Journey started (PID: $VISUALIZER_PID) on http://localhost:8091"
cd ..
sleep 2

# Start Detector (sends to both ports)
echo "Starting Movement Detector..."
cd dance_movement_detector
if [ -d "venv" ]; then
    venv/bin/python3 src/dance_movement_detector.py --interval 1 --config config/multi_destination.json > ../logs/detector.log 2>&1 &
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
echo "📊 Dashboard (alt): http://localhost:8082  (OSC: 5005)"
echo "🌌 Cosmic Journey:  http://localhost:8091  (OSC: 5007)"
echo "🤖 Detector:        Sending to all OSC ports"
echo ""
echo "Process IDs:"
echo "  Dashboard:  $DASHBOARD_PID"
echo "  Visualizer: $VISUALIZER_PID"
echo "  Detector:   $DETECTOR_PID"
echo ""
echo "To view logs:"
echo "  tail -f logs/dashboard_alt.log"
echo "  tail -f logs/cosmic.log"
echo "  tail -f logs/detector.log"
echo ""
echo "To stop all services:"
echo "  ./kill-all-services.sh"
echo ""
