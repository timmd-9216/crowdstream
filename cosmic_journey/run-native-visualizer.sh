#!/bin/bash

# Run GPU-Accelerated Cosmic Visualizer (no browser needed)
# Uses pyglet + OpenGL (Maxwell GPU rendering)

cd "$(dirname "$0")"

echo "=== GPU Cosmic Visualizer ==="
echo "Uses pyglet + OpenGL (Maxwell GPU rendering)"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found"
    echo "Run setup first: cd .. && ./setup-jetson-tx1.sh"
    exit 1
fi

# Activate venv
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import pythonosc" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements-gpu.txt
fi

if ! python -c "import pyglet" 2>/dev/null; then
    echo "Installing pyglet..."
    pip install -r requirements-gpu.txt
fi

echo "Starting GPU visualizer..."
echo ""
echo "Controls:"
echo "  ESC or Q - Quit"
echo "  F - Toggle fullscreen"
echo ""

# Run GPU visualizer (uses pyglet + OpenGL)
python src/cosmic_gpu_visualizer.py "$@"
