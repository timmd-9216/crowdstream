#!/bin/bash

# Iniciar todos los servicios
#./start-all-services.sh --visualizer cosmic_skeleton --no-dashboard
./start-all-services.sh --visualizer cosmic_skeleton
#./start-all-services.sh  --visualizer cosmic_skeleton_standalone --no-dashboard 

# Detectar el sistema operativo
OS="$(uname -s)"
ARCH="$(uname -m)"

# Ejecutar comando según el SO
if [[ "$OS" == "Darwin" ]]; then
    # macOS
    echo "Detectado macOS, abriendo Chrome..."
    open -a "Google Chrome" http://localhost:8091
elif [[ "$OS" == "Linux" ]]; then
    # Linux (Raspberry Pi u otro)
    if [[ "$ARCH" == "arm"* ]] || [[ "$ARCH" == "aarch64" ]]; then
        # Raspberry Pi (ARM)
        echo "Detectado Raspberry Pi, iniciando Chrome..."
        ./start-chrome.sh 8094 &
    else
        # Otro Linux
        echo "Detectado Linux, iniciando Chrome..."
        ./start-chrome.sh 8091 &
    fi
else
    echo "Sistema operativo no reconocido: $OS"
    echo "Intentando abrir Chrome en el puerto 8091..."
    ./start-chrome.sh 8091 &
fi

#old
#./start-all-services.sh  --visualizer cosmic_skeleton --no-dashboard 
#./start-chrome.sh 8091 &

