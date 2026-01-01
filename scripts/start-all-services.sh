#!/bin/bash

# Start Dance Movement Services
# Starts detector (always) and optionally dashboard and one visualizer

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Start dance movement detector, dashboard (default), and visualizer services."
    echo ""
    echo "Options:"
    echo "  --visualizer VISUALIZER  Start a visualizer (required, one of):"
    echo "                           - cosmic_skeleton"
    echo "                           - cosmic_skeleton_standalone (⭐ no detector needed)"
    echo "                           - skeleton_visualizer"
    echo "                           - cosmic_journey"
    echo "                           - space_visualizer"
    echo "                           - blur_skeleton (standalone)"
    echo "  --no-dashboard           Skip starting the dashboard (dashboard runs by default)"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --visualizer cosmic_skeleton"
    echo "  $0 --visualizer space_visualizer"
    echo "  $0 --visualizer blur_skeleton --no-dashboard"
    echo ""
}

# Default values
START_DASHBOARD=true
VISUALIZER=""
DASHBOARD_PID=""
VISUALIZER_PID=""
DETECTOR_PID=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-dashboard)
            START_DASHBOARD=false
            shift
            ;;
        --dashboard)
            # For backwards compatibility
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
    cosmic_skeleton|cosmic_skeleton_standalone|skeleton_visualizer|cosmic_journey|space_visualizer|blur_skeleton)
        ;;
    *)
        echo "Error: Invalid visualizer '$VISUALIZER'"
        echo "Must be one of: cosmic_skeleton, cosmic_skeleton_standalone, skeleton_visualizer, cosmic_journey, space_visualizer, blur_skeleton"
        echo ""
        show_usage
        exit 1
        ;;
esac

echo "=== Starting Dance Movement Services ==="
echo ""
# Check if visualizer is standalone (has built-in detection)
STANDALONE_VISUALIZERS="cosmic_skeleton_standalone blur_skeleton"
IS_STANDALONE=false
for standalone in $STANDALONE_VISUALIZERS; do
    if [ "$VISUALIZER" = "$standalone" ]; then
        IS_STANDALONE=true
        break
    fi
done

echo "Configuration:"
echo "  Dashboard:   $([ "$START_DASHBOARD" = true ] && echo "✅ Enabled" || echo "❌ Disabled")"
echo "  Visualizer:  $VISUALIZER"
if [ "$IS_STANDALONE" = true ]; then
    echo "  Detector:    ⚡ Built-in (standalone mode)"
else
    echo "  Detector:    ✅ External detector enabled"
fi
echo ""

# Change to script directory and save root directory (parent of scripts/)
cd "$(dirname "$0")"
ROOT_DIR=$(cd .. && pwd)
LOG_DIR="$ROOT_DIR/logs"

# Kill any existing services first
echo "Stopping any existing services..."
cd "$ROOT_DIR"
./kill-all-services.sh
sleep 2

echo ""
echo "=== Starting Services ==="
echo ""

# Start Dashboard (optional)
if [ "$START_DASHBOARD" = true ]; then
    echo "Starting FastAPI Dashboard..."
    cd "$ROOT_DIR/dance_dashboard_alt"
    if [ -d "venv" ]; then
        venv/bin/python3 src/server.py --osc-port 5005 --web-port 8082 > "$LOG_DIR/dashboard_alt.log" 2>&1 &
    else
        python3 src/server.py --osc-port 5005 --web-port 8082 > "$LOG_DIR/dashboard_alt.log" 2>&1 &
    fi
    DASHBOARD_PID=$!
    echo "  Dashboard started (PID: $DASHBOARD_PID) on http://localhost:8082"
    sleep 2
fi

