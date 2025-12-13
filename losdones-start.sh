#!/usr/bin/env bash
set -e


# activar venv
source venv/bin/activate

# sanity check (opcional pero recomendable)
which python
python --version

sleep 1

python audio_server.py --port 57120 &
sleep 5

python mixer.py --preflight-only
python mixer.py --host 0.0.0.0 --port 57120 &
#python mixer.py --host 127.0.0.1 --port 57120 &
