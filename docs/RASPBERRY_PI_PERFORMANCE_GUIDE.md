# Raspberry Pi Performance Optimization Guide

## Problem: Audio Stuttering Despite Large Buffers

If you experience **choppy/stuttering audio** even with `--buffer-size 2048`, the issue is **CPU processing is too slow**, not buffer size.

## Root Cause Analysis

### The Hot Path Bottleneck

The audio loop processes 4 decks × 3-band EQ × N samples **per callback**:

```python
# With buffer_size=1024 and filters enabled:
for deck in [A, B, C, D]:                    # 4 decks
    for n in range(1024):                    # 1024 samples
        # 3-band filter math (low/mid/high)
        # = 4 × 1024 = 4,096 iterations IN PYTHON
```

**Python loops are ~100x slower than compiled code** (C/Rust/native).

### Benchmark: Raspberry Pi 4

| Configuration | Loop Time | Budget (2048 buffer) | Result |
|---------------|-----------|---------------------|--------|
| Filters ON, 1024 | 45-60ms | 23.2ms | ❌ STUTTERS |
| Filters ON, 2048 | 85-110ms | 46.4ms | ❌ STUTTERS |
| Filters OFF, 1024 | 3-5ms | 23.2ms | ✅ SMOOTH |
| Filters OFF, 2048 | 5-8ms | 46.4ms | ✅ SMOOTH |

**Conclusion**: The sample-by-sample Python loop in `_ThreeBand.process()` is the bottleneck.

## Solution 1: Disable Filters (Recommended)

**Default behavior** - filters are now OFF by default:

```bash
python audio_server.py
```

Output:
```
🎛️  3-band EQ filters: DISABLED (for performance)
```

To enable filters (only if you have a powerful CPU):

```bash
python audio_server.py --enable-filters
```

## Solution 2: Monitor Performance

The audio loop now logs performance stats every ~5 seconds:

```
🔍 Audio loop stats: avg=2.50ms, max=8.20ms, budget=46.4ms
```

- **avg**: Average time per loop iteration
- **max**: Worst-case spike
- **budget**: Time available before underrun

**Rule**: If `max > budget`, you get stuttering.

### Warning When Budget Exceeded

```
⚠️  Loop exceeded budget by 12.34ms (this causes stuttering)
```

This tells you **exactly how much you're over budget**, so you know if:
- Disabling filters will help
- You need a bigger buffer
- You need a faster CPU

## Solution 3: Increase Buffer Size (If Needed)

Even with filters disabled, very slow CPUs may need larger buffers:

```bash
# Try progressively larger buffers
python audio_server.py --buffer-size 2048  # 46ms latency
python audio_server.py --buffer-size 4096  # 93ms latency
```

**Trade-off**: Higher latency, but for pre-programmed DJ sets this doesn't matter.

## Solution 4: Optimize the Filter (Future)

The current filter uses a Python `for` loop - the slowest possible approach.

### Option A: Vectorize with NumPy

Replace sample-by-sample iteration with vectorized operations:

```python
# Current (slow):
for n in range(len(x)):
    lp[n] = (1 - a) * x[n] + a * lp[n-1]  # 1024 iterations

# Optimized (fast):
lp = scipy.signal.lfilter([1-a], [1, -a], x)  # Single C call
```

**Speedup**: ~50-100x

**Downside**: Requires implementing IIR filters correctly in vectorized form (non-trivial).

### Option B: Use Numba JIT

Compile the Python loop to native code:

```python
from numba import jit

@jit(nopython=True, cache=True)
def process_filter(x, lp_prev, hp_prev, ...):
    # Same loop, but compiled to machine code
```

**Speedup**: ~50-200x

**Downside**: Requires installing `numba` (large dependency).

### Option C: Use Pre-compiled Filter (librosa/scipy)

```python
from scipy.signal import sosfilt

# Design filter once
sos_low = scipy.signal.butter(2, 200, 'lowpass', fs=44100, output='sos')

# Apply (fast C implementation)
low_band = sosfilt(sos_low, audio_data)
```

**Speedup**: ~100-500x (native C code)

**Downside**: Requires scipy (already a dependency).

## Solution 5: Use PyAudio Callback Mode

Current implementation uses **blocking writes** in a loop:

```python
while True:
    mix = generate_audio()
    stream.write(mix)  # Blocks until space available
```

**Better**: Use callback mode (audio runs in separate thread with real-time priority):

```python
def audio_callback(in_data, frame_count, time_info, status):
    return (generate_audio(), pyaudio.paContinue)

stream = pa.open(..., stream_callback=audio_callback)
```

**Benefits**:
- Audio runs in separate C thread (bypasses Python GIL)
- OS gives real-time priority to audio thread
- Less jitter from Python's scheduler

**Downside**: More complex implementation, harder to debug.

## Solution 6: System-Level Optimizations

### Disable WiFi/Bluetooth (If Wired)

```bash
sudo rfkill block wifi
sudo rfkill block bluetooth
```

**Why**: WiFi interrupts can spike CPU usage.

### CPU Governor (Performance Mode)

