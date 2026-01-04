#!/bin/bash
# Setup script for Raspberry Pi
# Installs PyAudio from system packages (version 0.2.13) which works better on RPi

echo "🍓 Setting up audio engine for Raspberry Pi..."

# Install system dependencies
echo "📦 Installing system packages..."
sudo apt-get update
sudo apt-get install -y python3-pyaudio python3-numpy python3-scipy portaudio19-dev

# Create/recreate venv
echo "🔧 Setting up virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  Removing existing venv..."
    rm -rf venv
fi

python3 -m venv venv --system-site-packages  # Allow access to system PyAudio

# Activate venv
source venv/bin/activate

# Install other dependencies (but not PyAudio - use system version)
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install python-osc soundfile

# Verify PyAudio
echo ""
echo "✅ Verifying PyAudio installation..."
python -c "import pyaudio; print(f'PyAudio version: {pyaudio.__version__}'); print(f'PortAudio version: {pyaudio.get_portaudio_version()}')"

echo ""
echo "✅ Setup complete!"
echo "Run: ./start_python_mixer.sh"
