#!/bin/bash
# Python Audio Mixer Launcher - Shell Script Version
# Starts both audio_server.py and stem_mixer_smart.py

echo "🚀 PYTHON AUDIO MIXER LAUNCHER 🚀"
echo "========================================"

# Optional audio device selection (pass as first argument)
AUDIO_DEVICE=""
if [ ! -z "$1" ]; then
    AUDIO_DEVICE="--device $1"
    echo "🎯 Using audio device: $1"
fi

# Check if files exist
if [ ! -f "audio_server.py" ]; then
    echo "❌ audio_server.py not found"
    exit 1
fi

if [ ! -f "stem_mixer_smart.py" ]; then
    echo "❌ stem_mixer_smart.py not found"
    exit 1
fi

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    if [ ! -z "$AUDIO_SERVER_PID" ]; then
        echo "⏹️  Stopping audio server (PID: $AUDIO_SERVER_PID)..."
        kill $AUDIO_SERVER_PID 2>/dev/null
    fi
    echo "👋 Cleanup complete"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start audio server in background
echo "🎛️💾 Starting Python Audio Server..."
if [ -d "venv" ]; then
    venv/bin/python3 audio_server.py $AUDIO_DEVICE &
else
    python3 audio_server.py $AUDIO_DEVICE &
fi
AUDIO_SERVER_PID=$!

# Wait for audio server to initialize
echo "⏳ Waiting for audio server to initialize..."
sleep 3

# Check if audio server is still running
if ! kill -0 $AUDIO_SERVER_PID 2>/dev/null; then
    echo "❌ Audio server failed to start"
    exit 1
fi

echo "✅ Audio server is running (PID: $AUDIO_SERVER_PID)"

# Start stem mixer in foreground
echo "🧠 Starting Smart Stem Mixer..."
echo ""
echo "🎵 PYTHON AUDIO MIXER SYSTEM READY 🎵"
echo "================================================="
echo "🎛️ Audio Server: Running in background (PID: $AUDIO_SERVER_PID)"
echo "🧠 Stem Mixer: Interactive mode"
echo "💡 Use Ctrl+C to stop both processes"
echo "================================================="
echo ""

if [ -d "venv" ]; then
    venv/bin/python3 stem_mixer_smart.py
else
    python3 stem_mixer_smart.py
fi

# If we get here, mixer exited normally
cleanup