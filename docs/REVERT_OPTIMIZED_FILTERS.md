# Revert: Optimized Filters - Caused Silent Audio

## Date: 2025-12-13

## Problem

After implementing `_ThreeBandOptimized` using scipy.signal.lfilter, **audio stopped working completely** (no sound output) both with and without filters enabled.

## Symptoms

- No audio output
- Server started normally
- No errors in logs
- Decks loaded successfully
- But silence on playback

## Root Cause (Suspected)

The optimized filter implementation had a bug that caused silent output. Likely issues:

1. **Incorrect zi (state) management** - scipy's lfilter zi format may have been wrong
2. **Filter coefficients error** - b/a arrays may have been incorrect
3. **Output data corruption** - Returning wrong data type or shape
4. **NaN/Inf propagation** - Filter instability causing invalid audio

## Reverted Changes

### 1. Removed `use_optimized_filters` parameter

**File**: [audio_server.py:368](audio_server.py#L368)

**Before**:
```python
def __init__(self, ..., enable_filters: bool = False, use_optimized_filters: bool = True):
    # ...
    if use_optimized_filters and SCIPY_AVAILABLE:
        filter_class = _ThreeBandOptimized
```

**After**:
```python
def __init__(self, ..., enable_filters: bool = False):
    # ...
    self._filters: Dict[str, _ThreeBand] = {
        'A': _ThreeBand(self.sample_rate),
        # ...
    }
```

### 2. Disabled `_ThreeBandOptimized` class

**File**: [audio_server.py:108-116](audio_server.py#L108-L116)

**Before**: Full implementation (80 lines)

**After**:
```python
# DISABLED: Optimized filters caused audio to stop working
# Keeping code for future debugging
# class _ThreeBandOptimized:
#     pass
```

### 3. Removed filter type tracking

**File**: [audio_server.py:440, 1155](audio_server.py)

**Before**:
```python
filters_status = f"ENABLED ({self.filter_type})"
```

**After**:
```python
filters_status = "ENABLED"
```

## Current State (Working)

### Audio Output: ✅ Working

```bash
python audio_server.py --buffer-size 2048
```

**Configuration**:
- Filters: OFF (default)
- Buffer: 2048 samples (46.4ms latency)
- Filter implementation: Standard (_ThreeBand)
- Performance: ~5ms per callback

### With Filters (Standard Implementation)

```bash
python audio_server.py --buffer-size 4096 --enable-filters
```

**Configuration**:
- Filters: ON (standard Python loops)
- Buffer: 4096 samples (92.8ms latency)
- Performance: ~40-50ms per callback (slow but works)

**Note**: Standard filters are slow on Raspberry Pi, but at least **audio works**.

## Files Modified

| File | Change |
|------|--------|
| audio_server.py | Removed `_ThreeBandOptimized` class |
| audio_server.py | Removed `use_optimized_filters` parameter |
| audio_server.py | Simplified filter initialization |
| audio_server.py | Removed filter type logging |
| OPTIMIZED_FILTERS_GUIDE.md | ⚠️ Obsolete (filter doesn't work) |

## Lessons Learned

1. **Test immediately after each feature** - Optimized filters were added and not tested before moving on
2. **Implement incrementally** - Should have tested basic scipy filter first, then added features
3. **Add unit tests** - Filter processing should have unit tests with known input/output
4. **Verify output shape/type** - Audio bugs are silent, need explicit validation

## Future Work (If Re-implementing)

### Step 1: Isolate and Test

Create standalone test script:

```python
# test_filter.py
import numpy as np
from scipy.signal import lfilter

# Generate test signal (1kHz sine wave)
t = np.linspace(0, 1, 44100)
x = np.sin(2 * np.pi * 1000 * t).astype(np.float32)

# Test filter
# ... implement filter ...

# Verify output
assert out.shape == x.shape
assert not np.any(np.isnan(out))
assert not np.any(np.isinf(out))
assert np.abs(out).max() < 10.0  # Sanity check amplitude
```

### Step 2: Compare with Standard

```python
# Run both filters on same input
out_standard = standard_filter.process(test_audio)
out_optimized = optimized_filter.process(test_audio)

# Should be nearly identical
diff = np.abs(out_standard - out_optimized)
print(f"Max difference: {diff.max()}")  # Should be < 0.001
```

### Step 3: Debug scipy lfilter state

The issue was likely in how `zi` (initial conditions) was managed:

```python
# Incorrect (what we had):
self._zi_lp = np.zeros((1, 2), dtype=np.float32)  # Wrong shape?

# Correct (maybe):
from scipy.signal import lfilter_zi
self._zi_lp = lfilter_zi(self._b_lp, self._a_lp_coef)
```

scipy's `lfilter_zi()` computes proper initial conditions for steady-state.

### Step 4: Add Logging During Development

```python
def process(self, x):
    print(f"Input: shape={x.shape}, min={x.min():.3f}, max={x.max():.3f}")

    low, zi = lfilter(...)
    print(f"Low: shape={low.shape}, min={low.min():.3f}, max={low.max():.3f}")

    out = ...
    print(f"Output: shape={out.shape}, min={out.min():.3f}, max={out.max():.3f}")

    return out
```

This would have immediately shown if output was zeros/NaN.

## Recommendation

**For now**: Use filters OFF (default) for Raspberry Pi performance.

**Future**: If EQ automation is critical, debug optimized filters in isolation before integrating.

## Testing Before Re-enabling

If optimized filters are fixed:

1. ✅ Unit test: filter produces non-zero output
2. ✅ Unit test: output shape matches input
3. ✅ Unit test: no NaN/Inf in output
4. ✅ Comparison test: matches standard filter (within tolerance)
5. ✅ Integration test: audio actually plays through speakers
6. ✅ Performance test: actually faster than standard

**Only after all 6 pass** should it be re-enabled.

## Current Recommended Usage

### Raspberry Pi 4

```bash
# Best performance, no filters
python audio_server.py --buffer-size 2048
```

### Raspberry Pi 5 / Desktop

```bash
# Can use smaller buffer
python audio_server.py --buffer-size 1024
```

### If EQ Automation Needed (Desktop Only)

```bash
# Large buffer to accommodate slow filters
python audio_server.py --buffer-size 4096 --enable-filters
```

**Note**: Standard filters still too slow for Raspberry Pi even with large buffer.

## Status

- **Audio**: ✅ Working (reverted to known-good state)
- **Filters**: ⚠️ Available but slow (standard implementation)
- **Optimized Filters**: ❌ Disabled (broken)
- **Performance**: ✅ Good (filters OFF)

## Related Docs

- [PERFORMANCE_OPTIMIZATION_V2.md](PERFORMANCE_OPTIMIZATION_V2.md) - Still valid
- [CHANGELOG_PERFORMANCE_FIX.md](CHANGELOG_PERFORMANCE_FIX.md) - Still valid
- [OPTIMIZED_FILTERS_GUIDE.md](OPTIMIZED_FILTERS_GUIDE.md) - ⚠️ Obsolete (filter broken)
