#!/usr/bin/env python3
"""
Native GPU-Accelerated Skeleton Visualizer for Jetson TX1
Uses pyglet + OpenGL for hardware-accelerated rendering
Python 3.5.2 compatible (no f-strings, no type hints, no dataclasses)
"""

import argparse
import math
import time
import threading
from collections import deque

import pyglet
from pyglet.gl import *
from pythonosc import dispatcher, osc_server


# YOLO Pose Keypoint indices
KEYPOINT_NAMES = [
    "nose",           # 0
    "left_eye",       # 1
    "right_eye",      # 2
    "left_ear",       # 3
    "right_ear",      # 4
    "left_shoulder",  # 5
    "right_shoulder", # 6
    "left_elbow",     # 7
    "right_elbow",    # 8
    "left_wrist",     # 9
    "right_wrist",    # 10
    "left_hip",       # 11
    "right_hip",      # 12
    "left_knee",      # 13
    "right_knee",     # 14
    "left_ankle",     # 15
    "right_ankle"     # 16
]

# Skeleton connections (bone structure)
SKELETON_CONNECTIONS = [
    # Head
    (0, 1), (0, 2),  # nose to eyes
    (1, 3), (2, 4),  # eyes to ears

    # Torso
    (5, 6),   # shoulders
    (5, 11),  # left shoulder to left hip
    (6, 12),  # right shoulder to right hip
    (11, 12), # hips

    # Arms
    (5, 7), (7, 9),   # left arm
    (6, 8), (8, 10),  # right arm

    # Legs
    (11, 13), (13, 15),  # left leg
    (12, 14), (14, 16)   # right leg
]

# Colors for different body parts (R, G, B, A)
COLORS = {
    'head': (1.0, 0.42, 0.42, 1.0),    # Red
    'torso': (0.31, 0.80, 0.77, 1.0),  # Cyan
    'arms': (1.0, 0.90, 0.43, 1.0),    # Yellow
    'legs': (0.58, 0.88, 0.83, 1.0)    # Light green
}


def get_keypoint_color(kp_idx):
    """Get color for a specific keypoint index"""
    if kp_idx in [0, 1, 2, 3, 4]:
        return COLORS['head']
    elif kp_idx in [5, 6, 11, 12]:
        return COLORS['torso']
    elif kp_idx in [7, 8, 9, 10]:
        return COLORS['arms']
    else:
        return COLORS['legs']


def get_connection_color(conn):
    """Get color for a specific connection"""
    kp1, kp2 = conn
    # Average the colors of the two keypoints
    color1 = get_keypoint_color(kp1)
    color2 = get_keypoint_color(kp2)
    return (
        (color1[0] + color2[0]) / 2.0,
        (color1[1] + color2[1]) / 2.0,
        (color1[2] + color2[2]) / 2.0,
        1.0
    )


class PoseData(object):
    """Single pose detection data"""
    def __init__(self, person_id, keypoints, timestamp):
        self.person_id = person_id
        self.keypoints = keypoints  # List of [x, y, confidence]
        self.timestamp = timestamp


class SkeletonState(object):
    """Holds pose data from OSC"""
    def __init__(self):
        self.poses = {}  # person_id -> PoseData
        self.lock = threading.Lock()
        self.pose_timeout = 1.0  # Remove poses older than 1 second


