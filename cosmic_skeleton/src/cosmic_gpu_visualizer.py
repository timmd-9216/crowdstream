#!/usr/bin/env python3
"""
Native GPU-Accelerated Cosmic Skeleton Visualizer for Jetson TX1
Space-themed YOLO pose visualization with stars, planets, and nebula effects
Uses pyglet + OpenGL for hardware-accelerated rendering
Python 3.5.2 compatible (no f-strings, no type hints, no dataclasses)
"""

import argparse
import math
import time
import random
import threading

import pyglet
from pyglet.gl import *
from pythonosc import dispatcher, osc_server


# YOLO Pose Keypoint indices (17 keypoints)
SKELETON_CONNECTIONS = [
    # Head
    (0, 1), (0, 2), (1, 3), (2, 4),
    # Torso
    (5, 6), (5, 11), (6, 12), (11, 12),
    # Arms
    (5, 7), (7, 9), (6, 8), (8, 10),
    # Legs
    (11, 13), (13, 15), (12, 14), (14, 16)
]

# Cosmic colors (R, G, B, A)
COSMIC_COLORS = {
    'purple': (0.63, 0.13, 0.94, 1.0),  # a020f0
    'cyan': (0.0, 0.83, 1.0, 1.0),      # 00d4ff
    'gold': (1.0, 0.84, 0.0, 1.0),      # ffd700
    'green': (0.0, 1.0, 0.53, 1.0)      # 00ff88
}


def get_keypoint_color(kp_idx):
    """Get cosmic color for keypoint"""
    if kp_idx in [0, 1, 2, 3, 4]:
        return COSMIC_COLORS['purple']
    elif kp_idx in [5, 6, 11, 12]:
        return COSMIC_COLORS['cyan']
    elif kp_idx in [7, 8, 9, 10]:
        return COSMIC_COLORS['gold']
    else:
        return COSMIC_COLORS['green']


class Star(object):
    """Background star particle"""
    def __init__(self, x, y, size, brightness):
        self.x = x
        self.y = y
        self.size = size
        self.brightness = brightness
        self.twinkle_phase = random.random() * math.pi * 2
        self.twinkle_speed = random.uniform(1.0, 3.0)


class Planet(object):
    """Orbiting planet decoration"""
    def __init__(self, distance, speed, size, color):
        self.distance = distance
        self.speed = speed
        self.size = size
        self.color = color
        self.angle = random.random() * math.pi * 2


class PoseData(object):
    """Single pose detection data"""
    def __init__(self, person_id, keypoints, timestamp):
        self.person_id = person_id
        self.keypoints = keypoints
        self.timestamp = timestamp


class SkeletonState(object):
    """Holds pose data from OSC"""
    def __init__(self):
        self.poses = {}
        self.lock = threading.Lock()
        self.pose_timeout = 1.0


