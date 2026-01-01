#!/bin/bash

# Install dependencies for Audio Engine
# Creates virtual environment and installs all requirements

set -e

echo "🎵 Installing Audio Engine dependencies..."
cd "$(dirname "$0")"

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