class GPUSkeletonVisualizer(pyglet.window.Window):
    """GPU-accelerated skeleton visualizer using pyglet + OpenGL"""

    def __init__(self, osc_port=5007, width=1280, height=720, fullscreen=False):
        super(GPUSkeletonVisualizer, self).__init__(
            width=width,
            height=height,
            caption="Skeleton Visualizer - GPU",
            fullscreen=fullscreen,
            vsync=True
        )

        self.osc_port = osc_port
        self.state = SkeletonState()

        # FPS tracking
        self.fps_time = time.time()
        self.fps_frames = 0
        self.fps = 0.0

        # Setup OpenGL
        self.setup_opengl()

        # Start OSC server
        self.start_osc_server()

        # Schedule update at 30 FPS
        pyglet.clock.schedule_interval(self.update, 1.0/30.0)

        print("=== GPU Skeleton Visualizer ===")
        print("OSC Port: {}".format(self.osc_port))
        print("Resolution: {}x{}".format(width, height))
        print("Fullscreen: {}".format(fullscreen))
        print("")
        print("Waiting for pose data on /pose/keypoints...")
        print("Press ESC or Q to quit")
        print("")

    def setup_opengl(self):
        """Configure OpenGL for 2D rendering"""
        glClearColor(0.05, 0.05, 0.10, 1.0)  # Dark blue background

        # Enable blending for transparency
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Enable line smoothing
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

        # Enable point smoothing
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)

    def start_osc_server(self):
        """Start OSC server in background thread"""
        osc_dispatcher = dispatcher.Dispatcher()
        osc_dispatcher.map("/pose/keypoints", self.handle_pose_keypoints)

        try:
            self.osc_server = osc_server.ThreadingOSCUDPServer(
                ("0.0.0.0", self.osc_port),
                osc_dispatcher
            )
        except OSError as e:
            print("ERROR: Could not open OSC port {}: {}".format(self.osc_port, e))
            raise

        server_thread = threading.Thread(target=self.osc_server.serve_forever, daemon=True)
        server_thread.start()
        print("[OK] OSC server started on port {}".format(self.osc_port))

    def handle_pose_keypoints(self, address, *args):
        """Handle incoming pose keypoints from OSC
        Expected format: person_id x0 y0 conf0 x1 y1 conf1 ... x16 y16 conf16
        Total: 1 + (17 * 3) = 52 values
        """
        if len(args) < 52:
            return

        person_id = int(args[0])
        keypoints = []

        # Parse keypoints (x, y, confidence)
        for i in range(1, len(args), 3):
            if i + 2 < len(args):
                x = float(args[i])
                y = float(args[i + 1])
                conf = float(args[i + 2])
                keypoints.append([x, y, conf])

        # Store pose data
        with self.state.lock:
            self.state.poses[person_id] = PoseData(
                person_id=person_id,
                keypoints=keypoints,
                timestamp=time.time()
            )

    def update(self, dt):
        """Update logic (called at 30 FPS)"""
        # Remove stale poses
        current_time = time.time()
        with self.state.lock:
            stale_ids = [
                pid for pid, pose in self.state.poses.items()
                if current_time - pose.timestamp > self.state.pose_timeout
            ]
            for pid in stale_ids:
                del self.state.poses[pid]

        # Update FPS
        self.fps_frames += 1
        if current_time - self.fps_time >= 1.0:
            self.fps = self.fps_frames / (current_time - self.fps_time)
            self.fps_frames = 0
            self.fps_time = current_time

    def on_draw(self):
        """Render the scene"""
        self.clear()

        # Setup 2D orthographic projection
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)  # Top-left origin

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # Get poses snapshot
        with self.state.lock:
            poses = list(self.state.poses.values())

        # Draw each pose
        for pose in poses:
            self.draw_pose(pose)

        # Draw HUD
        self.draw_hud(len(poses))

    def draw_pose(self, pose):
        """Draw a single pose (skeleton)"""
        keypoints = pose.keypoints

        # Draw connections (bones)
        glLineWidth(3.0)
        glBegin(GL_LINES)

        for conn in SKELETON_CONNECTIONS:
            kp1_idx, kp2_idx = conn

            if kp1_idx >= len(keypoints) or kp2_idx >= len(keypoints):
                continue

            kp1 = keypoints[kp1_idx]
            kp2 = keypoints[kp2_idx]

            # Only draw if both keypoints are confident
            if kp1[2] > 0.5 and kp2[2] > 0.5:
                color = get_connection_color(conn)
                glColor4f(color[0], color[1], color[2], color[3])

                # Convert normalized coords (0-1) to screen coords
                x1 = kp1[0] * self.width
                y1 = kp1[1] * self.height
                x2 = kp2[0] * self.width
                y2 = kp2[1] * self.height

                glVertex2f(x1, y1)
                glVertex2f(x2, y2)

        glEnd()

        # Draw keypoints (joints)
        glPointSize(8.0)
        glBegin(GL_POINTS)

        for i, kp in enumerate(keypoints):
            if kp[2] > 0.5:  # confidence threshold
                color = get_keypoint_color(i)
                glColor4f(color[0], color[1], color[2], color[3])

                x = kp[0] * self.width
                y = kp[1] * self.height

                glVertex2f(x, y)

        glEnd()

    def draw_hud(self, pose_count):
        """Draw HUD with stats"""
        # Draw semi-transparent background
        glColor4f(0.0, 0.0, 0.0, 0.5)
        glBegin(GL_QUADS)
        glVertex2f(10, 10)
        glVertex2f(250, 10)
        glVertex2f(250, 80)
        glVertex2f(10, 80)
        glEnd()

        # Draw text (simple labels)
        info_lines = [
            "FPS: {:.1f}".format(self.fps),
            "Poses: {}".format(pose_count),
            "Port: {}".format(self.osc_port)
        ]

        # Create labels
        y_offset = 20
        for line in info_lines:
            label = pyglet.text.Label(
                line,
                font_name='Courier New',
                font_size=12,
                x=20, y=y_offset,
                color=(255, 255, 255, 255)
            )
            label.draw()
            y_offset += 20

    def on_key_press(self, symbol, modifiers):
        """Handle keyboard input"""
        if symbol == pyglet.window.key.ESCAPE or symbol == pyglet.window.key.Q:
            print("\nShutting down...")
            self.osc_server.shutdown()
            pyglet.app.exit()
        elif symbol == pyglet.window.key.F:
            # Toggle fullscreen
            self.set_fullscreen(not self.fullscreen)


def main():
    parser = argparse.ArgumentParser(
        description="GPU-accelerated skeleton visualizer for Jetson TX1"
    )
    parser.add_argument(
        "--osc-port",
        type=int,
        default=5007,
        help="OSC port to listen on (default: 5007)"
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1280,
        help="Window width (default: 1280)"
    )
    parser.add_argument(
        "--height",
        type=int,
        default=720,
        help="Window height (default: 720)"
    )
    parser.add_argument(
        "--fullscreen",
        action="store_true",
        help="Run in fullscreen mode"
    )

    args = parser.parse_args()

    try:
        visualizer = GPUSkeletonVisualizer(
            osc_port=args.osc_port,
            width=args.width,
            height=args.height,
            fullscreen=args.fullscreen
        )
        pyglet.app.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print("ERROR: {}".format(e))
        raise


if __name__ == "__main__":
    main()
