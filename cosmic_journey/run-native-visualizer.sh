#!/bin/bash

# Run Simple Cosmic Visualizer (no browser needed)
# Uses tkinter (pre-installed, no compilation)

cd "$(dirname "$0")"

echo "=== Simple Cosmic Visualizer ==="
echo "Uses tkinter (no browser, no compilation needed)"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found"
    echo "Run setup first: cd .. && ./setup-jetson-tx1.sh"
    exit 1
fi

# Activate venv
source venv/bin/activate

# Check if python-osc is installed
if ! python -c "import pythonosc" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements-native.txt
fi

echo "Starting simple visualizer..."
echo ""
echo "Controls:"
echo "  ESC or Q - Quit"
echo ""

# Run simple visualizer (uses tkinter, pre-installed)
python src/cosmic_simple_visualizer.py "$@"
