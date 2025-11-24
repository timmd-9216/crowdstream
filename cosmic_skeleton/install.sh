#!/bin/bash

# Install dependencies for Cosmic Skeleton Visualizer
# Creates virtual environment and installs all requirements

set -e

echo "💀 Installing Cosmic Skeleton Visualizer dependencies..."
cd "$(dirname "$0")"

# Remove existing venv if present
if [ -d "venv" ]; then
    echo "  Removing existing venv..."
    rm -rf venv
fi

# Create venv
echo "  Creating virtual environment..."
python3 -m venv venv

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
