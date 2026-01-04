#!/usr/bin/env bash
# Optimized startup script for Dance Movement Detector on Raspberry Pi

set -e

echo "🎭 Starting Dance Movement Detector (Raspberry Pi Optimized)"
echo ""

# Check if we're on Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "⚠️  Warning: This script is optimized for Raspberry Pi"
    echo "   It will still work on other systems but may not be optimal"
    echo ""
fi

# Check temperature
if command -v vcgencmd &> /dev/null; then
    TEMP=$(vcgencmd measure_temp | grep -oP '\d+\.\d+')
    echo "🌡️  Current temperature: ${TEMP}°C"
    if (( $(echo "$TEMP > 75" | bc -l) )); then
        echo "⚠️  WARNING: Temperature is high! Consider adding cooling."
    fi
    echo ""
fi

# Check for camera
if command -v vcgencmd &> /dev/null; then
    CAMERA=$(vcgencmd get_camera | grep -oP 'detected=\K\d+')
    if [ "$CAMERA" != "1" ]; then
        echo "❌ Camera not detected!"
        echo "   Run: sudo raspi-config -> Interface Options -> Camera -> Enable"
        exit 1
    fi
    echo "📷 Camera detected"
    echo ""
fi

# Navigate to script directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "🐍 Activating virtual environment..."
    source venv/bin/activate
elif [ -d "../venv" ]; then
    echo "🐍 Activating virtual environment..."
    source ../venv/bin/activate
else
    echo "⚠️  No virtual environment found"
fi

# Set CPU governor to performance mode (requires sudo)
if [ -f "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor" ]; then
    CURRENT_GOVERNOR=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)
    echo "⚡ Current CPU governor: $CURRENT_GOVERNOR"

    if [ "$CURRENT_GOVERNOR" != "performance" ]; then
        echo "   Tip: For best performance, run:"
        echo "   sudo sh -c 'echo performance > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor'"
    fi
    echo ""
fi

# Check available memory
FREE_MEM=$(free -m | awk '/^Mem:/{print $7}')
echo "💾 Available memory: ${FREE_MEM}MB"
if [ "$FREE_MEM" -lt 500 ]; then
    echo "⚠️  Low memory! Close unnecessary applications."
fi
echo ""

# Configuration
CONFIG_FILE="${1:-config/config_rpi_optimized.json}"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Config file not found: $CONFIG_FILE"
    echo "   Using default config"
    CONFIG_FILE="config/config.json"
fi

echo "📋 Using config: $CONFIG_FILE"
echo ""

# Display configuration summary
if command -v jq &> /dev/null && [ -f "$CONFIG_FILE" ]; then
    MODEL=$(jq -r '.model // "yolov8n-pose.pt"' "$CONFIG_FILE")
    IMGSZ=$(jq -r '.imgsz // 640' "$CONFIG_FILE")
    SKIP=$(jq -r '.skip_frames // 0' "$CONFIG_FILE")
    SHOW=$(jq -r '.show_video // true' "$CONFIG_FILE")

    echo "⚙️  Configuration:"
    echo "   Model: $MODEL"
    echo "   Image size: $IMGSZ"
    echo "   Skip frames: $SKIP"
    echo "   Show video: $SHOW"
    echo ""
fi

echo "🚀 Starting detector..."
echo "   Press Ctrl+C to stop"
echo ""

# Run with nice priority to leave resources for other processes
nice -n 5 python src/dance_movement_detector.py \
    --config "$CONFIG_FILE" \
    --no-display

# Cleanup
echo ""
echo "✅ Detector stopped"
