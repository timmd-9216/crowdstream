#!/bin/bash
# Start the Video Skeleton Visualizer

if [ -z "$1" ]; then
    echo "Usage: $0 <video_file>"
    echo "Example: $0 /path/to/video.mp4"
    exit 1
fi

source venv/bin/activate
python src/server.py --video "$1" --port 8094
