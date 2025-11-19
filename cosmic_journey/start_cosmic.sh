#!/bin/bash
# Start Cosmic Journey Visualizer

echo "🌌 Starting Cosmic Journey Visualizer..."

cd "$(dirname "$0")"

venv/bin/python3 src/cosmic_server.py --osc-port 5007 --web-port 8091
