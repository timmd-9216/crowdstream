#!/usr/bin/env bash
set -e


# activar venv
source venv/bin/activate

# sanity check (opcional pero recomendable)
which python
python --version

sleep 1
sleep 3

python audio_server.py --port 57120 &
sleep 8  # Wait for audio server to fully initialize (ALSA probing takes time)
sleep 2
#python mixer.py --preflight-only
#python mixer.py --host 0.0.0.0 --port 57120 --optimized-filters &
#python mixer.py --host 0.0.0.0 --port 57120 --optimized-filters &
python mixer_3tracks.py --host 0.0.0.0 --port 57120 &
#python mixer.py --host 127.0.0.1 --port 57120 &

# Con filtros estándar (slower pero funciona sin scipy)
#python audio_server.py --enable-filters
