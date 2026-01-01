#!/bin/bash

# Kill All Dance Movement Services
# Stops all running detector, dashboard, visualizer, and controller services

# Function to detect Raspberry Pi
is_raspberry_pi() {
    if [ -f /proc/cpuinfo ]; then
        if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null || grep -q "BCM" /proc/cpuinfo 2>/dev/null; then
            return 0
        fi
    fi
    if [ -f /sys/firmware/devicetree/base/model ]; then
        if grep -qi "raspberry" /sys/firmware/devicetree/base/model 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# Function to sleep only on Raspberry Pi
sleep_if_rpi() {
    local duration=$1
    if is_raspberry_pi; then
        sleep "$duration"
    fi
}

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
        sleep_if_rpi 0.5

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
kill_service "FastAPI Dashboard" "movement_dashboard/src/server.py"
kill_service "Cosmic Skeleton" "visualizers/cosmic_skeleton/src/server.py"
kill_service "Cosmic Journey" "visualizers/cosmic_journey/src/cosmic_server.py"
kill_service "Space Visualizer" "visualizers/space_visualizer/src/visualizer_server.py"
kill_service "Blur Skeleton Visualizer" "visualizers/blur_skeleton_visualizer/src/server.py"
kill_service "Service Controller" "service_manager.py"

echo ""
echo "=== Verifying Ports ==="

# Check if ports are free and kill processes using them
for port in 5005 5006 5007 5008 5009 8000 8080 8081 8082 8090 8091 8092; do
    pids=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pids" ]; then
        echo "⚠ Port $port still in use (PIDs: $pids)"
        echo "  Killing processes on port $port..."
        echo "$pids" | xargs kill 2>/dev/null
        sleep_if_rpi 0.5
        # Force kill if still running
        remaining=$(lsof -ti:$port 2>/dev/null)
        if [ ! -z "$remaining" ]; then
            echo "  Force killing processes on port $port..."
            echo "$remaining" | xargs kill -9 2>/dev/null
        fi
        echo "✓ Port $port is now free"
    else
        echo "✓ Port $port is free"
    fi
done

echo ""
echo "All services stopped!"
