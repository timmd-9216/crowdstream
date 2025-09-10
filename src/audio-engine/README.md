# Music Mixing Engine 🎵

A **real-time** music mixing engine that combines stems from different songs with smart memory management.

***
Demo: Livecoding session, mixing stems from different songs:
https://youtu.be/1cXhiNixB_o
***
ect for another experimental uses and details.

## Features

### 🎛️ Mixing Capabilities
- **Stem Separation**: Works with bass, drums, vocals, piano, and other stems
- **Song Structure Analysis**: Understands verse, chorus, bridge, intro, outro sections  
- **Intelligent Stem Selection**: Different strategies per mixing theme
- **Time-stretching Detection**: Identifies when pitch/tempo adjustment needed


## File Structure

```
├── stems/                                    # Individual song stem directories
│   ├── 01-01 Zjerm.../
│   │   ├── bass.wav
│   │   ├── drums.wav
│   │   ├── vocals.wav
│   │   ├── piano.wav
│   │   └── other.wav
│   └── ...
├── song-structures/                          # Song metadata and structure (songs)
│   ├── 01-01 ....json                 # BPM, beats, segments
│   ├── 01-11  ....json    
│   └── ...
├── 🧠 stem_mixer_smart.py                  # ✅ SMART LOADING REAL-TIME MIXER
├── 🐍 audio_server.py                      # ✅ PYTHON AUDIO ENGINE
├── 🚀 start_python_mixer.sh                # ✅ ONE-CLICK PYTHON MIXER LAUNCHER
├── 📋 config_loader.py                     # Configuration management
├── 🔧 mixer_config.json                    # Mixer settings

```

**IMPORTANT NOTE:** for a reliable stems separation use demucs/spleeter and for song structure [allinone](https://github.com/hordiales/all-in-one) (which also does stems split using demucs)

## Usage

### 🎛️ **Real-Time Smart Mixer (Recommended)**

**🚀 One-Click Python Mixer (Easiest):**
```bash
./start_python_mixer.sh
```
*Automatically starts both Python audio server and stem mixer*

**Live Mixing Commands:**
```bash
🎛️🧠 > songs                    # List available songs
🎛️🧠 > a.bass 2                # Load bass from song 2 to deck A
🎛️🧠 > b.vocals.chorus 5       # Load vocals from chorus of song 5 to deck B
🎛️🧠 > bpm 128                 # Set BPM to 128
🎛️🧠 > cross 0.5               # 50/50 crossfade between decks
🎛️🧠 > bass 0.8                # Set bass volume to 80%
🎛️🧠 > random                  # Generate random creative mix
```

## Technical Details

### Song Structure Format
```json
{
  "bpm": 140,
  "beats": [0.82, 1.24, 1.7, ...],
  "downbeats": [1.7, 3.44, 5.19, ...],
  "segments": [
    {"start": 0.82, "end": 15.62, "label": "intro"},
    {"start": 15.62, "end": 29.53, "label": "verse"},
    ...
  ]
}
```

### Remix Plan Output
```json
{
  "theme": "energetic",
  "base_song": "Hallucination",
  "base_bpm": 140,
  "base_key": "D",
  "structure": ["intro", "verse", "chorus", ...],
  "sections": {
    "00_intro": {
      "stems": {
        "bass": {"song": "...", "bpm": 143, "pitch_shift": 0.98}
      }
    }
  }
}
```

## Advanced Features

### 🧠 **Smart Loading System**
- **Memory Efficient**: Only loads stems when actually playing
- **Automatic Cleanup**: Frees unused buffers automatically
- **Buffer Management**: Smart allocation and deallocation

### 🎛️ **Real-Time Audio Engine**
- **High-Quality**: 44.1kHz native, no resampling degradation  
- **Low Latency**: 256-sample blocks for responsive control
- **Individual Control**: Each stem controllable independently
- **Section Playback**: Jump to specific song sections (verse, chorus, etc.)

### 🎵 **Musical Intelligence**
- **BPM Sync**: Automatic tempo matching across stems
- **Key Detection**: Eurovision-specific key mapping
- **Structure Analysis**: Understands song sections and timing
- **Harmonic Mixing**: Camelot Wheel compatibility

### 📡 **OSC Integration**
- **External Control**: Full OSC message support
- **Real-Time**: Instant parameter changes
- **Automation Ready**: Perfect for live performance
- **Protocol Documentation**: Complete OSC reference available

## Requirements

** Python Audio Engine (Recommended)**
- **Python 3.7+** with dependencies:
  - `pythonosc` - OSC communication
  - `soundfile` - Audio file reading
  - `pyaudio` - Real-time audio playback
  - `numpy` - Audio processing

**Common Requirements:**
- **Audio Files**: WAV format, 44.1kHz stereo preferred
- **Memory**: 16GB+ RAM recommended
- **Song Structures**: JSON metadata files

### 📦 **Installation**

**Python Audio Engine Setup (Recommended)**
```bash
# Install Python dependencies:
pip install python-osc soundfile pyaudio numpy
```
