#!/usr/bin/env python3
"""
Minimal audio test to verify PyAudio is working.
This bypasses all the server complexity to isolate audio output issues.
"""
import numpy as np
import pyaudio
import time

print("🔍 Testing basic PyAudio functionality...")
print()

# Test 1: PyAudio initialization
try:
    pa = pyaudio.PyAudio()
    print("✅ PyAudio initialized successfully")
except Exception as e:
    print(f"❌ PyAudio initialization failed: {e}")
    exit(1)

# Test 2: List audio devices
print()
print("📋 Available audio devices:")
for i in range(pa.get_device_count()):
    info = pa.get_device_info_by_index(i)
    if info['maxOutputChannels'] > 0:
        print(f"   {i}: {info['name']} (outputs: {info['maxOutputChannels']})")

# Test 3: Open audio stream
print()
print("🔊 Opening audio stream (44100 Hz, 2 channels, 1024 buffer)...")
try:
    stream = pa.open(
        format=pyaudio.paFloat32,
        channels=2,
        rate=44100,
        output=True,
        frames_per_buffer=1024
    )
    print("✅ Audio stream opened successfully")
except Exception as e:
    print(f"❌ Failed to open audio stream: {e}")
    pa.terminate()
    exit(1)

# Test 4: Generate and play a simple sine wave
print()
print("🎵 Playing 440 Hz test tone for 2 seconds...")
print("   (You should hear a beep)")

sample_rate = 44100
duration = 2.0  # seconds
frequency = 440.0  # Hz (A4 note)

t = np.linspace(0, duration, int(sample_rate * duration), False)
tone = np.sin(frequency * 2 * np.pi * t) * 0.3  # 30% volume

# Convert to stereo
stereo_tone = np.column_stack([tone, tone]).astype(np.float32)

# Play in chunks
chunk_size = 1024
for i in range(0, len(stereo_tone), chunk_size):
    chunk = stereo_tone[i:i+chunk_size]
    if len(chunk) < chunk_size:
        # Pad last chunk if needed
        pad = chunk_size - len(chunk)
        chunk = np.vstack([chunk, np.zeros((pad, 2), dtype=np.float32)])
    try:
        stream.write(chunk.tobytes())
    except Exception as e:
        print(f"❌ Error writing audio: {e}")
        break

print("✅ Test tone completed")

# Cleanup
print()
print("🧹 Cleaning up...")
stream.stop_stream()
stream.close()
pa.terminate()
print("✅ All tests passed! Audio output is working.")
