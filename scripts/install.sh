#!/usr/bin/env bash
set -euo pipefail

# Bootstrap a local virtualenv for struct_loader.py and friends.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-"$ROOT/.venv"}"
PYTHON_BIN="${PYTHON:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Python not found; install Python 3.10+ first." >&2
    exit 1
  fi
fi

"$PYTHON_BIN" - <<'PY'
import sys
major, minor = sys.version_info[:2]
if (major, minor) < (3, 10):
    sys.exit(f"Python 3.10+ required; found {sys.version.split()[0]}")
PY

if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip

REQ_FILE="$ROOT/requirements.txt"
if [ -f "$REQ_FILE" ]; then
  python -m pip install -r "$REQ_FILE"
fi

python - <<'PY'
import shutil
import sys

if not shutil.which("ffmpeg"):
    sys.exit("ffmpeg not found on PATH; install it so struct_loader.py can export audio.")
PY

cat <<EOF
Virtualenv ready at $VENV_DIR
Activate with: source "$VENV_DIR/bin/activate"
EOF
