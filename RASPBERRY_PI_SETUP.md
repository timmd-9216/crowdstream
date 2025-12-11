# 🍓 Raspberry Pi 4 Setup & Optimization

Quick guide to get maximum performance on Raspberry Pi 4.

## Quick Start (One Command)

```bash
./optimize-for-rpi.sh
```

This will:
1. Export YOLOv8n to TFLite INT8 (5-10 min)
2. Configure detector to use TFLite
3. Set optimal parameters for RPi4

**Performance boost:** 3-5 FPS → 12-18 FPS (3-4x faster!)

## Performance Comparison

| Configuration | FPS | Latency | CPU Usage |
|---------------|-----|---------|-----------|
| Default (PyTorch .pt) | 3-5 | 2-3s | ~95% |
| Optimized (TFLite INT8) | 12-18 | <1s | ~70% |
| +Frame Skip (every 2nd) | 20-25 | <1s | ~50% |

## See Full Documentation

- [OPTIMIZATION_GUIDE.md](OPTIMIZATION_GUIDE.md) - Complete optimization guide
- [cosmic_skeleton_standalone/README.md](cosmic_skeleton_standalone/README.md) - Standalone visualizer

