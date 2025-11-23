# Docker Configuration for Ubuntu 16.04 (AMD64)

## Overview
This Dockerfile is configured to run on Ubuntu 16.04 (Xenial) with AMD64 architecture, which has specific limitations due to its age (EOL: April 2021).

## Key Changes from Modern Setup

### Base Image
- **Changed from**: `python:3.11-slim`
- **Changed to**: `ubuntu:16.04`
- **Reason**: Need direct control over system libraries and Python version

### Python Version
- **Using**: Python 3.8 (via deadsnakes PPA)
- **Reason**:
  - Python 3.11 requires glibc 2.28+ (Ubuntu 16.04 has glibc 2.23)
  - Python 3.8 is the highest stable version compatible with Ubuntu 16.04
  - Python 3.5 (default) is too old for modern ML libraries

### System Dependencies
Ubuntu 16.04 specific packages:
```
libavcodec-ffmpeg56      # FFmpeg codec library (older version)
libavformat-ffmpeg56     # FFmpeg format library
libswscale-ffmpeg3       # FFmpeg scaling library
libgtk2.0-0              # GTK2 for OpenCV GUI support
libatlas-base-dev        # BLAS library for NumPy
```

### Python Package Versions (Downgraded)

| Package | Modern | Ubuntu 16.04 | Reason |
|---------|--------|--------------|--------|
| ultralytics | 8.0.0+ | 8.0.196 | Compatibility with older PyTorch |
| opencv-python-headless | 4.8.0+ | 4.5.5.64 | Last version supporting glibc 2.23 |
| numpy | 1.24.0+ | 1.21.6 | Last version for Python 3.8 with old glibc |
| fastapi | 0.110+ | 0.95.2 | Stable version for older systems |
| uvicorn | 0.23+ | 0.22.0 | Compatible with FastAPI 0.95 |
| flask | 3.0.0 | 2.3.3 | Werkzeug compatibility |
| flask-socketio | 5.3.5 | 5.3.0 | Stable for older eventlet |
| python-socketio | 5.10.0 | 5.9.0 | Compatibility with older systems |

### PyTorch
- **Version**: 1.13.1 (CPU-only)
- **Reason**:
  - Ultralytics 8.0.196 requires PyTorch 1.13+
  - Using CPU version to reduce image size
  - Last version with pre-built wheels for older glibc

## Limitations

### Known Issues
1. **No GPU support**: CUDA libraries for Ubuntu 16.04 are deprecated
2. **Older OpenCV**: Missing some newer CV algorithms (4.5 vs 4.8)
3. **Memory**: NumPy 1.21 has less optimized memory handling
4. **Security**: Ubuntu 16.04 is EOL and receives no security updates

### Compatibility Notes
- **YOLO Models**: Works with YOLOv8 models but may be slower
- **Video Input**: WebRTC and modern codecs may have issues
- **WebSocket**: Full compatibility maintained
- **OSC Protocol**: Full compatibility (protocol-based, not library-dependent)

## Building the Image

```bash
# Build for AMD64
docker build --platform linux/amd64 -t crowdstream-ubuntu16:latest .

# Or use docker-compose
docker-compose build --build-arg BUILDPLATFORM=linux/amd64
```

## Testing Locally (on macOS/Modern Linux)

```bash
# Build and run with platform emulation
docker buildx build --platform linux/amd64 -t crowdstream-ubuntu16 .
docker run --platform linux/amd64 -p 8082:8082 -p 8091:8091 crowdstream-ubuntu16
```

## Deployment on Ubuntu 16.04 Server

```bash
# On the target Ubuntu 16.04 machine
docker-compose up -d

# View logs
docker-compose logs -f

# Access services
curl http://localhost:8082  # Dashboard
curl http://localhost:8091  # Cosmic Journey
```

## Troubleshooting

### If build fails on pip install:
```dockerfile
# Add before pip install:
RUN python3.8 -m pip install --upgrade pip==23.0.1
```

### If OpenCV fails to load:
```bash
# Check missing libraries
docker run crowdstream-ubuntu16 ldd /usr/local/lib/python3.8/site-packages/cv2/*.so
```

### If YOLO model download fails:
```bash
# Pre-download models and COPY into image
RUN mkdir -p /root/.cache/ultralytics
COPY yolov8n-pose.pt /root/.cache/ultralytics/
```

## Migration Path to Modern System

When ready to upgrade from Ubuntu 16.04:

1. **Ubuntu 18.04**: Can use Python 3.9, newer packages
2. **Ubuntu 20.04**: Can use Python 3.10, full compatibility
3. **Ubuntu 22.04+**: Can use original Dockerfile with Python 3.11

## Security Warning

⚠️ **Ubuntu 16.04 reached End of Life in April 2021**

- No security updates available
- Should only be used in isolated/trusted networks
- Consider Extended Security Maintenance (ESM) if needed
- Plan migration to Ubuntu 20.04 LTS or 22.04 LTS

## Performance Expectations

Compared to modern setup:
- **Startup time**: +20-30% (older libraries)
- **Inference speed**: -15-25% (older PyTorch/OpenCV)
- **Memory usage**: Similar or slightly higher
- **Stability**: Good for long-running services
