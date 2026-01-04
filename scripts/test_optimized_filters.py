#!/usr/bin/env python3
"""
Test script to verify optimized filters produce the same output as standard filters.
"""
import numpy as np
import sys
import time

try:
    from scipy.signal import lfilter
    SCIPY_AVAILABLE = True
except ImportError:
    print("❌ scipy not available - cannot test optimized filters")
    sys.exit(1)


# Copy the filter class definitions from audio_server.py
class _ThreeBand:
    """Standard Python implementation (slow but reliable)."""

    def __init__(self, sample_rate: int, low_hz: float = 200.0, high_hz: float = 2000.0):
        self.fs = float(sample_rate)
        self._alp_low = np.exp(-2.0 * np.pi * low_hz / self.fs)
        self._alp_high = np.exp(-2.0 * np.pi * high_hz / self.fs)
        self._lp_prev = np.zeros(2, dtype=np.float32)
        self._hp_prev = np.zeros(2, dtype=np.float32)
        self._x_prev = np.zeros(2, dtype=np.float32)
        self.low_gain = 1.0
        self.mid_gain = 1.0
        self.high_gain = 1.0

    def set_gain(self, band: str, value: float) -> None:
        b = (band or "").strip().lower()
        v = float(value)
        if b.startswith("lo"):
            self.low_gain = v
        elif b.startswith("mi"):
            self.mid_gain = v
        elif b.startswith("hi"):
            self.high_gain = v
        else:
            raise ValueError(f"Unknown band '{band}'")

    def process(self, x: np.ndarray) -> np.ndarray:
        if x.size == 0:
            return x
        out = np.empty_like(x)
        lp_prev = self._lp_prev.astype(np.float32)
        hp_prev = self._hp_prev.astype(np.float32)
        x_prev = self._x_prev.astype(np.float32)
        a_lp = float(self._alp_low)
        a_hp = float(self._alp_high)
        lg = float(self.low_gain)
        mg = float(self.mid_gain)
        hg = float(self.high_gain)
        for n in range(x.shape[0]):
            xnL = x[n, 0]
            xnR = x[n, 1]
            lpL = (1.0 - a_lp) * xnL + a_lp * lp_prev[0]
            lpR = (1.0 - a_lp) * xnR + a_lp * lp_prev[1]
            hpL = a_hp * (hp_prev[0] + xnL - x_prev[0])
            hpR = a_hp * (hp_prev[1] + xnR - x_prev[1])
            midL = xnL - lpL - hpL
            midR = xnR - lpR - hpR
            out[n, 0] = lg * lpL + mg * midL + hg * hpL
            out[n, 1] = lg * lpR + mg * midR + hg * hpR
            lp_prev[0] = lpL; lp_prev[1] = lpR
            hp_prev[0] = hpL; hp_prev[1] = hpR
            x_prev[0] = xnL; x_prev[1] = xnR
        self._lp_prev[:] = lp_prev
        self._hp_prev[:] = hp_prev
        self._x_prev[:] = x_prev
        return out


class _ThreeBandOptimized:
    """Optimized scipy implementation (50-100x faster)."""

    def __init__(self, sample_rate: int, low_hz: float = 200.0, high_hz: float = 2000.0):
        self.fs = float(sample_rate)
        self._alp_low = np.exp(-2.0 * np.pi * low_hz / self.fs)
        self._alp_high = np.exp(-2.0 * np.pi * high_hz / self.fs)

        self._b_lp = np.array([1.0 - self._alp_low], dtype=np.float32)
        self._a_lp = np.array([1.0, -self._alp_low], dtype=np.float32)

        self._b_hp = np.array([self._alp_high, -self._alp_high], dtype=np.float32)
        self._a_hp = np.array([1.0, -self._alp_high], dtype=np.float32)

        self._zi_lp_L = np.zeros(1, dtype=np.float32)
        self._zi_lp_R = np.zeros(1, dtype=np.float32)
        self._zi_hp_L = np.zeros(1, dtype=np.float32)
        self._zi_hp_R = np.zeros(1, dtype=np.float32)

        self.low_gain = 1.0
        self.mid_gain = 1.0
        self.high_gain = 1.0

    def set_gain(self, band: str, value: float) -> None:
        b = (band or "").strip().lower()
        v = float(value)
        if b.startswith("lo"):
            self.low_gain = v
        elif b.startswith("mi"):
            self.mid_gain = v
        elif b.startswith("hi"):
            self.high_gain = v
        else:
            raise ValueError(f"Unknown band '{band}'")

    def process(self, x: np.ndarray) -> np.ndarray:
        if x.size == 0:
            return x

        x_L = x[:, 0].astype(np.float32)
        x_R = x[:, 1].astype(np.float32)

        lp_L, self._zi_lp_L = lfilter(self._b_lp, self._a_lp, x_L, zi=self._zi_lp_L)
        lp_R, self._zi_lp_R = lfilter(self._b_lp, self._a_lp, x_R, zi=self._zi_lp_R)

        hp_L, self._zi_hp_L = lfilter(self._b_hp, self._a_hp, x_L, zi=self._zi_hp_L)
        hp_R, self._zi_hp_R = lfilter(self._b_hp, self._a_hp, x_R, zi=self._zi_hp_R)

        mid_L = x_L - lp_L - hp_L
        mid_R = x_R - lp_R - hp_R

        out_L = self.low_gain * lp_L + self.mid_gain * mid_L + self.high_gain * hp_L
        out_R = self.low_gain * lp_R + self.mid_gain * mid_R + self.high_gain * hp_R

        return np.column_stack([out_L, out_R]).astype(np.float32)

