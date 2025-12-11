#!/bin/bash
# Installation script for Video Skeleton Visualizer

set -e

echo "🌌 Video Skeleton Visualizer Installation"
echo "=========================================="

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: requirements.txt not found"
    echo "Please run this script from the video_skeleton_visualizer directory"
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📥 Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Installation complete!"
echo ""
echo "To start the server:"
echo "  source venv/bin/activate"
echo "  python src/server.py --video /path/to/video.mp4"
echo ""
echo "Or use the start script:"
echo "  ./start_video_skeleton.sh /path/to/video.mp4"
