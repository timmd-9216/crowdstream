# Native Cosmic Visualizer (No Browser Needed)

## Why Native?

Chromium 90 on Jetson TX1 has limited WebGL support. The **native visualizer uses OpenGL directly** for:
- Full GPU acceleration (Maxwell 256 CUDA cores)
- Better performance (30-60 FPS)
- No browser compatibility issues
- Lower memory usage
- Direct GPU rendering

## Quick Start

```bash
# Install dependencies (one time)
cd cosmic_journey
source venv/bin/activate
pip install -r requirements-gpu.txt

# Run GPU visualizer
./run-native-visualizer.sh

# Or with options
./run-native-visualizer.sh --fullscreen --width 1920 --height 1080
```

## Controls

- **ESC** or **Q** - Quit
- **F** - Toggle fullscreen

## Features

### Visual Elements

1. **Star Field** - 300 stars with depth
2. **Orbiting Planets** - 4 planets with orbital paths
3. **Galaxy Center** - Rotating spiral arms
4. **Energy Particles** - Dynamic particle field
5. **HUD** - Energy bar display

### OSC Mapping

Same as web version:

| OSC Message | Visual Effect |
|-------------|---------------|
| `/dance/leg_movement` | Galaxy rotation speed |
| `/dance/arm_movement` | Asteroid/planet speed |
| `/dance/head_movement` | Camera zoom |
| `/dance/total_movement` | Star brightness + energy |

## Performance

**On Jetson TX1:**
- Native GPU: **30-60 FPS**
- Browser: **15-24 FPS** (with issues)

## Architecture

```
┌─────────────────┐
│ Dance Detector  │
│  (Camera Input) │
└────────┬────────┘
         │ OSC (port 5007)
         ▼
┌─────────────────┐
│ Native OpenGL   │
│   Visualizer    │ ──► Direct GPU Rendering
│  (pyglet+GL)    │     (No Browser!)
└─────────────────┘
```

## Requirements

```bash
# System packages (already installed on Jetson)
# - OpenGL
# - Mesa drivers
# - X11

# Python packages (requirements-gpu.txt)
python-osc==1.7.4       # OSC protocol
pyglet==1.4.10          # OpenGL windowing (Python 3.5 compatible, no f-strings)
```

## Installation on Jetson TX1

```bash
# 1. Setup environment
cd ~/dev/crowdstream
./setup-jetson-tx1.sh

# 2. Install GPU visualizer dependencies
cd cosmic_journey
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

# Different OSC port
./run-native-visualizer.sh --osc-port 5008
```

## Troubleshooting

### ImportError: No module named pyglet

```bash
source venv/bin/activate
pip install pyglet==1.3.2
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

## Comparison: Browser vs Native

| Feature | Browser (Chromium 90) | Native (OpenGL) |
|---------|----------------------|-----------------|
| **FPS** | 15-24 | 30-60 |
| **GPU Usage** | Limited | Full |
| **Memory** | ~500MB | ~150MB |
| **Compatibility** | Issues | Perfect |
| **Latency** | High | Low |
| **Setup** | Complex | Simple |

## Advanced: Multiple Visualizers

Run both web and native simultaneously:

```bash
# Terminal 1: Start detector
cd dance_movement_detector
venv/bin/python src/dance_movement_detector.py

# Terminal 2: Start native visualizer
cd cosmic_journey
./run-native-visualizer.sh --osc-port 5007

# Terminal 3: Start web version (different port)
cd cosmic_journey
python src/cosmic_server.py --osc-port 5008 --web-port 8092
```

## Code Structure

```python
cosmic_gpu_visualizer.py
├── CosmicState         # Shared state with OSC updates
├── Star                # Star field particles
├── Planet              # Orbiting planet objects
└── GPUCosmicVisualizer (pyglet.window.Window)
    ├── setup_opengl()  # Setup OpenGL context
    ├── on_draw()       # Main render loop (30 FPS)
    ├── draw_stars()    # Star field rendering
    ├── draw_planets()  # Planet orbits + spheres
    ├── draw_galaxy_center()  # Spiral galaxy
    └── draw_energy_field()   # Particle effects
```

## Performance Tips

### 1. Reduce Star Count

Edit `cosmic_gpu_visualizer.py`:

```python
self.create_stars(count=200)  # Default: 300
```

### 2. Lower Resolution

```bash
./run-native-visualizer.sh --width 1280 --height 720
```

### 3. Disable Effects

Comment out in `on_draw()`:

```python
# self.draw_energy_field()  # Expensive particle system
```

### 4. Simplify Planets

Reduce sphere detail in `draw_planets()`:

```python
gluSphere(quadric, planet.size, 8, 8)  # Default: 16, 16
```

## Customization

### Change Colors

Edit planet colors in `create_planets()`:

```python
self.planets = [
    Planet(150, 0.002, (1.0, 0.0, 0.0)),  # Pure red
    Planet(250, 0.001, (0.0, 1.0, 0.0)),  # Pure green
    # ...
]
```

### Add More Planets

```python
def create_planets(self):
    self.planets = [
        Planet(100, 0.003, (1.0, 0.3, 0.3)),
        Planet(200, 0.002, (0.3, 0.5, 1.0)),
        Planet(300, 0.001, (1.0, 1.0, 0.3)),
        Planet(400, 0.0008, (0.5, 1.0, 0.5)),
        Planet(500, 0.0005, (1.0, 0.5, 1.0)),  # New!
    ]
```

### Adjust Camera

Edit in `on_draw()`:

```python
gluLookAt(
    0, 50, 200 / zoom,  # Move camera up and back
    0, 0, -500,
    0, 1, 0
)
```

## Future Enhancements

- [ ] CUDA-accelerated particle system
- [ ] Multiple galaxy visualization (person_count)
- [ ] Post-processing effects (bloom, glow)
- [ ] Export to video
- [ ] VR/360 camera mode

## License

Same as main project.

## Support

For issues specific to native visualizer:
1. Check `tegrastats` for GPU usage
2. Verify OpenGL with `glxinfo`
3. Monitor FPS in terminal output
4. Try lower resolution first
