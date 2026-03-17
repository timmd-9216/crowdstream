#!/bin/bash

# Optimize CrowdStream for Raspberry Pi 4
# Exports YOLO to TFLite INT8 and configures for best performance

set -e

echo "🚀 CrowdStream Raspberry Pi 4 Optimizer"
echo "========================================"
echo ""

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT_DIR"

# Check if already optimized
if [ -d "yolov8n-pose_saved_model" ]; then
    echo "⚠️  TFLite model already exists: yolov8n-pose_saved_model/"
    echo ""
    read -p "Re-export? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping export. Using existing model."
    else
        echo "🗑️  Removing old model..."
        rm -rf yolov8n-pose_saved_model
    fi
fi

if [ ! -d "yolov8n-pose_saved_model" ]; then
    echo "📦 Step 1/3: Exporting YOLOv8n-pose to TFLite INT8..."
    echo "   (This takes 5-10 minutes, be patient)"
    echo ""

    python3 export_yolo_tflite.py

    if [ ! -d "yolov8n-pose_saved_model" ]; then
        echo "❌ Export failed. Check that ultralytics is installed."
        exit 1
    fi

    echo ""
    echo "✅ Model exported successfully!"
fi

echo ""
echo "📝 Step 2/3: Configuring detector for TFLite..."

# Update start-all-services.sh: RPi branch uses TFLite config
if grep -q "raspberry_pi_optimized.json" "$SCRIPT_DIR/start-all-services.sh"; then
    sed -i.bak 's/raspberry_pi_optimized\.json/raspberry_pi_tflite.json/g' "$SCRIPT_DIR/start-all-services.sh"
    echo "   ✅ Updated scripts/start-all-services.sh (RPi detector config → TFLite)"
else
    echo "   ⚠️  Could not auto-update scripts/start-all-services.sh"
    echo "      Manual step: set DETECTOR_CFG to config/raspberry_pi_tflite.json for the RPi branch"
fi

echo ""
echo "🧪 Step 3/3: Testing configuration..."
echo ""

if [ -f "dance_movement_detector/config/raspberry_pi_tflite.json" ]; then
    echo "   ✅ TFLite config exists"
else
    echo "   ❌ TFLite config missing"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Optimization Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Expected performance improvement:"
echo "  Before (PyTorch):    3-5 FPS"
echo "  After (TFLite INT8): 12-18 FPS"
echo "  With frame skip:     20-25 FPS"
echo ""
echo "Model location:"
echo "  yolov8n-pose_saved_model/yolov8n-pose_int8.tflite"
echo ""
echo "To run optimized:"
echo "  ./scripts/start-all-services.sh --visualizer cosmic_skeleton"
echo ""
echo "To test standalone:"
echo "  cd dance_movement_detector"
echo "  venv/bin/python3 src/dance_movement_detector.py --config config/raspberry_pi_tflite.json"
echo ""
echo "📖 See OPTIMIZATION_GUIDE.md for more details"
echo ""
