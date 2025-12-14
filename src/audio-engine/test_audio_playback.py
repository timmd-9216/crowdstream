#!/usr/bin/env python3
"""Test direct audio playback without OSC"""

import soundfile as sf
import pyaudio
import numpy as np
import time

print("🔊 Direct Audio Playback Test")
print("=" * 60)

# Load a stem file
stems_path = "stems/01-01 Zjerm (Eurovision 2025 - Albania)/bass.wav"
print(f"📂 Loading: {stems_path}")

try:
    audio_data, sample_rate = sf.read(stems_path, dtype=np.float32)
    print(f"✅ Loaded: {len(audio_data)} samples @ {sample_rate}Hz")

    # Ensure stereo
    if len(audio_data.shape) == 1:
        audio_data = np.column_stack((audio_data, audio_data))

    channels = audio_data.shape[1]
    print(f"🎵 Channels: {channels}")

except Exception as e:
    print(f"❌ Load error: {e}")
    exit(1)

# Setup PyAudio
pa = pyaudio.PyAudio()
chunk_size = 1024

print(f"\n🔊 Opening audio stream...")
stream = pa.open(
    format=pyaudio.paFloat32,
    channels=2,
    rate=sample_rate,
    output=True,
    frames_per_buffer=chunk_size
)

print(f"✅ Stream opened")
print(f"\n▶️  Playing 5 seconds of audio...")
print(f"🔊 TURN UP YOUR VOLUME! Listening...")

# Play first 5 seconds
samples_to_play = int(5 * sample_rate)
pos = 0

while pos < min(samples_to_play, len(audio_data)):
    end = min(pos + chunk_size, len(audio_data))
    chunk = audio_data[pos:end]

    # Apply volume boost
    chunk = chunk * 0.5  # 50% volume

    stream.write(chunk.astype(np.float32).tobytes())
    pos = end

print(f"⏹️  Stopped")

# Cleanup
stream.stop_stream()
stream.close()
pa.terminate()

print(f"\n✅ Test complete!")
print(f"\nDid you hear bass playing? (yes/no)")
print(f"If NO:")
print(f"  - Check system volume")
print(f"  - Check Komplete Audio 6 is connected")
print(f"  - Check audio output in System Preferences")
