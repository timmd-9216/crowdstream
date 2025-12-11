# 🎥 Video Skeleton Visualizer

Real-time YOLO pose detection from video files with space-themed visual effects!

## ✨ Features

- 🎬 Process any video file with YOLO pose detection
- 🌟 Animated starfield background
- 🌌 Pulsating nebula clouds
- ⚡ Glowing energy-beam skeletons
- 💫 Dynamic particle effects
- 🎨 Cosmic color scheme (purple, cyan, gold, green)
- 🌠 Synchronized glow animations
- 🔄 Automatic video looping

## 🚀 Quick Start

### Installation

```bash
cd video_skeleton_visualizer
chmod +x install.sh
./install.sh
```

### Running with a video file

```bash
# Method 1: Using the start script
./start_video_skeleton.sh /path/to/your/video.mp4

# Method 2: Direct invocation
source venv/bin/activate
python src/server.py --video /path/to/your/video.mp4
```

Access the visualizer at: http://localhost:8094

## 🔌 Configuration

- **Web Port**: 8094 (default, configurable with `--port`)
- **Video Input**: Any video file supported by OpenCV (MP4, AVI, MOV, etc.)
- **YOLO Model**: yolo11n-pose.pt (default, configurable with `--model`)

## 📖 Command Line Options

```bash
python src/server.py --help

Options:
  --host HOST        Host to bind to (default: 0.0.0.0)
  --port PORT        Web server port (default: 8094)
  --video VIDEO      Path to video file (required)
  --model MODEL      YOLO model to use (default: yolo11n-pose.pt)
```

## 🎯 Example

```bash
# Process a dance video with the default YOLO model
python src/server.py --video /path/to/dance.mp4

# Use a different port and YOLO model
python src/server.py --video /path/to/dance.mp4 --port 9000 --model yolo11m-pose.pt
```

## 🔄 How It Works

1. The server loads your video file
2. YOLO pose detection processes each frame in real-time
3. Detected poses are streamed via WebSocket to the browser
4. The cosmic visualizer renders the skeletons with stunning effects
5. Video automatically loops when it reaches the end

## 🎨 Technical Details

- **Backend**: FastAPI + Ultralytics YOLO
- **Video Processing**: OpenCV
- **Frontend**: HTML5 Canvas + WebSocket
- **Pose Model**: YOLO v11 (17 keypoints)

## 🌌 Enjoy the Cosmic Dance!
