#!/bin/bash

# Setup All Virtual Environments
# Creates venvs for all services in the project
#
set -e

echo "=== Setting up All Virtual Environments ==="
echo ""

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project root directory
cd "$ROOT_DIR"
BASE_DIR="$ROOT_DIR"

# Create logs directory if it doesn't exist
mkdir -p logs

# Counter for tracking
TOTAL=0
SUCCESS=0
FAILED=0

# Function to run install script
install_service() {
    local service_dir=$1
    local service_name=$2

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📦 Installing $service_name..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    TOTAL=$((TOTAL + 1))

    if [ -f "$BASE_DIR/$service_dir/install.sh" ]; then
        cd "$BASE_DIR/$service_dir"
        if ./install.sh; then
            SUCCESS=$((SUCCESS + 1))
            echo "✅ $service_name installed successfully"
        else
            FAILED=$((FAILED + 1))
            echo "❌ $service_name installation failed"
        fi
        cd "$BASE_DIR"
    else
        FAILED=$((FAILED + 1))
        echo "⚠️  No install.sh found in $service_dir"
    fi

    echo ""
}

# Install all services
install_service "movement_dashboard" "FastAPI Dashboard"
install_service "visualizers/cosmic_journey" "Cosmic Journey Visualizer"
install_service "visualizers/cosmic_skeleton" "Cosmic Skeleton Visualizer"
install_service "visualizers/cosmic_skeleton_standalone" "Cosmic Skeleton Standalone"
install_service "visualizers/space_visualizer" "Space Visualizer"
install_service "visualizers/blur_skeleton_visualizer" "Blur Skeleton Visualizer"
install_service "visualizers/skeleton_visualizer" "Skeleton Visualizer"
install_service "dance_movement_detector" "Movement Detector"

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "=== Setup Complete ==="
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Summary:"
echo "   Total:   $TOTAL"
echo "   Success: $SUCCESS ✅"
echo "   Failed:  $FAILED ❌"
echo ""

if [ $SUCCESS -eq $TOTAL ]; then
    echo "🎉 All virtual environments created successfully!"
    echo ""
    echo "Virtual environments created for:"
    echo "  • movement_dashboard/venv"
    echo "  • visualizers/cosmic_journey/venv"
    echo "  • visualizers/cosmic_skeleton/venv"
    echo "  • visualizers/cosmic_skeleton_standalone/venv  ⭐ (no detector needed)"
    echo "  • visualizers/space_visualizer/venv"
    echo "  • visualizers/blur_skeleton_visualizer/venv"
    echo "  • visualizers/skeleton_visualizer/venv"
    echo "  • dance_movement_detector/venv"
    echo ""
    echo "To start services:"
    echo "  ./scripts/start-all-services.sh --visualizer cosmic_skeleton_standalone"
    echo ""
    echo "Note: For Raspberry Pi, use setup-venvs-rpi.sh instead"
    exit 0
else
    echo "⚠️  Some installations failed. Check the output above for details."
    exit 1
fi
