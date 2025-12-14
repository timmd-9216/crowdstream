#!/bin/bash

# Start Cosmic Skeleton Standalone Visualizer

cd "$(dirname "$0")"

echo "🌌 Starting Cosmic Skeleton Standalone..."
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run ./install.sh first."
    exit 1
fi

# Default values
PORT=8094
SOURCE=0
#IMGSZ=416
IMGSZ=320

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --source)
            SOURCE="$2"
            shift 2
            ;;
        --imgsz)
            IMGSZ="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --port PORT      Web port (default: 8094)"
            echo "  --source SOURCE  Video source (default: 0 = webcam)"
            echo "  --imgsz SIZE     YOLO input size (default: 416, try 320 for speed)"
            echo "  -h, --help       Show this help"
            echo ""
            echo "Examples:"
            echo "  $0                      # Use defaults"
            echo "  $0 --port 8095          # Custom port"
            echo "  $0 --imgsz 320          # Faster, lower quality"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run with -h for help"
            exit 1
            ;;
    esac
done

echo "Configuration:"
echo "  Port:   $PORT"
echo "  Source: $SOURCE"
echo "  Size:   $IMGSZ"
echo ""

# Run the server
DISPLAY=:0 venv/bin/python3 src/server.py --port "$PORT" --source "$SOURCE" --imgsz "$IMGSZ"
