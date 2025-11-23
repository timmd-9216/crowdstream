#!/bin/bash

# Launch Chromium with GPU acceleration on Jetson TX1
# Optimized for hardware-accelerated WebGL visualization

echo "Launching Chromium with GPU acceleration for Jetson TX1..."

# URL to open (default: cosmic visualizer)
URL="${1:-http://localhost:8091}"

# Chromium flags for Jetson TX1 GPU acceleration
chromium-browser \
  --kiosk \
  --no-first-run \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-pinch \
  --overscroll-history-navigation=0 \
  --enable-gpu-rasterization \
  --enable-zero-copy \
  --use-gl=egl \
  --enable-features=VaapiVideoDecoder \
  --ignore-gpu-blacklist \
  --disable-gpu-driver-bug-workarounds \
  --disable-software-rasterizer \
  --enable-webgl \
  --enable-accelerated-2d-canvas \
  --enable-accelerated-video-decode \
  --num-raster-threads=4 \
  --enable-oop-rasterization \
  "$URL"
