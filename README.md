# crowdstream_local

Python audio server capable of loading stems into memory and playing them in sync
via OSC control. The server exposes a SuperCollider-compatible OSC API and
supports crossfading between two virtual decks, tempo control, and real-time
mixing using PyAudio.

## Requirements

- Python 3.10+
- NumPy
- SoundFile
- PyAudio
- python-osc

Install dependencies with:

```bash
pip install numpy soundfile pyaudio python-osc
```

## Usage

```bash
python audio_server.py --port 57120 --device <audio_device_id> --bpm 120
```

Once running, control the server using OSC messages such as `/load_buffer`,
`/play_stem`, `/stop_stem`, `/stem_volume`, `/crossfade_levels`, `/set_tempo`,
and `/mixer_cleanup`.
