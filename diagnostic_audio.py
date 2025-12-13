#!/usr/bin/env python3
"""Audio server diagnostic script - check what's broken."""

import sys
import numpy as np

print("=" * 60)
print("AUDIO SERVER DIAGNOSTIC")
print("=" * 60)

# Check 1: Python version
print(f"\n1. Python version: {sys.version}")

# Check 2: Import dependencies
print("\n2. Checking imports...")
try:
    import pyaudio
    print(f"   ✅ pyaudio: {pyaudio.__version__}")
except ImportError as e:
    print(f"   ❌ pyaudio: {e}")

try:
    import soundfile as sf
    print(f"   ✅ soundfile: {sf.__version__}")
except ImportError as e:
    print(f"   ❌ soundfile: {e}")

try:
    import numpy as np
    print(f"   ✅ numpy: {np.__version__}")
except ImportError as e:
    print(f"   ❌ numpy: {e}")

try:
    from pythonosc import dispatcher
    print(f"   ✅ python-osc: OK")
except ImportError as e:
    print(f"   ❌ python-osc: {e}")

try:
    from scipy.signal import lfilter
    import scipy
    print(f"   ✅ scipy: {scipy.__version__}")
    SCIPY_OK = True
except ImportError as e:
    print(f"   ❌ scipy: {e}")
    SCIPY_OK = False

# Check 3: Test audio initialization
print("\n3. Testing PyAudio initialization...")
try:
    pa = pyaudio.PyAudio()
    info = pa.get_default_output_device_info()
    print(f"   ✅ Default output: {info['name']}")
    print(f"      Sample rate: {info['defaultSampleRate']}")
    print(f"      Channels: {info['maxOutputChannels']}")
    pa.terminate()
except Exception as e:
    print(f"   ❌ PyAudio error: {e}")

# Check 4: Test filter
print("\n4. Testing filter implementations...")

if SCIPY_OK:
    print("   Testing optimized filter (scipy)...")
    try:
        sample_rate = 44100
        low_hz = 200.0
        a_lp = float(np.exp(-2.0 * np.pi * low_hz / sample_rate))
        b_lp = np.array([1.0 - a_lp], dtype=np.float32)
        a_lp_coef = np.array([1.0, -a_lp], dtype=np.float32)

        x = np.random.randn(1024, 2).astype(np.float32) * 0.1
        zi = np.zeros(1, dtype=np.float32)

        out, zi_new = lfilter(b_lp, a_lp_coef, x[:, 0], zi=zi)
        print(f"   ✅ Optimized filter works (output shape: {out.shape})")
    except Exception as e:
        print(f"   ❌ Optimized filter error: {e}")
        import traceback
        traceback.print_exc()

# Check 5: Try to import audio_server
print("\n5. Testing audio_server module...")
try:
    import audio_server
    print(f"   ✅ audio_server module imports OK")
    print(f"      SCIPY_AVAILABLE: {audio_server.SCIPY_AVAILABLE}")
except Exception as e:
    print(f"   ❌ audio_server import error: {e}")
    import traceback
    traceback.print_exc()

# Check 6: Test creating server instance
print("\n6. Testing server initialization...")
try:
    from audio_server import PythonAudioServer
    server = PythonAudioServer(enable_filters=False)
    print(f"   ✅ Server created (filters OFF)")
    print(f"      Sample rate: {server.sample_rate}")
    print(f"      Chunk size: {server.chunk_size}")
    print(f"      Channels: {server.channels}")
    server.stop()
except Exception as e:
    print(f"   ❌ Server init error: {e}")
    import traceback
    traceback.print_exc()

if SCIPY_OK:
    print("\n7. Testing server with optimized filters...")
    try:
        from audio_server import PythonAudioServer
        server = PythonAudioServer(enable_filters=True, use_optimized_filters=True)
        print(f"   ✅ Server created (optimized filters ON)")
        print(f"      Filter type: {server.filter_type}")

        # Test filter processing
        test_audio = np.random.randn(256, 2).astype(np.float32) * 0.1
        filtered = server._filters['A'].process(test_audio)
        print(f"   ✅ Filter processing works (output shape: {filtered.shape})")

        server.stop()
    except Exception as e:
        print(f"   ❌ Optimized filter test error: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
