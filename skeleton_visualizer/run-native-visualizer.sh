#!/bin/bash

# Run GPU-Accelerated Skeleton Visualizer (no browser needed)
# Uses pyglet + OpenGL (Maxwell GPU rendering)

cd "$(dirname "$0")"

echo "=== GPU Skeleton Visualizer ==="
echo "Uses pyglet + OpenGL (Maxwell GPU rendering)"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found"
    echo "Create venv first:"
    echo "  python3 -m venv --without-pip venv --system-site-packages"
    echo "  source venv/bin/activate"
    echo "  wget https://bootstrap.pypa.io/pip/3.5/get-pip.py"
    echo "  python get-pip.py"
    echo "  pip install -r requirements-gpu.txt"
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

echo "Starting GPU skeleton visualizer..."
echo ""
echo "Controls:"
echo "  ESC or Q - Quit"
echo "  F - Toggle fullscreen"
echo ""

# Run GPU visualizer (uses pyglet + OpenGL)
python src/skeleton_gpu_visualizer.py "$@"