print("🧪 Testing optimized filters vs standard filters...")
print()

# Test parameters
sample_rate = 44100
chunk_size = 1024

# Create test signal: 1 second of white noise
duration = 1.0
num_samples = int(sample_rate * duration)
test_signal = np.random.randn(num_samples, 2).astype(np.float32) * 0.1

print(f"📊 Test signal: {num_samples} samples, {duration}s duration")
print()

# Create both filter types
standard_filter = _ThreeBand(sample_rate)
optimized_filter = _ThreeBandOptimized(sample_rate)

# Set the same gains on both
standard_filter.set_gain('low', 0.5)
standard_filter.set_gain('mid', 0.8)
standard_filter.set_gain('high', 0.3)

optimized_filter.set_gain('low', 0.5)
optimized_filter.set_gain('mid', 0.8)
optimized_filter.set_gain('high', 0.3)

print("🎛️  Filter gains: low=0.5, mid=0.8, high=0.3")
print()

# Process in chunks like the real audio loop does
num_chunks = num_samples // chunk_size
standard_output = []
optimized_output = []

print(f"⏱️  Processing {num_chunks} chunks of {chunk_size} samples...")
print()

# Time the standard filter
start = time.perf_counter()
for i in range(num_chunks):
    chunk = test_signal[i*chunk_size:(i+1)*chunk_size]
    processed = standard_filter.process(chunk)
    standard_output.append(processed)
standard_time = time.perf_counter() - start
standard_output = np.vstack(standard_output)

print(f"✅ Standard filter: {standard_time*1000:.2f}ms total ({standard_time*1000/num_chunks:.3f}ms per chunk)")

# Time the optimized filter
start = time.perf_counter()
for i in range(num_chunks):
    chunk = test_signal[i*chunk_size:(i+1)*chunk_size]
    processed = optimized_filter.process(chunk)
    optimized_output.append(processed)
optimized_time = time.perf_counter() - start
optimized_output = np.vstack(optimized_output)

print(f"✅ Optimized filter: {optimized_time*1000:.2f}ms total ({optimized_time*1000/num_chunks:.3f}ms per chunk)")
print()

speedup = standard_time / optimized_time
print(f"🚀 Speedup: {speedup:.1f}x faster")
print()

# Compare outputs
difference = np.abs(standard_output - optimized_output)
max_diff = np.max(difference)
mean_diff = np.mean(difference)
rms_diff = np.sqrt(np.mean(difference**2))

print("📊 Output comparison:")
print(f"   Max difference:  {max_diff:.6f}")
print(f"   Mean difference: {mean_diff:.6f}")
print(f"   RMS difference:  {rms_diff:.6f}")
print()

# Check if outputs are close enough (within 0.1% tolerance)
tolerance = 0.001
if max_diff < tolerance:
    print(f"✅ PASS: Outputs match within tolerance ({tolerance})")
    print("   Optimized filters are working correctly!")
else:
    print(f"❌ FAIL: Outputs differ by more than tolerance ({tolerance})")
    print("   There may be a bug in the optimized implementation")
    sys.exit(1)
