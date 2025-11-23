#!/bin/bash

# Run Native Cosmic Visualizer (no browser needed)
# Uses GPU directly via OpenGL for Jetson TX1

cd "$(dirname "$0")"

echo "=== Native Cosmic Visualizer ==="
echo "Uses OpenGL + GPU directly (no browser)"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found"
    echo "Run setup first: cd .. && ./setup-jetson-tx1.sh"
    exit 1
fi

# Activate venv and check for PyOpenGL
source venv/bin/activate

if ! python -c "import pygame" 2>/dev/null; then
    echo "Installing native visualization dependencies..."
    pip install -r requirements-native.txt
fi

echo "Starting native visualizer..."
echo ""
echo "Controls:"
echo "  ESC or Q - Quit"
echo "  F - Toggle fullscreen"
echo ""

# Run native visualizer
python src/cosmic_native_visualizer.py "$@"
