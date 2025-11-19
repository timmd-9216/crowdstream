#!/bin/bash

# Kill All Dance Movement Services
# Stops all running detector, dashboard, visualizer, and controller services

echo "=== Stopping All Dance Movement Services ==="
echo ""

# Function to kill processes by name pattern
kill_service() {
    local name=$1
    local pattern=$2

    pids=$(ps aux | grep "$pattern" | grep -v grep | awk '{print $2}')

    if [ -z "$pids" ]; then
        echo "✓ $name: No processes running"
    else
        echo "⚠ $name: Stopping processes..."
        echo "$pids" | xargs kill 2>/dev/null
        sleep 0.5

        # Force kill if still running
        remaining=$(ps aux | grep "$pattern" | grep -v grep | awk '{print $2}')
        if [ ! -z "$remaining" ]; then
            echo "  Force killing remaining processes..."
            echo "$remaining" | xargs kill -9 2>/dev/null
        fi
        echo "✓ $name: Stopped"
    fi
}

# Kill services
kill_service "Dance Movement Detector" "dance_movement_detector.py"
kill_service "Dashboard Server" "dashboard_server.py"
kill_service "Space Visualizer" "visualizer_server.py"
kill_service "Service Controller" "service_manager.py"

echo ""
echo "=== Verifying Ports ==="

# Check if ports are free
for port in 5005 5006 5007 8000 8080 8081 8090; do
    if lsof -ti:$port > /dev/null 2>&1; then
        echo "⚠ Port $port still in use"
    else
        echo "✓ Port $port is free"
    fi
done

echo ""
echo "All services stopped!"
