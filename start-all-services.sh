#!/bin/bash

# Start Dance Movement Services
# Starts detector (always) and optionally dashboard and one visualizer

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Start dance movement detector and optional dashboard/visualizer services."
    echo ""
    echo "Options:"
    echo "  --dashboard              Start the FastAPI dashboard (optional)"
    echo "  --visualizer VISUALIZER  Start a visualizer (required, one of):"
    echo "                           - cosmic_skeleton"
    echo "                           - cosmic_journey"
    echo "                           - space_visualizer"
    echo "                           - blur_skeleton"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --visualizer cosmic_skeleton"
    echo "  $0 --dashboard --visualizer space_visualizer"
    echo "  $0 --visualizer cosmic_journey --dashboard"
    echo ""
}

# Default values
START_DASHBOARD=false
VISUALIZER=""
DASHBOARD_PID=""
VISUALIZER_PID=""
DETECTOR_PID=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dashboard)
            START_DASHBOARD=true
            shift
            ;;
        --visualizer)
            VISUALIZER="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Error: Unknown option $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
done

# Validate visualizer
if [ -z "$VISUALIZER" ]; then
    echo "Error: --visualizer is required"
    echo ""
    show_usage
    exit 1
fi

case $VISUALIZER in
    cosmic_skeleton|cosmic_journey|space_visualizer|blur_skeleton)
        ;;
    *)
        echo "Error: Invalid visualizer '$VISUALIZER'"
        echo "Must be one of: cosmic_skeleton, cosmic_journey, space_visualizer, blur_skeleton"
        echo ""
        show_usage
        exit 1
        ;;
esac

echo "=== Starting Dance Movement Services ==="
echo ""
echo "Configuration:"
echo "  Dashboard:   $([ "$START_DASHBOARD" = true ] && echo "✅ Enabled" || echo "❌ Disabled")"
echo "  Visualizer:  $VISUALIZER"
echo "  Detector:    ✅ Always enabled"
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

# Start Dashboard (optional)
if [ "$START_DASHBOARD" = true ]; then
    echo "Starting FastAPI Dashboard..."
    cd dance_dashboard_alt
    if [ -d "venv" ]; then
        venv/bin/python3 src/server.py --osc-port 5005 --web-port 8082 > ../logs/dashboard_alt.log 2>&1 &
    else
        python3 src/server.py --osc-port 5005 --web-port 8082 > ../logs/dashboard_alt.log 2>&1 &
    fi
    DASHBOARD_PID=$!
    echo "  Dashboard started (PID: $DASHBOARD_PID) on http://localhost:8082"
    cd ..
    sleep 2
fi

# Start selected visualizer
echo "Starting $VISUALIZER..."
case $VISUALIZER in
    cosmic_skeleton)
        cd cosmic_skeleton
        if [ -d "venv" ]; then
            venv/bin/python3 src/server.py --osc-port 5007 --port 8091 > ../logs/skeleton.log 2>&1 &
        else
            python3 src/server.py --osc-port 5007 --port 8091 > ../logs/skeleton.log 2>&1 &
        fi
        VISUALIZER_PID=$!
        echo "  Cosmic Skeleton started (PID: $VISUALIZER_PID) on http://localhost:8091"
        VISUALIZER_LOG="skeleton.log"
        ;;
    cosmic_journey)
        cd cosmic_journey
        if [ -d "venv" ]; then
            venv/bin/python3 src/cosmic_server.py --osc-port 5007 --web-port 8091 > ../logs/cosmic.log 2>&1 &
        else
            python3 src/cosmic_server.py --osc-port 5007 --web-port 8091 > ../logs/cosmic.log 2>&1 &
        fi
        VISUALIZER_PID=$!
        echo "  Cosmic Journey started (PID: $VISUALIZER_PID) on http://localhost:8091"
        VISUALIZER_LOG="cosmic.log"
        ;;
    space_visualizer)
        cd space_visualizer
        if [ -d "venv" ]; then
            venv/bin/python3 src/visualizer_server.py > ../logs/space.log 2>&1 &
        else
            python3 src/visualizer_server.py > ../logs/space.log 2>&1 &
        fi
        VISUALIZER_PID=$!
        echo "  Space Visualizer started (PID: $VISUALIZER_PID)"
        VISUALIZER_LOG="space.log"
        ;;
    blur_skeleton)
        cd blur_skeleton_visualizer
        if [ -d "venv" ]; then
            venv/bin/python3 src/server.py --osc-port 5009 --port 8092 --blur 51 > ../logs/blur.log 2>&1 &
        else
            python3 src/server.py --osc-port 5009 --port 8092 --blur 51 > ../logs/blur.log 2>&1 &
        fi
        VISUALIZER_PID=$!
        echo "  Blur Skeleton started (PID: $VISUALIZER_PID) on http://localhost:8092"
        VISUALIZER_LOG="blur.log"
        ;;
esac
cd ..
sleep 2

# Start Detector (always)
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
echo "=== Services Started ==="
echo ""

# Show running services
if [ "$START_DASHBOARD" = true ]; then
    echo "📊 Dashboard:    http://localhost:8082  (OSC: 5005)"
fi

case $VISUALIZER in
    cosmic_skeleton)
        echo "💀 Cosmic Skeleton:    http://localhost:8091  (OSC: 5007)"
        ;;
    cosmic_journey)
        echo "🌌 Cosmic Journey:     http://localhost:8091  (OSC: 5007)"
        ;;
    space_visualizer)
        echo "🌌 Space Visualizer:   http://localhost:8090"
        ;;
    blur_skeleton)
        echo "🎨 Blur Skeleton:      http://localhost:8092  (OSC: 5009)"
        ;;
esac

echo "🤖 Detector:           Sending to all OSC ports"
echo ""

# Show PIDs
echo "Process IDs:"
if [ "$START_DASHBOARD" = true ]; then
    echo "  Dashboard:  $DASHBOARD_PID"
fi
echo "  Visualizer: $VISUALIZER_PID"
echo "  Detector:   $DETECTOR_PID"
echo ""

# Show log commands
echo "To view logs:"
if [ "$START_DASHBOARD" = true ]; then
    echo "  tail -f logs/dashboard_alt.log"
fi
echo "  tail -f logs/$VISUALIZER_LOG"
echo "  tail -f logs/detector.log"
echo ""
echo "To stop all services:"
echo "  ./kill-all-services.sh"
echo ""
