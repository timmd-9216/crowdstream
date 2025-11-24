#!/bin/bash
# Start Cosmic Skeleton Visualizer

echo "💀 Starting Cosmic Skeleton Visualizer..."

cd "$(dirname "$0")"

venv/bin/python3 src/server.py --osc-port 5007 --port 8091
