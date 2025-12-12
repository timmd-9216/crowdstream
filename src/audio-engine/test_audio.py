#!/usr/bin/env python3
"""
Audio diagnostic tool for Raspberry Pi
Tests PyAudio configuration and playback
"""

import pyaudio
import numpy as np
import sys

def test_audio_devices():
    """List and test audio devices"""
    print("=" * 60)
    print("🔍 AUDIO DEVICE DIAGNOSTICS")
    print("=" * 60)

    pa = pyaudio.PyAudio()

    # List all devices
    print("\n📡 Available Audio Devices:")
    device_count = pa.get_device_count()

    for i in range(device_count):
        try:
            info = pa.get_device_info_by_index(i)
            if info['maxOutputChannels'] > 0:
                host_api = pa.get_host_api_info_by_index(info['hostApi'])
                is_default = " (DEFAULT)" if i == pa.get_default_output_device_info()['index'] else ""
                print(f"  [{i}] {info['name']}")
                print(f"      Host API: {host_api['name']}")
                print(f"      Channels: {info['maxOutputChannels']}")
                print(f"      Sample Rate: {int(info['defaultSampleRate'])} Hz{is_default}")
        except Exception as e:
            print(f"  [{i}] Error: {e}")

    # Get default device
    try:
        default_device = pa.get_default_output_device_info()
        print(f"\n✅ Default Output Device: [{default_device['index']}] {default_device['name']}")
        print(f"   Sample Rate: {int(default_device['defaultSampleRate'])} Hz")
        print(f"   Channels: {default_device['maxOutputChannels']}")
    except Exception as e:
        print(f"\n❌ No default output device found: {e}")
        pa.terminate()
        return False

    pa.terminate()
    return True

def test_audio_playback(device_id=None):
    """Test audio playback with a simple tone"""
    print("\n" + "=" * 60)
    print("🔊 AUDIO PLAYBACK TEST")
    print("=" * 60)

    pa = pyaudio.PyAudio()

    # Audio parameters
    sample_rate = 44100
    duration = 2.0  # seconds
    frequency = 440.0  # A4 note

    print(f"\n🎵 Generating {frequency} Hz test tone ({duration}s)...")

    # Generate sine wave
    t = np.linspace(0, duration, int(sample_rate * duration))
    samples = np.sin(2 * np.pi * frequency * t) * 0.3  # 30% volume

    # Convert to stereo
    stereo_samples = np.column_stack((samples, samples)).astype(np.float32)

    print(f"📊 Audio data shape: {stereo_samples.shape}")
    print(f"📊 Data type: {stereo_samples.dtype}")
    print(f"📊 Sample rate: {sample_rate} Hz")

    try:
        # Open stream
        stream_params = {
            'format': pyaudio.paFloat32,
            'channels': 2,
            'rate': sample_rate,
            'output': True,
            'frames_per_buffer': 1024
        }

        if device_id is not None:
            stream_params['output_device_index'] = device_id
            device_info = pa.get_device_info_by_index(device_id)
            print(f"\n🎯 Using device: [{device_id}] {device_info['name']}")
        else:
            print(f"\n🎯 Using default device")

        stream = pa.open(**stream_params)

        print(f"\n▶️  Playing test tone...")

        # Write audio data
        stream.write(stereo_samples.tobytes())

        print(f"✅ Playback completed successfully!")

        # Cleanup
        stream.stop_stream()
        stream.close()

    except Exception as e:
        print(f"\n❌ Playback failed: {e}")
        pa.terminate()
        return False

    pa.terminate()
    return True

def main():
    print("\n🎛️ PyAudio Audio Diagnostic Tool")
    print("For Raspberry Pi and Linux systems\n")

    # Test 1: List devices
    if not test_audio_devices():
        print("\n❌ Device enumeration failed")
        sys.exit(1)

    # Test 2: Playback with default device
    print("\n" + "=" * 60)
    print("Testing playback with DEFAULT device...")
    print("=" * 60)

    if test_audio_playback():
        print("\n✅ All tests passed!")
    else:
        print("\n⚠️  Playback test failed")
        print("\nTroubleshooting:")
        print("1. Check ALSA configuration: aplay -L")
        print("2. Test with aplay: speaker-test -t wav -c 2")
        print("3. Check volume: alsamixer")
        print("4. Verify device permissions")

        # Offer to test with specific device
        print("\nTry testing with a specific device:")
        try:
            pa = pyaudio.PyAudio()
            device_count = pa.get_device_count()
            pa.terminate()

            device_id = input(f"\nEnter device ID (0-{device_count-1}) or press Enter to skip: ").strip()
            if device_id:
                test_audio_playback(int(device_id))
        except:
            pass

if __name__ == "__main__":
    main()
