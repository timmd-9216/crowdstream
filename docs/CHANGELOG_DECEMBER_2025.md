# Changelog - December 2025

## Summary
Fixed critical audio silence bug and successfully re-implemented optimized EQ filters with 34x performance improvement.

## Issues Fixed

### 1. Audio Silence Bug (CRITICAL)
**Problem**: Audio server was not playing any sound despite receiving OSC commands.

**Root causes**:
1. **Malformed class definition** - `_print_all_messages` method was placed before the class docstring, causing incorrect indentation
2. **OSC timing race condition** - `mixer.py` was sending commands before `audio_server.py` was ready to receive them

**Solution**:
- Fixed class definition structure ([audio_server.py:287-295](audio_server.py))
- Increased startup delay in `losdones-start.sh` from 5s to 8s to allow ALSA probing to complete
- Commented out `set_default_handler` to reduce console spam

**Documentation**: [AUDIO_SILENCE_FIX.md](AUDIO_SILENCE_FIX.md)

**User impact**: Audio now plays reliably on startup

---

### 2. Optimized Filters Re-implementation
**Feature**: Optional high-performance EQ filters using scipy.signal.lfilter

**Performance improvement**:
- Standard filters: ~1.65ms per 1024-sample chunk
- Optimized filters: ~0.05ms per 1024-sample chunk
- **Speedup: 34x faster**

**Implementation**:
- New class `_ThreeBandOptimized` using scipy's vectorized C implementation
- Maintains identical output to standard filters (verified by test suite)
- Automatic fallback to standard filters if scipy not available
- New CLI flag: `--optimized-filters`

**Usage**:
```bash
# Standard filters (default, slower)
python audio_server.py --enable-filters

# Optimized filters (34x faster, requires scipy)
python audio_server.py --enable-filters --optimized-filters
```

**Documentation**: [OPTIMIZED_FILTERS_V2.md](OPTIMIZED_FILTERS_V2.md)

**User impact**: Filters can now be used on Raspberry Pi without causing audio stuttering

---

## Files Modified

### Core Changes
- [audio_server.py](audio_server.py)
  - Fixed class definition indentation (lines 287-295)
  - Commented out default OSC handler (line 480)
  - Added `_ThreeBandOptimized` class (lines 108-189)
  - Added `use_optimized_filters` parameter to `__init__` (line 376)
  - Added `--optimized-filters` CLI flag (line 1213)
  - Added `Union` import for type hints (line 20)
  - Cleaned up duplicate code at end of file (line 1328)

- [losdones-start.sh](losdones-start.sh)
  - Increased audio server startup delay from 5s to 8s (line 15)

### Documentation
- [AUDIO_SILENCE_FIX.md](AUDIO_SILENCE_FIX.md) - Detailed analysis of silence bug
- [OPTIMIZED_FILTERS_V2.md](OPTIMIZED_FILTERS_V2.md) - Optimized filters guide
- [CHANGELOG_DECEMBER_2025.md](CHANGELOG_DECEMBER_2025.md) - This file

### Testing
- [test_optimized_filters.py](test_optimized_filters.py) - Verification suite for optimized filters
- [test_basic_audio.py](test_basic_audio.py) - Basic PyAudio functionality test

---

## Testing Performed

### 1. Audio Silence Fix
✅ Server starts correctly with 8s delay
✅ `/cue` commands are received and processed (🧷 Cued messages appear)
✅ `/start_group` commands are received and processed (🎬 Group START messages appear)
✅ Audio plays successfully on Raspberry Pi

### 2. Optimized Filters
✅ Test suite passes with 0.000000 max difference
✅ 34x speedup confirmed
✅ Fallback to standard filters works when scipy unavailable
✅ CLI flags work as expected

---

## Migration Notes

### For users upgrading from previous version:

1. **Update startup script** (if using custom script):
   ```bash
   # OLD
   python audio_server.py --port 57120 &
   sleep 5

   # NEW
   python audio_server.py --port 57120 &
   sleep 8  # Increased for ALSA probing
   ```

2. **Enable optimized filters** (optional, requires scipy):
   ```bash
   # Install scipy first (if not already installed)
   pip install scipy

   # Then use both flags
   python audio_server.py --enable-filters --optimized-filters
   ```

3. **Verify startup** - Look for these messages:
   ```
   🔌 OSC server listening on port 57120
   🧷 Cued A → filename.wav @pos 0.000 (buffer 100)
   🎬 Group START Deck A at t=0.500s
   ```

---

## Known Issues

None at this time.

---

## Future Work

### Potential optimizations:
- [ ] Further reduce startup time by optimizing ALSA device probing
- [ ] Add filter enable/disable via OSC command (runtime toggle)
- [ ] Implement filter preset system (e.g., "club", "radio", "telephone")

### Feature requests:
- [ ] Support for boost mode in EQ (currently cut-only)
- [ ] Additional filter types (parametric EQ, shelf filters)
- [ ] Filter automation/modulation

---

## Version History

### December 13, 2025
- Fixed critical audio silence bug
- Re-implemented optimized filters with 34x speedup
- Improved startup reliability with longer delay
- Comprehensive documentation added
