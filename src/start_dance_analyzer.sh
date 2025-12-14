#!/bin/bash
# Dance Energy Analyzer Startup Script

echo "🕺 CrowdStream Dance Energy Analyzer 🕺"
echo "======================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is required but not installed."
    exit 1
fi

# Check if audio engine is running (optional)
echo "🔊 Checking audio engine status..."
if pgrep -f "audio_server.py\|stem_mixer_smart.py" > /dev/null; then
    echo "✅ Audio engine detected running"
else
    echo "⚠️  Audio engine not detected. You may want to start it first:"
    echo "   cd audio-engine && python audio_server.py"
    echo "   or: ./start_python_mixer.sh"
    echo ""
fi

# Install requirements if needed
if [ ! -f "dance_analyzer_requirements_installed.flag" ]; then
    echo "📦 Installing requirements..."
    pip3 install -r dance_analyzer_requirements.txt
    touch dance_analyzer_requirements_installed.flag
    echo ""
fi

# Check camera access
echo "📹 Checking camera access..."
python3 -c "
import cv2
cap = cv2.VideoCapture(0)
if cap.isOpened():
    print('✅ Camera access OK')
    cap.release()
else:
    print('❌ Camera access failed')
    exit(1)
" || exit 1

echo ""
echo "🚀 Starting Dance Energy Analyzer..."
echo "Controls:"
echo "  - 'q' to quit"
echo "  - 'space' to pause/resume"
echo "  - Dance to control the music! 💃🕺"
echo ""

# Start the analyzer with default settings
python3 dance_energy_analyzer.py "$@"

echo ""
echo "💫 Alternative versions available:"
echo "  python3 dance_energy_simple.py     # Minimal dependencies"
echo "  python3 dance_energy_working.py    # Fallback version"