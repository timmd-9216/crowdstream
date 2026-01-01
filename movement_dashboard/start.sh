#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "=== Dance Dashboard (FastAPI) ==="

if [ ! -d "venv" ]; then
  echo "Creating virtualenv"
  python3 -m venv venv
fi

source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

python3 src/server.py "$@"
