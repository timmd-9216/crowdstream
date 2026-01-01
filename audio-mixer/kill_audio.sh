#!/usr/bin/env bash
set -euo pipefail

# Kill audio_server and mixer processes (by script name or OSC port).

PORTS=(${PORTS:-57120 57122})
PATTERN="audio_server.py|mixer.py|mixer_tracks.py|mixer_3tracks.py"

echo "🔍 Checking for python scripts (${PATTERN}) and ports: ${PORTS[*]}"

# Kill by script name (only python processes)
pids=($(pgrep -f "python.*(${PATTERN})" || true))
if [ ${#pids[@]} -gt 0 ]; then
  echo "⏹️  Killing by name: ${pids[*]}"
  kill "${pids[@]}" 2>/dev/null || true
fi

# Kill by port (UDP/TCP), but only for matching python scripts
for port in "${PORTS[@]}"; do
  port_pids=($(lsof -t -i udp:${port} -i tcp:${port} 2>/dev/null | sort -u || true))
  if [ ${#port_pids[@]} -gt 0 ]; then
    for pid in "${port_pids[@]}"; do
      cmd="$(ps -p "${pid}" -o command= 2>/dev/null || true)"
      if echo "${cmd}" | rg -q "python.*(${PATTERN})"; then
        echo "⏹️  Killing by port ${port}: ${pid}"
        kill "${pid}" 2>/dev/null || true
      fi
    done
  fi
done

echo "✅ Done."