# Start selected visualizer
echo "Starting $VISUALIZER..."
case $VISUALIZER in
    cosmic_skeleton)
        cd "$ROOT_DIR/visualizers/cosmic_skeleton"
        if [ -d "venv" ]; then
            venv/bin/python3 src/server.py --osc-port 5007 --port 8091 > "$LOG_DIR/cosmic_skeleton.log" 2>&1 &
        else
            python3 src/server.py --osc-port 5007 --port 8091 > "$LOG_DIR/cosmic_skeleton.log" 2>&1 &
        fi
        VISUALIZER_PID=$!
        echo "  Cosmic Skeleton started (PID: $VISUALIZER_PID) on http://localhost:8091"
        VISUALIZER_LOG="cosmic_skeleton.log"
        ;;
    cosmic_skeleton_standalone)
        cd "$ROOT_DIR/visualizers/cosmic_skeleton_standalone"
        if [ -d "venv" ]; then
            DISPLAY=:0 venv/bin/python3 src/server.py --port 8094 --source 0 --imgsz 416 > "$LOG_DIR/cosmic_standalone.log" 2>&1 &
        else
            DISPLAY=:0 python3 src/server.py --port 8094 --source 0 --imgsz 416 > "$LOG_DIR/cosmic_standalone.log" 2>&1 &
        fi
        VISUALIZER_PID=$!
        echo "  Cosmic Skeleton Standalone started (PID: $VISUALIZER_PID) on http://localhost:8094"
        VISUALIZER_LOG="cosmic_standalone.log"
        ;;
    skeleton_visualizer)
        cd "$ROOT_DIR/visualizers/skeleton_visualizer"
        if [ -d "venv" ]; then
            venv/bin/python3 src/server.py --osc-port 5007 --port 8093 > "$LOG_DIR/skeleton_visualizer.log" 2>&1 &
        else
            python3 src/server.py --osc-port 5007 --port 8093 > "$LOG_DIR/skeleton_visualizer.log" 2>&1 &
        fi
        VISUALIZER_PID=$!
        echo "  Skeleton Visualizer started (PID: $VISUALIZER_PID) on http://localhost:8093"
        VISUALIZER_LOG="skeleton_visualizer.log"
        ;;
    cosmic_journey)
        cd "$ROOT_DIR/visualizers/cosmic_journey"
        if [ -d "venv" ]; then
            venv/bin/python3 src/cosmic_server.py --osc-port 5007 --web-port 8091 > "$LOG_DIR/cosmic.log" 2>&1 &
        else
            python3 src/cosmic_server.py --osc-port 5007 --web-port 8091 > "$LOG_DIR/cosmic.log" 2>&1 &
        fi
        VISUALIZER_PID=$!
        echo "  Cosmic Journey started (PID: $VISUALIZER_PID) on http://localhost:8091"
        VISUALIZER_LOG="cosmic.log"
        ;;
    space_visualizer)
        cd "$ROOT_DIR/visualizers/space_visualizer"
        if [ -d "venv" ]; then
            venv/bin/python3 src/visualizer_server.py > "$LOG_DIR/space.log" 2>&1 &
        else
            python3 src/visualizer_server.py > "$LOG_DIR/space.log" 2>&1 &
        fi
        VISUALIZER_PID=$!
        echo "  Space Visualizer started (PID: $VISUALIZER_PID)"
        VISUALIZER_LOG="space.log"
        ;;
    blur_skeleton)
        cd "$ROOT_DIR/visualizers/blur_skeleton_visualizer"
        if [ -d "venv" ]; then
            venv/bin/python3 src/server.py --osc-port 5009 --port 8092 --blur 51 > "$LOG_DIR/blur.log" 2>&1 &
        else
            python3 src/server.py --osc-port 5009 --port 8092 --blur 51 > "$LOG_DIR/blur.log" 2>&1 &
        fi
        VISUALIZER_PID=$!
        echo "  Blur Skeleton started (PID: $VISUALIZER_PID) on http://localhost:8092"
        VISUALIZER_LOG="blur.log"
        ;;
esac
sleep 2

# Start Detector (only if not standalone)
if [ "$IS_STANDALONE" = false ]; then
    echo "Starting Movement Detector..."
    cd "$ROOT_DIR/dance_movement_detector"
    DETECTOR_CFG="${DETECTOR_CFG:-config/raspberry_pi_optimized.json}"
    if [ -d "venv" ]; then
        DISPLAY=:0 venv/bin/python3 src/dance_movement_detector.py --config "$DETECTOR_CFG" > "$LOG_DIR/detector.log" 2>&1 &
    else
        DISPLAY=:0 python3 src/dance_movement_detector.py --config "$DETECTOR_CFG" > "$LOG_DIR/detector.log" 2>&1 &
    fi
    DETECTOR_PID=$!
    echo "  Detector started (PID: $DETECTOR_PID)"
    sleep 2
else
    echo "⏭️  Skipping external detector (visualizer has built-in YOLO)"
    DETECTOR_PID=""
fi

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
    cosmic_skeleton_standalone)
        echo "⭐ Cosmic Skeleton Standalone: http://localhost:8094  (Built-in YOLO)"
        ;;
    skeleton_visualizer)
        echo "🦴 Skeleton Visualizer: http://localhost:8093  (OSC: 5007)"
        ;;
    cosmic_journey)
        echo "🌌 Cosmic Journey:     http://localhost:8091  (OSC: 5007)"
        ;;
    space_visualizer)
        echo "🌌 Space Visualizer:   http://localhost:8090"
        ;;
    blur_skeleton)
        echo "🎨 Blur Skeleton:      http://localhost:8092  (Built-in YOLO)"
        ;;
esac

if [ "$IS_STANDALONE" = false ]; then
    echo "🤖 Detector:           Sending to all OSC ports"
fi
echo ""

# Show PIDs
echo "Process IDs:"
if [ "$START_DASHBOARD" = true ]; then
    echo "  Dashboard:  $DASHBOARD_PID"
fi
echo "  Visualizer: $VISUALIZER_PID"
if [ "$IS_STANDALONE" = false ] && [ ! -z "$DETECTOR_PID" ]; then
    echo "  Detector:   $DETECTOR_PID"
fi
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
