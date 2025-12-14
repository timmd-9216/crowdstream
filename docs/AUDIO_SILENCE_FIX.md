# Audio Silence Fix - OSC Timing Issue

## Problem
Audio server was receiving OSC commands but not playing any sound. Commands like `/cue` and `/start_group` were being sent but not processed.

## Root Cause
**Two issues were identified:**

### 1. Malformed class definition (lines 287-294)
The `_print_all_messages` method was placed BEFORE the class docstring, causing incorrect indentation:

```python
class PythonAudioServer:
    def _print_all_messages(self, address: str, *args: object) -> None:  # ❌ WRONG
        """Print every OSC message received (for debugging)."""
        ...
    """Main audio server class managing audio playback and OSC interface."""  # ❌ Docstring after method
```

This should be:

```python
class PythonAudioServer:
    """Main audio server class managing audio playback and OSC interface."""  # ✅ Docstring first

    def _print_all_messages(self, address: str, *args: object) -> None:  # ✅ Method properly indented
        """Print every OSC message received (for debugging)."""
        ...
```

### 2. OSC command timing issue
The `mixer.py` script was sending OSC commands **before** the audio server was ready to receive them:

**Timeline of events:**
```
T+0s:   mixer.py starts sending OSC commands
        → /cue ('A', ...)
        → /start_group (0.5, 'A')

T+2s:   [ALSA device probing happens - takes several seconds]
        ALSA lib pcm.c:2722: Unknown PCM cards.pcm.front
        [... many ALSA warnings ...]

T+4s:   🎛️💾 PYTHON AUDIO SERVER INITIALIZING 💾🎛️

T+5s:   🔌 OSC server listening on port 57120  ← READY TOO LATE!
```

Commands sent at T+0s were **lost** because the OSC server wasn't listening yet.

## Solution

### Fix 1: Correct class definition
Move the docstring to the correct position and properly indent the method.

### Fix 2: Increase startup delay
In [losdones-start.sh](losdones-start.sh), increase the sleep time after launching `audio_server.py`:

```bash
python audio_server.py --port 57120 &
sleep 8  # Was 5s - increased to allow ALSA probing to complete
```

On Raspberry Pi, PyAudio takes 5-7 seconds to probe all ALSA devices before the OSC server starts listening.

## Verification
After the fix, you should see these messages appearing in sequence:

```
🎛️💾 PYTHON AUDIO SERVER READY 💾🎛️
→ /cue ('A', ...)
🧷 Cued A → filename.wav @pos 0.000 (buffer 100)
→ /start_group (0.5, 'A')
🎬 Group START Deck A at t=0.500s
```

If you see the `🧷 Cued` and `🎬 Group START` messages, the audio should now be playing.

## Additional Notes

- The `set_default_handler(self._print_all_messages)` line was also commented out to reduce console spam
- The `/deck_eq` commands are silently ignored when `enable_filters=False` (performance mode)
- ALSA warnings are normal on Raspberry Pi and can be safely ignored
