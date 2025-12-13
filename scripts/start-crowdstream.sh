
source src/audio-engine/venv/bin/activate


python audio_server.py --port 57120 &
sleep 5
python mixer.py --preflight-only 
#python mixer.py --host 127.0.0.1 --port 57120 &
python mixer.py --host 0.0.0.0 --port 57120 &
