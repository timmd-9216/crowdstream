# Dance Energy Analyzer 🕺💃

Real-time video analysis system that measures dance movement energy from webcam input and controls the CrowdStream audio engine via OSC messages.

## Features

- **Multi-modal Energy Detection:**
  - Frame difference analysis for movement detection
  - Optical flow for motion vector analysis
  - Pose detection for body movement tracking (optional)

- **Real-time Audio Control:**
  - OSC communication with audio engine
  - Dynamic volume adjustment based on energy
  - Crossfade control between audio decks
  - Smooth parameter transitions

- **Visual Feedback:**
  - Live energy visualization bars
  - Real-time parameter display
  - Mirror-effect camera view

## Installation

### Quick Start (Simple Version)
```bash
# Install minimal requirements
pip install opencv-python numpy python-osc

# Run simple analyzer (no ML dependencies)
python dance_energy_simple.py
```

### Full Version with Pose Detection
```bash
# Install all requirements
pip install -r dance_analyzer_requirements.txt

# Run full analyzer
python dance_energy_analyzer.py
```

### One-Click Startup
```bash
# Make executable and run
chmod +x start_dance_analyzer.sh
./start_dance_analyzer.sh
```

## Usage

### Basic Commands
```bash
# Default settings (camera 0, localhost:57120)
python dance_energy_analyzer.py

# Custom camera and OSC settings
python dance_energy_analyzer.py --camera 1 --osc-host 192.168.1.100 --osc-port 57120

# Disable pose detection (faster on older hardware)
python dance_energy_analyzer.py --no-pose

# Simple version (minimal dependencies)
python dance_energy_simple.py
```

### Runtime Controls
- **'q'** - Quit application
- **'space'** - Pause/resume analysis
- **Dance!** - Move your body to control the music

### Prerequisites
1. **Audio Engine Running:**
   ```bash
   cd audio-engine
   python audio_server.py
   # or
   ./start_python_mixer.sh
   ```

2. **Camera Access:** Webcam or external camera connected

3. **Audio Content:** Load stems/tracks in the audio engine before starting

## How It Works

### Energy Detection Algorithm

The system uses multiple computer vision techniques to measure dance energy:

1. **Frame Difference Analysis** (40% weight)
   - Calculates pixel differences between consecutive frames
   - Detects overall movement in the scene
   - Fast and reliable for general motion

2. **Optical Flow Analysis** (30% weight)
   - Tracks feature points between frames
   - Measures motion vectors and velocity
   - Sensitive to directional movement

3. **Pose Movement Analysis** (30% weight, optional)
   - Uses YOLO pose detection to track body keypoints
   - Focuses on key dance movements (arms, legs, head)
   - Weighted by body part importance for dance

### Audio Engine Integration

Energy levels are mapped to audio parameters via OSC:

- **Volume Control:** `0.3 + (energy * 0.7)` range
- **Crossfade:** Linear mapping from energy to deck balance
- **Stem Selection:** High energy triggers different audio elements

### OSC Commands Sent
- `/crossfade_levels [deck_a_level] [deck_b_level]` - Mix between decks
- `/stem_volume [buffer_id] [volume]` - Adjust individual stem volumes
- `/get_status` - Check audio engine connection

## Configuration

### Energy Thresholds
- **Low Energy:** < 0.3 (ambient/calm music)
- **High Energy:** > 0.7 (intense/pumping music)
- **Normal Energy:** 0.3 - 0.7 (regular dance music)

### Performance Tuning
- **Target FPS:** 30fps default (adjustable via --fps)
- **Smoothing:** Exponential moving average with α=0.3
- **Update Rate:** Audio commands limited to 10Hz (100ms intervals)

### Camera Settings
- **Resolution:** 640x480 (optimal for real-time processing)
- **Frame Rate:** 30fps target
- **Mirror Effect:** Enabled for natural interaction

## Troubleshooting

### Common Issues

1. **"Camera access failed"**
   - Check camera permissions in system settings
   - Try different camera ID: `--camera 1` or `--camera 2`
   - Ensure no other apps are using the camera

2. **"OSC communication error"**
   - Verify audio engine is running on correct port
   - Check network connectivity for remote OSC hosts
   - Test with: `python -c "from pythonosc import udp_client; udp_client.SimpleUDPClient('localhost', 57120).send_message('/get_status', [])"`

3. **Low FPS / Performance Issues**
   - Use simple version: `python dance_energy_simple.py`
   - Reduce camera resolution in code
   - Disable pose detection: `--no-pose`
   - Close other applications

4. **"ultralytics not available"**
   - Install ML dependencies: `pip install ultralytics torch torchvision`
   - Or use simple version without pose detection

### Performance Optimization

For older hardware or better performance:

1. **Use Simple Version:** `dance_energy_simple.py`
2. **Reduce Resolution:** Edit camera settings in code
3. **Lower FPS:** Use `--fps 15` or `--fps 20`
4. **Disable Pose:** Use `--no-pose` flag

## Integration with Audio Engine

### Workflow
1. Start audio engine: `./start_python_mixer.sh`
2. Load music stems: `a.bass 1`, `b.vocals 2`, etc.
3. Start dance analyzer: `./start_dance_analyzer.sh`
4. Dance to control the mix! 🎵

### Audio Engine Commands
The analyzer automatically sends these commands based on detected energy:

```python
# Crossfade between decks based on energy
osc_client.send_message("/crossfade_levels", [deck_a_level, deck_b_level])

# Adjust volume based on movement intensity
osc_client.send_message("/stem_volume", [buffer_id, volume_level])

# High energy = more deck B, low energy = more deck A
```

## Development

### Architecture
- **Main Class:** `DanceEnergyAnalyzer` - Full featured version
- **Simple Class:** `SimpleDanceEnergyAnalyzer` - Minimal dependencies
- **Energy Metrics:** Dataclass for different energy measurements
- **OSC Integration:** Direct communication with audio engine

### Extending the System
- Add new energy detection methods in `calculate_*_energy()` methods
- Modify audio mapping in `control_audio_engine()`
- Customize visualization in `draw_energy_visualization()`
- Add new OSC commands for additional audio effects

### Reference Implementation
Based on the analysis approach from `0.1-jcc-demo-videos (2).ipynb`:
- Frame difference calculation for movement detection
- Optical flow analysis for motion vectors
- Pose detection for body movement tracking
- Temporal smoothing for stable control signals

## License

Part of the CrowdStream project - experimental music mixing platform for research and educational purposes.