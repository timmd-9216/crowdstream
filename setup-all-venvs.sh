#!/bin/bash

# Setup All Virtual Environments
# Creates venvs for all services in the project

set -e

echo "=== Setting up All Virtual Environments ==="
echo ""

# Change to script directory
cd "$(dirname "$0")"
BASE_DIR=$(pwd)

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
install_service "dance_dashboard_alt" "FastAPI Dashboard"
install_service "cosmic_journey" "Cosmic Journey Visualizer"
install_service "cosmic_skeleton" "Cosmic Skeleton Visualizer"
install_service "space_visualizer" "Space Visualizer"
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
    echo "  • dance_dashboard_alt/venv"
    echo "  • cosmic_journey/venv"
    echo "  • cosmic_skeleton/venv"
    echo "  • space_visualizer/venv"
    echo "  • dance_movement_detector/venv"
    echo ""
    echo "To start all services:"
    echo "  ./start-all-services.sh"
    echo ""
    echo "Note: For Raspberry Pi, use setup-venvs-rpi.sh instead"
    exit 0
else
    echo "⚠️  Some installations failed. Check the output above for details."
    exit 1
fi