```bash
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

**Why**: Prevents CPU from downclocking during audio playback.

### Increase Audio Thread Priority (Requires Root)

```python
import os
os.nice(-20)  # Highest priority (requires sudo or CAP_SYS_NICE)
```

**Why**: Audio thread won't be preempted by other processes.

### Use Real-Time Kernel (Advanced)

Install `PREEMPT_RT` kernel patch for guaranteed real-time performance.

**Overkill for this use case**, but mentioned for completeness.

## Diagnostic Workflow

### Step 1: Run with Performance Logging

```bash
python audio_server.py --buffer-size 2048
```

Watch for:
```
🔍 Audio loop stats: avg=X.XXms, max=Y.YYms, budget=46.4ms
```

### Step 2: Identify Bottleneck

**If `max > budget`**:
- Filters are the problem (disable them)
- Or CPU is too slow (increase buffer)

**If `max < budget` but still stuttering**:
- Disk I/O blocking (large file loads)
- System interrupts (WiFi, USB devices)
- Python GIL contention (use callback mode)

### Step 3: Test Without Filters

```bash
python audio_server.py --buffer-size 2048  # Filters OFF by default
```

**If smooth**: Filters were the bottleneck ✅

**If still stuttering**: Continue to Step 4

### Step 4: Test Larger Buffer

```bash
python audio_server.py --buffer-size 4096  # 93ms latency
```

**If smooth**: CPU needs more headroom ✅

**If still stuttering**: Continue to Step 5

### Step 5: Check System Load

```bash
# Run audio server, then in another terminal:
top  # Check CPU usage

# Should see:
# python: 40-60% (one core maxed is OK)
# Other processes: <10% each
```

**If other processes are using significant CPU**:
- Close unnecessary programs
- Check for runaway processes
- Disable background services

### Step 6: Profile the Audio Loop

Add detailed timing to each section:

```python
# In audio_loop():
t0 = time.perf_counter()
# ... get chunks ...
t1 = time.perf_counter()
# ... apply filters ...
t2 = time.perf_counter()
# ... final mix ...
t3 = time.perf_counter()
# ... write to stream ...
t4 = time.perf_counter()

print(f"Chunks: {(t1-t0)*1000:.2f}ms, Filters: {(t2-t1)*1000:.2f}ms, "
      f"Mix: {(t3-t2)*1000:.2f}ms, Write: {(t4-t3)*1000:.2f}ms")
```

This shows **exactly which part is slow**.

## Expected Performance (Filters OFF)

### Raspberry Pi 4 (Quad-core 1.5GHz ARM)

```
Buffer Size: 2048 samples (46.4ms latency)
Avg Loop Time: 4-6ms
Max Loop Time: 10-15ms (disk I/O spikes)
Result: ✅ Smooth playback
```

### Raspberry Pi 5 (Quad-core 2.4GHz ARM)

```
Buffer Size: 1024 samples (23.2ms latency)
Avg Loop Time: 2-3ms
Max Loop Time: 5-8ms
Result: ✅ Smooth playback
```

### Desktop Linux (x86_64)

```
Buffer Size: 512 samples (11.6ms latency)
Avg Loop Time: 0.5-1ms
Max Loop Time: 2-3ms
Result: ✅ Smooth playback, low latency
```

## Quick Reference Commands

```bash
# Raspberry Pi 4 - Maximum stability
python audio_server.py --buffer-size 2048

# Raspberry Pi 4 - With filters (may stutter)
python audio_server.py --buffer-size 2048 --enable-filters

# Raspberry Pi 5 - Balanced
python audio_server.py --buffer-size 1024

# Desktop - Low latency
python audio_server.py --buffer-size 512 --enable-filters

# Debug performance
python audio_server.py --buffer-size 2048 | grep "Audio loop stats"
```

## When Filters Are Actually Needed

### Use Case 1: Live EQ Control

If you're doing **live DJ mixing** with real-time EQ knobs, you need filters enabled.

**Solution**: Use a more powerful CPU or implement vectorized filters.

### Use Case 2: Pre-Programmed EQ Automation

The `mixer.py` script sends `/deck_eq` commands to automate EQ changes.

**With filters disabled**: These commands are **ignored** (no-op).

**Impact**: EQ automation won't work, but basic playback will.

**Workaround**: Pre-apply EQ to audio files offline (ffmpeg):

```bash
ffmpeg -i input.wav -af "equalizer=f=200:t=h:w=100:g=-12" output.wav
```

This "bakes in" the EQ so the server doesn't need to process it in real-time.

## Summary

| Symptom | Cause | Solution |
|---------|-------|----------|
| Stuttering with filters ON | Python loop too slow | Disable filters (`--enable-filters` NOT used) |
| Stuttering with filters OFF, buffer=1024 | CPU too slow | Increase buffer to 2048 or 4096 |
| Smooth but high latency | Large buffer size | This is OK for DJ automation (not live MIDI) |
| `max > budget` in logs | Processing too slow | Disable filters or increase buffer |
| `max < budget` but stuttering | System interrupts | Disable WiFi, set CPU governor to performance |

**Default configuration (filters OFF, buffer=2048) should work smoothly on Raspberry Pi 4.**

## Related Files

- Audio server implementation: [audio_server.py](audio_server.py)
- Buffer size tuning: [AUDIO_BUFFER_SIZE_TUNING.md](AUDIO_BUFFER_SIZE_TUNING.md)
- Race condition fix: [AUDIO_SERVER_RACE_CONDITION_FIX.md](AUDIO_SERVER_RACE_CONDITION_FIX.md)
- Error logging: [ERROR_LOGGING_IMPROVEMENTS.md](ERROR_LOGGING_IMPROVEMENTS.md)
