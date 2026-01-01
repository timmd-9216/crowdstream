# Skeleton Visualizer 💃🦴

Real-time visualization of YOLO pose detection keypoints and skeleton connections.

## Features

- **Real-time skeleton display**: Shows body keypoints (joints) connected by lines (bones)
- **Color-coded body parts**:
  - 🔴 Head (nose, eyes, ears)
  - 🔵 Torso (shoulders, hips)
  - 🟡 Arms (elbows, wrists)
  - 🟢 Legs (knees, ankles)
- **Multi-person support**: Can display multiple people simultaneously
- **WebSocket communication**: Real-time updates via WebSocket
- **OSC input**: Receives pose data from YOLO detector via OSC

## Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Start the server

```bash
python src/server.py --host 0.0.0.0 --port 8092 --osc-port 5007
```

### Access the visualizer

Open your browser to: http://localhost:8092

### Options

- `--host`: Host to bind to (default: 0.0.0.0)
- `--port`: Web server port (default: 8092)
- `--osc-port`: OSC port to listen on (default: 5007)

## Integration

The skeleton visualizer receives pose keypoint data from the dance movement detector via OSC messages.

**OSC Message Format:**
```
Address: /pose/keypoints
Data: [person_id, x0, y0, conf0, x1, y1, conf1, ..., x16, y16, conf16]
```

Where:
- `person_id`: Integer identifying the tracked person
- `x, y, conf`: X coordinate, Y coordinate, and confidence for each of 17 YOLO keypoints

**YOLO Keypoint Order:**
```
0: nose
1: left_eye, 2: right_eye
3: left_ear, 4: right_ear
5: left_shoulder, 6: right_shoulder
7: left_elbow, 8: right_elbow
9: left_wrist, 10: right_wrist
11: left_hip, 12: right_hip
13: left_knee, 14: right_knee
15: left_ankle, 16: right_ankle
```

## Architecture

```
dance_movement_detector (YOLO)
    |
    | OSC (/pose/keypoints)
    v
skeleton_visualizer (FastAPI + OSC)
    |
    | WebSocket
    v
Browser (Canvas visualization)
```

## Files

- `src/server.py`: FastAPI server with OSC and WebSocket handling
- `templates/skeleton.html`: Web interface
- `static/js/skeleton.js`: Canvas drawing logic and skeleton connections
- `static/css/skeleton.css`: Styling
- `requirements.txt`: Python dependencies

## Troubleshooting

**No skeletons appearing:**
- Ensure the dance movement detector is running
- Check that OSC port 5007 is not blocked
- Verify detector is configured to send to port 5007

**Connection issues:**
- Check browser console for WebSocket errors
- Ensure port 8092 is not in use by another service
- Try hard refresh (Ctrl+F5 or Cmd+Shift+R)

## Development

The visualizer uses:
- **FastAPI**: Web framework
- **python-osc**: OSC message handling
- **WebSockets**: Real-time browser communication
- **Canvas API**: Skeleton rendering
