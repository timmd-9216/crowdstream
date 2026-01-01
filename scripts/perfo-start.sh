#!/bin/bash

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT_DIR"

"$SCRIPT_DIR/kill-all-services.sh"

# Iniciar todos los servicios
#"$SCRIPT_DIR/start-all-services.sh" --visualizer cosmic_skeleton --no-dashboard
"$SCRIPT_DIR/start-all-services.sh" --visualizer cosmic_skeleton
#"$SCRIPT_DIR/start-all-services.sh"  --visualizer cosmic_skeleton_standalone --no-dashboard 

# Detectar el sistema operativo
OS="$(uname -s)"
ARCH="$(uname -m)"

# Ejecutar comando según el SO
if [[ "$OS" == "Darwin" ]]; then
    # macOS
    echo "Detectado macOS, abriendo Chrome..."
    open -a "Google Chrome" http://localhost:8091
    open -a "Google Chrome" http://localhost:8082
elif [[ "$OS" == "Linux" ]]; then
    # Linux (Raspberry Pi u otro)
    if [[ "$ARCH" == "arm"* ]] || [[ "$ARCH" == "aarch64" ]]; then
        # Raspberry Pi (ARM)
        echo "Detectado Raspberry Pi, iniciando Chrome..."
        "$SCRIPT_DIR/start-chrome.sh" 8094 &
    else
        # Otro Linux
        echo "Detectado Linux, iniciando Chrome..."
        "$SCRIPT_DIR/start-chrome.sh" 8091 &
    fi
else
    echo "Sistema operativo no reconocido: $OS"
    echo "Intentando abrir Chrome en el puerto 8091..."
    "$SCRIPT_DIR/start-chrome.sh" 8091 &
fi

#old
#./start-all-services.sh  --visualizer cosmic_skeleton --no-dashboard 
#./start-chrome.sh 8091 &

