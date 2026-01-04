#!/bin/bash
#
# Wrapper to install audio-mixer dependencies using the shared script.
# Usage:
#   ./install.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

"$ROOT_DIR/scripts/audio-mixer-install.sh"

