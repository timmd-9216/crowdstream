#!/bin/bash

# Install dependencies for Audio Engine
# Creates virtual environment and installs all requirements

set -e

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
AUDIO_MIXER_DIR="$ROOT_DIR/audio-mixer"

echo "🎵 Installing Audio Engine dependencies..."
cd "$AUDIO_MIXER_DIR"

# Remove existing venv if present
if [ -d "venv" ]; then
    echo "  Removing existing venv..."
    rm -rf venv
fi

# Create venv (prefer python3.13 if available)
echo "  Creating virtual environment (prefer python3.13 if available)..."
PY_CMD=""
if command -v python3.13 >/dev/null 2>&1; then
    PY_CMD=python3.13
elif command -v python3 >/dev/null 2>&1; then
    PY_CMD=python3
elif command -v python >/dev/null 2>&1; then
    PY_CMD=python
else
    echo "  ❌ No Python interpreter found (python3.13/python3/python). Install Python 3.13 or ensure 'python3' is on PATH." >&2
    exit 1
fi

echo "  Using: $PY_CMD"
$PY_CMD -m venv venv

# Upgrade pip
echo "  Upgrading pip..."
venv/bin/pip install --upgrade pip

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "  Installing requirements..."
    venv/bin/pip install -r requirements.txt
    echo "  ✅ Installation complete"
else
    echo "  ⚠️  No requirements.txt found"
    exit 1
fi

echo ""
echo "Virtual environment ready at: venv/"
echo "To activate: source venv/bin/activate"
echo ""

# Print system-specific recommendations
print_recommendations() {
    echo "════════════════════════════════════════════════════════════"
    echo "📋 RECOMENDACIONES DE INSTALACIÓN"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    
    OS="$(uname -s)"
    case "${OS}" in
        Linux*)
            echo "🐧 Sistema: Linux"
            echo ""
            echo "Para habilitar todas las funciones de time-stretching, instala:"
            echo ""
            echo "  # Para pyrubberband (alta calidad):"
            echo "  sudo apt-get update"
            echo "  sudo apt-get install -y librubberband-dev"
            echo ""
            echo ""
            echo "  # Para PyAudio (si no está instalado):"
            echo "  sudo apt-get install -y python3-pyaudio portaudio19-dev"
            echo ""
            echo "  # Luego reinstala las dependencias Python:"
            echo "  source venv/bin/activate"
            echo "  pip install --upgrade pyrubberband"
            ;;
        Darwin*)
            echo "🍎 Sistema: macOS"
            echo ""
            echo "Para habilitar todas las funciones de time-stretching, instala:"
            echo ""
            
            # Check if Homebrew is installed
            if command -v brew >/dev/null 2>&1; then
                echo "  # Para pyrubberband (alta calidad):"
                echo "  brew install rubberband"
                echo ""
                echo ""
                echo "  # Para PyAudio (si hay problemas):"
                echo "  brew install portaudio"
                echo ""
                echo "  # Luego reinstala las dependencias Python:"
                echo "  source venv/bin/activate"
                echo "  pip install --upgrade pyrubberband"
            else
                echo "  ⚠️  Homebrew no está instalado"
                echo "  Instala Homebrew primero: https://brew.sh"
                echo ""
                echo "  Luego ejecuta:"
                echo "  brew install rubberband sound-touch"
            fi
            ;;
        *)
            echo "💻 Sistema: ${OS}"
            echo ""
            echo "Consulta la documentación para instalar:"
            echo "  - Rubber Band library (para pyrubberband)"
            ;;
    esac
    
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "🔍 VERIFICAR BIBLIOTECAS DISPONIBLES"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "Para verificar qué métodos de time-stretching están disponibles:"
    echo ""
    echo "  source venv/bin/activate"
    echo "  python check_time_stretch_libs.py"
    echo ""
    echo "O desde el directorio raíz:"
    echo "  python audio-mixer/check_time_stretch_libs.py"
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo ""
}

print_recommendations
