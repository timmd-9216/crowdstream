#!/usr/bin/env bash
set -euo pipefail

# Kill audio_server and mixer processes (by script name or OSC port 57120).

PORT="${PORT:-57120}"

echo "🔍 Checking for processes on UDP/TCP port ${PORT} and python scripts {audio_server,mixer}.py"

# Kill by script name
pids=($(pgrep -f "audio_server.py|mixer.py" || true))
if [ ${#pids[@]} -gt 0 ]; then
  echo "⏹️  Killing by name: ${pids[*]}"
  kill "${pids[@]}" 2>/dev/null || true
fi

# Kill by port (UDP/TCP)
port_pids=($(lsof -t -i udp:${PORT} -i tcp:${PORT} 2>/dev/null | sort -u || true))
if [ ${#port_pids[@]} -gt 0 ]; then
  echo "⏹️  Killing by port ${PORT}: ${port_pids[*]}"
  kill "${port_pids[@]}" 2>/dev/null || true
fi

echo "✅ Done."
