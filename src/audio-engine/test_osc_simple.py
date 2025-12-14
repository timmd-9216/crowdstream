#!/usr/bin/env python3
"""Simple OSC test to verify connectivity"""

from pythonosc import udp_client
import time

print("🧪 Testing OSC connection to audio_server.py...")
print()

# Create client
client = udp_client.SimpleUDPClient("127.0.0.1", 57120)
print("✅ Client created")

# Test 1: Get status
print("\n1️⃣  Sending /get_status...")
client.send_message("/get_status", [])
time.sleep(0.5)

# Test 2: Test tone
print("\n2️⃣  Sending /test_tone (440 Hz)...")
client.send_message("/test_tone", [440])
time.sleep(0.5)

# Test 3: Load a real buffer
import os
stems_dir = "stems/01-01 Zjerm (Eurovision 2025 - Albania)"
bass_file = os.path.join(stems_dir, "bass.wav")
abs_path = os.path.abspath(bass_file)

if os.path.exists(abs_path):
    print(f"\n3️⃣  Loading buffer: {bass_file}")
    client.send_message("/load_buffer", [1000, abs_path, "TEST_Bass"])
    time.sleep(1)

    print("\n4️⃣  Playing buffer 1000...")
    client.send_message("/play_stem", [1000, 1.0, 0.8, 1, 0.0])
    time.sleep(2)

    print("\n5️⃣  Stopping buffer 1000...")
    client.send_message("/stop_stem", [1000])
    time.sleep(0.5)
else:
    print(f"\n⚠️  File not found: {abs_path}")

print("\n✅ Test complete!")
print("\nCheck the audio_server.py terminal for output.")
print("You should see messages like:")
print("  📡 OSC RECEIVED: /get_status")
print("  📡 OSC RECEIVED: /load_buffer (1000, ...)")
print("  ✅ Loaded TEST_Bass")
print("  📡 OSC RECEIVED: /play_stem (1000, ...)")
print("  ▶️  Playing buffer 1000")
