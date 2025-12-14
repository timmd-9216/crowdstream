#!/usr/bin/env python3
"""Test real stem playback through audio_server"""

from pythonosc import udp_client
import time
import os

print("🧪 Testing REAL stem playback through audio_server.py")
print("=" * 70)
print()

client = udp_client.SimpleUDPClient("127.0.0.1", 57120)

# Get absolute path
stems_path = os.path.abspath("stems/01-01 Zjerm (Eurovision 2025 - Albania)/bass.wav")
print(f"📂 File: {stems_path}")
print(f"📁 Exists: {os.path.exists(stems_path)}")
print()

# Step 1: Load buffer
print("1️⃣  Loading buffer 1000...")
client.send_message("/load_buffer", [1000, stems_path, "TEST_Bass"])
time.sleep(1)

# Step 2: Set full volume on deck A
print("2️⃣  Setting crossfade to 100% Deck A...")
client.send_message("/crossfade_levels", [1.0, 0.0])
time.sleep(0.2)

# Step 3: Play at max volume
print("3️⃣  Playing buffer 1000 (max volume, normal rate)...")
client.send_message("/play_stem", [1000, 1.0, 1.0, 1, 0.0])
time.sleep(0.5)

print()
print("🔊 AUDIO SHOULD BE PLAYING NOW!")
print("   Listen for 10 seconds...")
print()

# Wait and show countdown
for i in range(10, 0, -1):
    print(f"   ⏱️  {i} seconds... ", end="")

    # Every 2 seconds, verify player is still active
    if i % 3 == 0:
        client.send_message("/get_status", [])
        print("(status check)")
    else:
        print()

    time.sleep(1)

print()
print("4️⃣  Stopping playback...")
client.send_message("/stop_stem", [1000])
time.sleep(0.5)

print()
print("=" * 70)
print("✅ Test complete!")
print()
print("Did you hear bass playing? If NOT, check audio_server terminal for:")
print("  - 'Audio loop started' message")
print("  - '▶️ Playing buffer 1000' message")
print("  - Any errors in the audio loop")
print()
print("Also check:")
print("  - System volume is up")
print("  - Komplete Audio 6 is selected as output")
print("  - Audio is not muted")
