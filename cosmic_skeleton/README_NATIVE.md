# Native Cosmic Skeleton Visualizer (No Browser Needed)

## Why Native?

Chromium 90 on Jetson TX1 has limited WebGL support. The **native visualizer uses OpenGL directly** with space-themed effects for:
- Full GPU acceleration (Maxwell 256 CUDA cores)
- Better performance (30-60 FPS)
- No browser compatibility issues
- Lower memory usage
- Direct GPU rendering with cosmic effects

## Quick Start

```bash
# Install dependencies (one time)
cd cosmic_skeleton
source venv/bin/activate
pip install -r requirements-gpu.txt

# Run cosmic GPU visualizer
./run-native-visualizer.sh

# Or with options
./run-native-visualizer.sh --fullscreen --width 1920 --height 1080
```

## Controls

- **ESC** or **Q** - Quit
- **F** - Toggle fullscreen

## Features

### Cosmic Visual Elements

1. **Twinkling Starfield** - 200 animated stars with brightness variation
2. **Pulsating Nebula** - Dynamic purple nebula clouds in the background
3. **Orbiting Planets** - 4 colorful planets with glowing auras
4. **Glowing Skeletons** - 17 YOLO keypoints with cosmic glow effects
5. **Color-coded Body Parts** (Cosmic Theme):
   - Purple: Head (nose, eyes, ears)
   - Cyan: Torso (shoulders, hips)
   - Gold: Arms (elbows, wrists)
   - Green: Legs (knees, ankles)
6. **Multi-person Support** - Multiple cosmic skeletons simultaneously
7. **Real-time HUD** - FPS, pose count, OSC port info

### Cosmic Effects

- **Dynamic Glow** - Synchronized pulsating glow on skeletons
- **Star Twinkling** - Each star has unique twinkle speed
- **Nebula Pulsation** - Background nebula breathes with the rhythm
- **Planet Orbits** - Smooth orbital motion around screen center
- **Planet Halos** - Glowing auras around each planet

### OSC Mapping

Same as web version:

| OSC Message | Data Format |
|-------------|-------------|
| `/pose/keypoints` | `[person_id, x0, y0, conf0, ..., x16, y16, conf16]` |

**YOLO Keypoint Order (17 keypoints):**
```
0: nose
1-2: eyes (left, right)
3-4: ears (left, right)
5-6: shoulders (left, right)
7-8: elbows (left, right)
9-10: wrists (left, right)
11-12: hips (left, right)
13-14: knees (left, right)
15-16: ankles (left, right)
```

## Performance

**On Jetson TX1:**
- Native Cosmic GPU: **30-60 FPS**
- Browser: **15-24 FPS** (with WebGL issues)

## Architecture

```
┌─────────────────┐
│ Dance Detector  │
│  (Camera Input) │
└────────┬────────┘
         │ OSC (port 5008)
         ▼
┌─────────────────────────┐
│ Cosmic Native OpenGL    │
│   Visualizer            │ ──► Direct GPU Rendering
│  (pyglet+GL+Effects)    │     (Space Theme!)
└─────────────────────────┘
```

## Requirements

```bash
# System packages (already installed on Jetson)
# - OpenGL
# - Mesa drivers
# - X11

# Python packages (requirements-gpu.txt)
python-osc==1.7.4       # OSC protocol
pyglet==1.4.10          # OpenGL windowing (Python 3.5 compatible)
```

## Installation on Jetson TX1

```bash
# 1. Setup environment
cd ~/dev/crowdstream
./setup-jetson-tx1.sh

# 2. Install cosmic GPU visualizer dependencies
cd cosmic_skeleton
source venv/bin/activate
pip install -r requirements-gpu.txt

# 3. Run
./run-native-visualizer.sh
```

## Command Line Options

```bash
# Fullscreen mode
./run-native-visualizer.sh --fullscreen

# Custom resolution
./run-native-visualizer.sh --width 1920 --height 1080

# Different OSC port (default: 5008)
./run-native-visualizer.sh --osc-port 5009
```

## Troubleshooting

### ImportError: No module named pyglet

