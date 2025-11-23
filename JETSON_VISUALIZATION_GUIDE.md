# Jetson TX1 Visualization Guide

## GPU Specifications

**Jetson TX1 (Maxwell Architecture)**
- GPU: NVIDIA Maxwell (256 CUDA cores)
- Memory: 4GB LPDDR4 shared
- OpenGL: 4.5
- OpenGL ES: 3.1
- CUDA: 6.1
- Chromium: 90.0 (old, limited WebGL 2.0 support)

## Recommended Approach

### Option 1: Native OpenGL Application (RECOMMENDED - Maximum Performance)

Use pyglet with OpenGL directly on the GPU:

```bash
cd cosmic_journey
source venv/bin/activate
pip install -r requirements-gpu.txt
./run-native-visualizer.sh
```

**Benefits:**
- Direct GPU access via OpenGL
- 30-60 FPS easily achievable
- Lower latency and better performance
- No browser compatibility issues
- Pre-compiled wheels (no compilation needed)
- Python 3.5.2 compatible

**Implementation:**
- See [cosmic_journey/README_NATIVE.md](cosmic_journey/README_NATIVE.md) for details
- GPU visualizer: [cosmic_journey/src/cosmic_gpu_visualizer.py](cosmic_journey/src/cosmic_gpu_visualizer.py)

### Option 2: GPU-Accelerated Chromium (Fallback)

Launch Chromium with GPU acceleration:

```bash
./launch-chromium-jetson.sh http://localhost:8091
```

Or manually:
```bash
chromium-browser \
  --kiosk \
  --enable-gpu-rasterization \
  --enable-zero-copy \
  --use-gl=egl \
  --ignore-gpu-blacklist \
  --enable-webgl \
  --enable-accelerated-2d-canvas \
  http://localhost:8091
```

**Pros:**
- Uses Maxwell GPU for rendering
- Hardware-accelerated Canvas 2D
- No code changes needed