class CosmicGPUVisualizer(pyglet.window.Window):
    """GPU-accelerated cosmic skeleton visualizer"""

    def __init__(self, osc_port=5008, width=1280, height=720, fullscreen=False):
        super(CosmicGPUVisualizer, self).__init__(
            width=width,
            height=height,
            caption="Cosmic Skeleton Visualizer - GPU",
            fullscreen=fullscreen,
            vsync=True
        )

        self.osc_port = osc_port
        self.state = SkeletonState()

        # FPS tracking
        self.fps_time = time.time()
        self.fps_frames = 0
        self.fps = 0.0

        # Cosmic effects
        self.stars = []
        self.planets = []
        self.glow_phase = 0.0
        self.nebula_phase = 0.0

        # Setup
        self.setup_opengl()
        self.create_stars()
        self.create_planets()
        self.start_osc_server()

        # Schedule updates
        pyglet.clock.schedule_interval(self.update, 1.0/30.0)

        print("=== Cosmic Skeleton Visualizer ===")
        print("OSC Port: {}".format(self.osc_port))
        print("Resolution: {}x{}".format(width, height))
        print("Fullscreen: {}".format(fullscreen))
        print("")
        print("Waiting for pose data on /pose/keypoints...")
        print("Press ESC or Q to quit, F for fullscreen")
        print("")

    def setup_opengl(self):
        """Configure OpenGL"""
        glClearColor(0.02, 0.02, 0.08, 1.0)  # Deep space blue

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)

    def create_stars(self):
        """Create starfield background"""
        for i in range(200):
            self.stars.append(Star(
                x=random.uniform(0, self.width),
                y=random.uniform(0, self.height),
                size=random.uniform(1.0, 3.0),
                brightness=random.uniform(0.3, 1.0)
            ))

    def create_planets(self):
        """Create orbiting planets"""
        center_x = self.width / 2.0
        center_y = self.height / 2.0

        self.planets.append(Planet(150, 0.002, 15, COSMIC_COLORS['purple']))
        self.planets.append(Planet(250, 0.001, 20, COSMIC_COLORS['cyan']))
        self.planets.append(Planet(350, 0.0008, 12, COSMIC_COLORS['gold']))
        self.planets.append(Planet(450, 0.0005, 18, COSMIC_COLORS['green']))

    def start_osc_server(self):
        """Start OSC server"""
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
        """Handle incoming pose keypoints"""
        if len(args) < 52:
            return

        person_id = int(args[0])
        keypoints = []

        for i in range(1, len(args), 3):
            if i + 2 < len(args):
                keypoints.append([
                    float(args[i]),
                    float(args[i + 1]),
                    float(args[i + 2])
                ])

        with self.state.lock:
            self.state.poses[person_id] = PoseData(
                person_id=person_id,
                keypoints=keypoints,
                timestamp=time.time()
            )

    def update(self, dt):
        """Update logic"""
        current_time = time.time()

        # Remove stale poses
        with self.state.lock:
            stale_ids = [
                pid for pid, pose in self.state.poses.items()
                if current_time - pose.timestamp > self.state.pose_timeout
            ]
            for pid in stale_ids:
                del self.state.poses[pid]

        # Update cosmic effects
        self.glow_phase += dt * 2.0
        self.nebula_phase += dt * 0.5

        # Update planets
        for planet in self.planets:
            planet.angle += planet.speed

        # Update FPS
        self.fps_frames += 1
        if current_time - self.fps_time >= 1.0:
            self.fps = self.fps_frames / (current_time - self.fps_time)
            self.fps_frames = 0
            self.fps_time = current_time

    def on_draw(self):
        """Render the scene"""
        self.clear()

        # Setup 2D projection
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # Draw layers
        self.draw_nebula()
        self.draw_stars()
        self.draw_planets()

        # Draw poses
        with self.state.lock:
            poses = list(self.state.poses.values())

        for pose in poses:
            self.draw_cosmic_skeleton(pose)

        # Draw HUD
        self.draw_hud(len(poses))

    def draw_nebula(self):
        """Draw pulsating nebula background"""
        center_x = self.width / 2.0
        center_y = self.height / 2.0

        # Pulsating glow
        glow = 0.3 + 0.2 * math.sin(self.nebula_phase)

        # Draw gradient circles
        for radius in range(400, 0, -50):
            alpha = glow * (radius / 400.0) * 0.3

            glColor4f(0.4, 0.1, 0.6, alpha)  # Purple nebula
            glBegin(GL_TRIANGLE_FAN)
            glVertex2f(center_x, center_y)

            segments = 32
            for i in range(segments + 1):
                angle = (i / float(segments)) * math.pi * 2
                x = center_x + math.cos(angle) * radius
                y = center_y + math.sin(angle) * radius
                glVertex2f(x, y)

            glEnd()

    def draw_stars(self):
        """Draw twinkling stars"""
        glPointSize(2.0)
        glBegin(GL_POINTS)

        current_time = time.time()

        for star in self.stars:
            # Twinkle effect
            twinkle = 0.5 + 0.5 * math.sin(current_time * star.twinkle_speed + star.twinkle_phase)
            brightness = star.brightness * twinkle

            glColor4f(1.0, 1.0, 1.0, brightness)
            glVertex2f(star.x, star.y)

        glEnd()

    def draw_planets(self):
        """Draw orbiting planets"""
        center_x = self.width / 2.0
        center_y = self.height / 2.0

        for planet in self.planets:
            x = center_x + math.cos(planet.angle) * planet.distance
            y = center_y + math.sin(planet.angle) * planet.distance

            # Draw planet
            color = planet.color
            glColor4f(color[0], color[1], color[2], 0.6)

            segments = 16
            glBegin(GL_TRIANGLE_FAN)
            glVertex2f(x, y)

            for i in range(segments + 1):
                angle = (i / float(segments)) * math.pi * 2
                px = x + math.cos(angle) * planet.size
                py = y + math.sin(angle) * planet.size
                glVertex2f(px, py)

            glEnd()

            # Draw glow
            glColor4f(color[0], color[1], color[2], 0.2)
            glBegin(GL_TRIANGLE_FAN)
            glVertex2f(x, y)

            for i in range(segments + 1):
                angle = (i / float(segments)) * math.pi * 2
                px = x + math.cos(angle) * planet.size * 2.0
                py = y + math.sin(angle) * planet.size * 2.0
                glVertex2f(px, py)

            glEnd()

    def draw_cosmic_skeleton(self, pose):
        """Draw skeleton with cosmic glow effects"""
        keypoints = pose.keypoints

        # Glow intensity
        glow = 0.7 + 0.3 * math.sin(self.glow_phase)

        # Draw glowing connections
        glLineWidth(5.0)
        glBegin(GL_LINES)

        for conn in SKELETON_CONNECTIONS:
            kp1_idx, kp2_idx = conn

            if kp1_idx >= len(keypoints) or kp2_idx >= len(keypoints):
                continue

            kp1 = keypoints[kp1_idx]
            kp2 = keypoints[kp2_idx]

            if kp1[2] > 0.5 and kp2[2] > 0.5:
                # Average colors
                color1 = get_keypoint_color(kp1_idx)
                color2 = get_keypoint_color(kp2_idx)
                color = (
                    (color1[0] + color2[0]) / 2.0,
                    (color1[1] + color2[1]) / 2.0,
                    (color1[2] + color2[2]) / 2.0
                )

                glColor4f(color[0], color[1], color[2], glow)

                x1 = kp1[0] * self.width
                y1 = kp1[1] * self.height
                x2 = kp2[0] * self.width
                y2 = kp2[1] * self.height

                glVertex2f(x1, y1)
                glVertex2f(x2, y2)

        glEnd()

        # Draw glowing keypoints
        glPointSize(12.0)
        glBegin(GL_POINTS)

        for i, kp in enumerate(keypoints):
            if kp[2] > 0.5:
                color = get_keypoint_color(i)
                glColor4f(color[0], color[1], color[2], glow)

                x = kp[0] * self.width
                y = kp[1] * self.height

                glVertex2f(x, y)

        glEnd()

    def draw_hud(self, pose_count):
        """Draw HUD"""
        # Semi-transparent background
        glColor4f(0.0, 0.0, 0.0, 0.6)
        glBegin(GL_QUADS)
        glVertex2f(10, 10)
        glVertex2f(250, 10)
        glVertex2f(250, 80)
        glVertex2f(10, 80)
        glEnd()

        # Info text
        info_lines = [
            "FPS: {:.1f}".format(self.fps),
            "Poses: {}".format(pose_count),
            "Port: {}".format(self.osc_port)
        ]

        y_offset = 20
        for line in info_lines:
            label = pyglet.text.Label(
                line,
                font_name='Courier New',
                font_size=12,
                x=20, y=y_offset,
                color=(0, 255, 255, 255)  # Cyan text
            )
            label.draw()
            y_offset += 20

    def on_key_press(self, symbol, modifiers):
        """Handle keyboard"""
        if symbol == pyglet.window.key.ESCAPE or symbol == pyglet.window.key.Q:
            print("\nShutting down...")
            self.osc_server.shutdown()
            pyglet.app.exit()
        elif symbol == pyglet.window.key.F:
            self.set_fullscreen(not self.fullscreen)


def main():
    parser = argparse.ArgumentParser(
        description="Cosmic GPU skeleton visualizer for Jetson TX1"
    )
    parser.add_argument("--osc-port", type=int, default=5008)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fullscreen", action="store_true")

    args = parser.parse_args()

    try:
        visualizer = CosmicGPUVisualizer(
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
