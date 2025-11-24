#!/bin/bash
# Start Blur Skeleton Visualizer

echo "🎨 Starting Blur Skeleton Visualizer..."

cd "$(dirname "$0")"

venv/bin/python3 src/server.py --osc-port 5009 --port 8092 --blur 25