**Cons:**
- Chromium 90 is old (May 2021)
- WebGL 2.0 limited/broken (planets don't show)
- Security vulnerabilities
- Lower performance than native

### Option 3: Electron/NW.js (Not Recommended)

Electron bundles Chromium but:
- Too heavy for Jetson TX1 (4GB RAM)
- Similar performance to Chromium
- More resource intensive

## Performance Optimization Tips

### 1. Check GPU Acceleration

Open in Chromium:
```
chrome://gpu
```

Look for:
- **Canvas: Hardware accelerated** ✓
- **WebGL: Hardware accelerated** ✓
- **Rasterization: Hardware accelerated** ✓

### 2. Reduce Canvas Resolution

If performance is poor, reduce resolution:

```javascript
// In visualization code
const canvas = document.getElementById('canvas');
const dpr = window.devicePixelRatio || 1;

// Jetson TX1: use lower DPR
canvas.width = window.innerWidth * Math.min(dpr, 1.5);
canvas.height = window.innerHeight * Math.min(dpr, 1.5);
```

### 3. Use RequestAnimationFrame Throttling

```javascript
let lastFrame = 0;
const targetFPS = 30; // Lower FPS for Jetson TX1

function render(timestamp) {
    if (timestamp - lastFrame >= 1000/targetFPS) {
        // Do rendering
        lastFrame = timestamp;
    }
    requestAnimationFrame(render);
}
```

### 4. Optimize WebGL Shaders

For WebGL visualizations:

```javascript
// Use simpler shaders
const vertexShader = `
    attribute vec3 position;
    uniform mat4 mvp;
    void main() {
        gl_Position = mvp * vec4(position, 1.0);
    }
`;

// Avoid expensive operations in fragment shader
const fragmentShader = `
    precision mediump float;
    uniform vec3 color;
    void main() {
        gl_FragColor = vec4(color, 1.0);
    }
`;
```

### 5. Enable CUDA for Custom Processing

If using custom image processing:

```python
import cv2

# Check CUDA availability
print(cv2.cuda.getCudaEnabledDeviceCount())

# Use CUDA-accelerated OpenCV
gpu_frame = cv2.cuda_GpuMat()
gpu_frame.upload(frame)
# ... GPU processing ...
result = gpu_frame.download()
```

## Visualization Library Recommendations

### For Canvas 2D

**Recommended:**
1. **Fabric.js** - Hardware accelerated, good performance
2. **Paper.js** - Vector graphics, smooth animations
3. **PixiJS** - Fast 2D rendering (can use WebGL as fallback)

**Example (PixiJS):**
```javascript
const app = new PIXI.Application({
    width: window.innerWidth,
    height: window.innerHeight,
    backgroundColor: 0x000000,
    resolution: 1, // Lower resolution for Jetson
    antialias: false, // Disable for performance
    powerPreference: 'high-performance'
});
```

### For WebGL

**Recommended:**
1. **Three.js** (r90-r100) - Stable with Chromium 90
2. **Babylon.js** (older version ~4.x)
3. **Raw WebGL** - Best performance

**Example (Three.js):**
```javascript
const renderer = new THREE.WebGLRenderer({
    antialias: false, // Disable for performance
    powerPreference: 'high-performance'
});

// Use simpler materials
const material = new THREE.MeshBasicMaterial({ color: 0x00ff00 });

// Reduce polygon count
const geometry = new THREE.SphereGeometry(1, 16, 16); // Low poly
```

## Current Visualization: Cosmic Journey

**Technology Stack:**
- **Backend**: Flask + Flask-SocketIO (threading mode)
- **Frontend**: HTML5 Canvas + JavaScript
- **Communication**: WebSocket (polling fallback)

**Optimization for Jetson TX1:**

1. **Reduce particle count:**
```javascript
// In cosmic.html
const MAX_PARTICLES = 200; // Instead of 1000
```

2. **Lower canvas resolution:**
```javascript
canvas.width = window.innerWidth * 0.75;
canvas.height = window.innerHeight * 0.75;
```

3. **Simplify rendering:**
```javascript
// Use fillRect instead of complex paths
ctx.fillRect(x, y, size, size); // Faster than arc()
```

## Monitoring GPU Usage

### Check GPU stats in real-time:

```bash
# Jetson stats
tegrastats
```

Look for:
- **GR3D**: GPU utilization percentage
- **EMC**: Memory controller frequency
- **Temp**: Temperature (keep below 80°C)

### Chrome DevTools Performance:

1. Open DevTools (F12)
2. Performance tab
3. Record while visualization runs
4. Look for frame drops

**Target FPS:**
- **30 FPS**: Good for Jetson TX1
- **60 FPS**: Possible with optimizations
- **Below 24 FPS**: Reduce visual complexity

## Native GPU Visualization (Implemented!)

**GPU-accelerated visualizer using pyglet + OpenGL is now available:**

```bash
cd cosmic_journey
./run-native-visualizer.sh
```

**Features:**
- Uses Maxwell GPU directly via OpenGL
- 300 stars, 4 planets, galaxy center, energy particles
- 30-60 FPS on Jetson TX1
- Python 3.5.2 compatible
- No compilation required (pyglet has wheels)
- Same OSC protocol as web version

**See:**
- [cosmic_journey/README_NATIVE.md](cosmic_journey/README_NATIVE.md) - Full documentation
- [cosmic_journey/src/cosmic_gpu_visualizer.py](cosmic_journey/src/cosmic_gpu_visualizer.py) - Source code

## Troubleshooting

### Black screen in browser

```bash
# Check if GPU is available
glxinfo | grep "OpenGL"

# Test WebGL
chromium-browser --enable-webgl-draft-extensions http://webglreport.com
```

### Low FPS

1. Reduce canvas resolution
2. Lower particle/object count
3. Disable shadows/effects
4. Use simpler shaders
5. Target 30 FPS instead of 60

### GPU not used

```bash
# Force GPU rendering
export LIBGL_ALWAYS_SOFTWARE=0
chromium-browser --enable-gpu-rasterization --use-gl=egl
```

### Memory issues

```bash
# Monitor memory
free -h
sudo jetson_clocks # Lock to max performance
```

## Recommended Settings for Cosmic Journey

**Optimal configuration for Jetson TX1:**

```javascript
// In templates/cosmic.html
const CONFIG = {
    stars: 100,           // Reduce from 500
    asteroids: 20,        // Reduce from 50
    planets: 3,           // Reduce from 5
    particles: 150,       // Reduce from 500
    targetFPS: 30,        // Lock to 30 FPS
    resolution: 0.75,     // 75% native resolution
    shadows: false,       // Disable shadows
    antialiasing: false   // Disable AA
};
```

## Summary

**For Jetson TX1:**

**RECOMMENDED: Native OpenGL visualizer**
- Use `./run-native-visualizer.sh` in cosmic_journey/
- Direct GPU rendering via pyglet + OpenGL
- 30-60 FPS, no browser issues
- Python 3.5.2 compatible
- See [cosmic_journey/README_NATIVE.md](cosmic_journey/README_NATIVE.md)

**FALLBACK: Chromium with GPU acceleration**
- Use `./launch-chromium-jetson.sh http://localhost:8091`
- Canvas 2D works, WebGL 2.0 has issues (planets don't show)
- Target 30 FPS
- Reduce visual complexity
- Use `tegrastats` to monitor

**Performance monitoring:**
- `tegrastats` - Check GR3D (GPU usage)
- `glxinfo | grep "OpenGL"` - Verify OpenGL support
- Target 30 FPS for stable performance