```bash
source venv/bin/activate
pip install pyglet==1.4.10
```

### OpenGL error

```bash
# Check OpenGL support
glxinfo | grep "OpenGL version"

# Should show: OpenGL version string: 4.5.0 (or 3.3+)
```

### Black screen

```bash
# Check display
echo $DISPLAY  # Should show :0 or :1

# Set if needed
export DISPLAY=:0
```

### Low FPS

```bash
# Enable max performance
sudo nvpmodel -m 0
sudo jetson_clocks

# Monitor GPU usage
tegrastats
```

## Comparison: Browser vs Native Cosmic

| Feature | Browser (Chromium 90) | Native Cosmic (OpenGL) |
|---------|----------------------|------------------------|
| **FPS** | 15-24 | 30-60 |
| **GPU Usage** | Limited | Full |
| **Memory** | ~600MB | ~180MB |
| **Effects** | Limited | All |
| **Compatibility** | Issues | Perfect |
| **Latency** | High | Low |

## Code Structure

```python
cosmic_gpu_visualizer.py
├── Star                    # Twinkling star particle
├── Planet                  # Orbiting planet decoration
├── PoseData                # Pose data container
├── SkeletonState           # Shared state with OSC
└── CosmicGPUVisualizer (pyglet.window.Window)
    ├── setup_opengl()      # Setup OpenGL context
    ├── create_stars()      # Generate starfield
    ├── create_planets()    # Generate orbiting planets
    ├── start_osc_server()  # Start OSC listener
    ├── update()            # Update logic (30 FPS)
    ├── on_draw()           # Main render loop
    ├── draw_nebula()       # Draw pulsating nebula
    ├── draw_stars()        # Draw twinkling stars
    ├── draw_planets()      # Draw orbiting planets
    ├── draw_cosmic_skeleton() # Draw glowing skeleton
    └── draw_hud()          # Draw stats overlay
```

## Performance Tips

### 1. Reduce Star Count

Edit `cosmic_gpu_visualizer.py`:

```python
for i in range(100):  # Default: 200
```

### 2. Fewer Planets

Edit `create_planets()`:

```python
# Comment out planets you don't want
# self.planets.append(Planet(450, 0.0005, 18, COSMIC_COLORS['green']))
```

### 3. Disable Nebula

Comment out in `on_draw()`:

```python
# self.draw_nebula()  # Expensive gradient effect
```

### 4. Lower Resolution

```bash
./run-native-visualizer.sh --width 1280 --height 720
```

## Customization

### Change Cosmic Colors

Edit color scheme in `cosmic_gpu_visualizer.py`:

```python
COSMIC_COLORS = {
    'purple': (1.0, 0.0, 1.0, 1.0),  # Magenta
    'cyan': (0.0, 1.0, 1.0, 1.0),    # Bright cyan
    'gold': (1.0, 0.84, 0.0, 1.0),   # Keep gold
    'green': (0.0, 1.0, 0.0, 1.0)    # Bright green
}
```

### Adjust Planet Orbits

Edit in `create_planets()`:

```python
# Larger orbits
Planet(200, 0.002, 15, COSMIC_COLORS['purple']),  # closer, faster
Planet(400, 0.001, 20, COSMIC_COLORS['cyan']),    # farther, slower
```

### Change Glow Speed

Edit in `update()`:

```python
self.glow_phase += dt * 4.0  # Default: 2.0 (faster pulsing)
```

### Adjust Nebula Intensity

Edit in `draw_nebula()`:

```python
glow = 0.5 + 0.3 * math.sin(self.nebula_phase)  # Stronger glow
```

## Cosmic Journey vs Cosmic Skeleton

Both use the same cosmic theme but different visualizations:

| Feature | Cosmic Journey | Cosmic Skeleton |
|---------|----------------|-----------------|
| **Input** | OSC movement data | OSC pose keypoints |
| **Output** | Abstract space scene | Skeleton display |
| **Effects** | Planets, galaxy, meteors | Starfield, nebula, planets |
| **Port** | 5007 | 5008 |
| **Use Case** | Dance energy visualization | Pose tracking visualization |

## License

Same as main project.
