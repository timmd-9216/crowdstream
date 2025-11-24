#!/usr/bin/env python3
"""Blur video visualizer with skeleton overlay and space elements"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import math
import random
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pythonosc import dispatcher, osc_server
import uvicorn


@dataclass
class PoseData:
    """Single pose detection data"""
    timestamp: float
    person_id: int
    keypoints: List[List[float]]  # [[x, y, confidence], ...]

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "person_id": self.person_id,
            "keypoints": self.keypoints,
        }


@dataclass
class MovementData:
    """Movement intensity data from OSC"""
    timestamp: float
    head_movement: float = 0.0
    arm_movement: float = 0.0
    leg_movement: float = 0.0
    total_movement: float = 0.0


class SpaceParticle:
    """A particle in space (star, planet, etc)"""
    def __init__(self, x: float, y: float, size: float, color: Tuple[int, int, int],
                 speed: float, particle_type: str):
        self.x = x
        self.y = y
        self.base_size = size
        self.size = size
        self.color = color
        self.speed = speed
        self.type = particle_type  # 'star', 'planet', 'nebula'
        self.angle = random.uniform(0, 2 * math.pi)
        self.phase = random.uniform(0, 2 * math.pi)

    def update(self, movement_intensity: float, frame_width: int, frame_height: int):
        """Update particle position and size based on movement"""
        # Move based on speed and movement intensity
        movement_factor = 1.0 + (movement_intensity / 100.0) * 3.0
        self.x += math.cos(self.angle) * self.speed * movement_factor
        self.y += math.sin(self.angle) * self.speed * movement_factor

        # Wrap around screen
        if self.x < 0:
            self.x = frame_width
        elif self.x > frame_width:
            self.x = 0
        if self.y < 0:
            self.y = frame_height
        elif self.y > frame_height:
            self.y = 0

        # Pulse size based on movement
        self.phase += 0.1
        pulse = math.sin(self.phase) * 0.3 + 1.0
        self.size = self.base_size * pulse * (1.0 + movement_intensity / 200.0)

    def draw(self, frame: np.ndarray, alpha: float = 0.6):
        """Draw particle on frame"""
        overlay = frame.copy()
        center = (int(self.x), int(self.y))
        radius = int(self.size)

        if self.type == 'star':
            # Draw star as bright point with glow
            cv2.circle(overlay, center, radius, self.color, -1, cv2.LINE_AA)
            cv2.circle(overlay, center, radius * 2, self.color, 1, cv2.LINE_AA)
        elif self.type == 'planet':
            # Draw planet with ring
            cv2.circle(overlay, center, radius, self.color, -1, cv2.LINE_AA)
            cv2.ellipse(overlay, center, (radius * 2, radius // 2), 0, 0, 360,
                       self.color, 1, cv2.LINE_AA)
        elif self.type == 'nebula':
            # Draw nebula as soft cloud
            for i in range(3):
                offset_x = random.randint(-radius, radius)
                offset_y = random.randint(-radius, radius)
                pos = (center[0] + offset_x, center[1] + offset_y)
                cv2.circle(overlay, pos, radius, self.color, -1, cv2.LINE_AA)

        # Blend with original frame
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


class VideoBlurServer:
    """Receives video frames and poses via OSC, applies blur, streams to web."""

    def __init__(self, osc_port: int, web_port: int, blur_amount: int = 51):
        self.osc_port = osc_port
        self.web_port = web_port
        self.blur_amount = blur_amount  # Kernel size for Gaussian blur

        # Video frame storage
        self.current_frame = None
        self.frame_lock = threading.Lock()

        # Pose data storage
        self.poses: Dict[int, PoseData] = {}
        self.pose_lock = threading.Lock()

        # Movement data storage
        self.movement_data = MovementData(timestamp=time.time())
        self.movement_lock = threading.Lock()
        self.movement_history = deque(maxlen=30)  # 1 second at 30fps

        # Space particles
        self.particles: List[SpaceParticle] = []
        self.particle_lock = threading.Lock()

        # WebSocket clients
        self.clients: Set[WebSocket] = set()
        self.clients_lock = threading.Lock()

        # OSC setup
        self.osc_dispatcher = dispatcher.Dispatcher()
        self.setup_osc_handlers()
        self.osc_thread = None
        self.osc_server = None

        # FastAPI app
        self.app = FastAPI(title="Blur Skeleton Visualizer")
        self.setup_routes()

        # Broadcast control
        self.running = False
        self.broadcast_task = None

    def setup_osc_handlers(self):
        """Setup OSC message handlers"""
        base = "/dance"

        # Pose keypoints handler
        self.osc_dispatcher.map(f"{base}/pose/person/*/keypoints", self._handle_pose_keypoints)

        # Movement handlers
        self.osc_dispatcher.map(f"{base}/total_movement", self._handle_total_movement)
        self.osc_dispatcher.map(f"{base}/head_movement", self._handle_head_movement)
        self.osc_dispatcher.map(f"{base}/arm_movement", self._handle_arm_movement)
        self.osc_dispatcher.map(f"{base}/leg_movement", self._handle_leg_movement)

    def _handle_pose_keypoints(self, address: str, *args):
        """Handle pose keypoints from OSC"""
        try:
            # Extract person_id from address: /dance/pose/person/0/keypoints
            parts = address.split('/')
            person_id = int(parts[4])

            # Parse keypoints: [x1, y1, conf1, x2, y2, conf2, ...]
            keypoints = []
            for i in range(0, len(args), 3):
                if i + 2 < len(args):
                    keypoints.append([args[i], args[i+1], args[i+2]])

            with self.pose_lock:
                self.poses[person_id] = PoseData(
                    timestamp=time.time(),
                    person_id=person_id,
                    keypoints=keypoints
                )
        except Exception as e:
            print(f"Error handling pose keypoints: {e}")

    def _handle_total_movement(self, address: str, value: float):
        """Handle total movement intensity"""
        with self.movement_lock:
            self.movement_data.total_movement = value
            self.movement_data.timestamp = time.time()

    def _handle_head_movement(self, address: str, value: float):
        """Handle head movement intensity"""
        with self.movement_lock:
            self.movement_data.head_movement = value

    def _handle_arm_movement(self, address: str, value: float):
        """Handle arm movement intensity"""
        with self.movement_lock:
            self.movement_data.arm_movement = value

    def _handle_leg_movement(self, address: str, value: float):
        """Handle leg movement intensity"""
        with self.movement_lock:
            self.movement_data.leg_movement = value

    def initialize_particles(self, width: int, height: int):
        """Initialize space particles"""
        with self.particle_lock:
            self.particles = []

            # Stars (many, small, fast) - react to head movement
            for _ in range(100):
                self.particles.append(SpaceParticle(
                    x=random.uniform(0, width),
                    y=random.uniform(0, height),
                    size=random.uniform(1, 3),
                    color=(255, 255, 255),
                    speed=random.uniform(0.5, 2.0),
                    particle_type='star'
                ))

            # Planets (few, medium, medium speed) - react to arm movement
            for _ in range(10):
                self.particles.append(SpaceParticle(
                    x=random.uniform(0, width),
                    y=random.uniform(0, height),
                    size=random.uniform(10, 25),
                    color=(random.randint(100, 255), random.randint(100, 255),
                          random.randint(100, 255)),
                    speed=random.uniform(0.2, 1.0),
                    particle_type='planet'
                ))

            # Nebulas (few, large, slow) - react to leg movement
            for _ in range(5):
                self.particles.append(SpaceParticle(
                    x=random.uniform(0, width),
                    y=random.uniform(0, height),
                    size=random.uniform(30, 60),
                    color=(random.randint(50, 150), random.randint(50, 150),
                          random.randint(100, 255)),
                    speed=random.uniform(0.1, 0.5),
                    particle_type='nebula'
                ))

    def setup_routes(self):
        """Setup FastAPI routes"""
        base_path = Path(__file__).parent.parent

        # Static files
        static_path = base_path / "static"
        if static_path.exists():
            self.app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

        # Templates
        templates_path = base_path / "templates"
        templates = Jinja2Templates(directory=str(templates_path))

        @self.app.get("/", response_class=HTMLResponse)
        async def index(request: Request):
            return templates.TemplateResponse("index.html", {"request": request})

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            with self.clients_lock:
                self.clients.add(websocket)

            try:
                while True:
                    # Keep connection alive
                    await websocket.receive_text()
            except WebSocketDisconnect:
                with self.clients_lock:
                    self.clients.discard(websocket)

    async def broadcast_frames(self):
        """Continuously broadcast blurred frames with skeletons to clients"""
        cap = cv2.VideoCapture(0)

        # Get frame dimensions and initialize particles
        ret, test_frame = cap.read()
        if ret:
            h, w = test_frame.shape[:2]
            self.initialize_particles(w, h)

        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    await asyncio.sleep(0.1)
                    continue

                h, w = frame.shape[:2]

                # Apply heavy blur
                blurred = cv2.GaussianBlur(frame, (self.blur_amount, self.blur_amount), 0)

                # Additional blur pass for more effect
                blurred = cv2.GaussianBlur(blurred, (self.blur_amount, self.blur_amount), 0)

                # Get current movement data
                with self.movement_lock:
                    head_mov = self.movement_data.head_movement
                    arm_mov = self.movement_data.arm_movement
                    leg_mov = self.movement_data.leg_movement
                    total_mov = self.movement_data.total_movement

                # Update and draw space particles
                with self.particle_lock:
                    for particle in self.particles:
                        if particle.type == 'star':
                            particle.update(head_mov, w, h)
                        elif particle.type == 'planet':
                            particle.update(arm_mov, w, h)
                        elif particle.type == 'nebula':
                            particle.update(leg_mov, w, h)

                        particle.draw(blurred, alpha=0.4)

                # Draw skeletons with YOLO keypoints
                with self.pose_lock:
                    for person_id, pose in list(self.poses.items()):
                        # Remove old poses
                        if time.time() - pose.timestamp > 1.0:
                            del self.poses[person_id]
                            continue

                        self._draw_skeleton(blurred, pose.keypoints)

                # Add movement intensity overlay
                self._draw_movement_overlay(blurred, head_mov, arm_mov, leg_mov)

                # Encode frame to JPEG
                _, buffer = cv2.imencode('.jpg', blurred, [cv2.IMWRITE_JPEG_QUALITY, 85])
                frame_b64 = base64.b64encode(buffer).decode('utf-8')

                # Broadcast to all clients
                message = json.dumps({
                    "type": "frame",
                    "data": frame_b64,
                    "movement": {
                        "head": head_mov,
                        "arms": arm_mov,
                        "legs": leg_mov,
                        "total": total_mov
                    }
                })

                with self.clients_lock:
                    disconnected = set()
                    for client in self.clients:
                        try:
                            await client.send_text(message)
                        except:
                            disconnected.add(client)

                    self.clients -= disconnected

                # Control frame rate (~30 FPS)
                await asyncio.sleep(0.033)

        finally:
            cap.release()

    def _draw_skeleton(self, frame: np.ndarray, keypoints: List[List[float]]):
        """Draw skeleton lines and keypoints on frame with high intensity"""
        # YOLO pose keypoint connections
        connections = [
            (0, 1), (0, 2), (1, 3), (2, 4),  # Head
            (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),  # Arms
            (5, 11), (6, 12), (11, 12),  # Torso
            (11, 13), (13, 15), (12, 14), (14, 16)  # Legs
        ]

        h, w = frame.shape[:2]

        # Draw connections with glow effect
        for start_idx, end_idx in connections:
            if start_idx < len(keypoints) and end_idx < len(keypoints):
                start_kp = keypoints[start_idx]
                end_kp = keypoints[end_idx]

                # Check confidence
                if start_kp[2] > 0.5 and end_kp[2] > 0.5:
                    # Convert normalized coords to pixel coords
                    start_point = (int(start_kp[0] * w), int(start_kp[1] * h))
                    end_point = (int(end_kp[0] * w), int(end_kp[1] * h))

                    # Draw glow (thicker, semi-transparent)
                    overlay = frame.copy()
                    cv2.line(overlay, start_point, end_point, (0, 255, 255), 8, cv2.LINE_AA)
                    cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)

                    # Draw main line (bright and thick)
                    cv2.line(frame, start_point, end_point, (0, 255, 255), 4, cv2.LINE_AA)

        # Draw keypoints with glow
        for kp in keypoints:
            if kp[2] > 0.5:
                point = (int(kp[0] * w), int(kp[1] * h))

                # Outer glow
                cv2.circle(frame, point, 12, (0, 255, 0), 2, cv2.LINE_AA)

                # Inner bright circle
                cv2.circle(frame, point, 8, (0, 255, 0), -1, cv2.LINE_AA)

                # Center highlight
                cv2.circle(frame, point, 4, (255, 255, 255), -1, cv2.LINE_AA)

    def _draw_movement_overlay(self, frame: np.ndarray, head: float, arms: float, legs: float):
        """Draw movement intensity bars"""
        h, w = frame.shape[:2]

        bar_width = 200
        bar_height = 20
        x_start = 20
        y_start = h - 100

        # Background
        overlay = frame.copy()
        cv2.rectangle(overlay, (x_start - 10, y_start - 10),
                     (x_start + bar_width + 10, y_start + 80), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

        # Head movement (stars)
        self._draw_bar(frame, x_start, y_start, bar_width, bar_height,
                      head, (255, 255, 255), "Head")

        # Arm movement (planets)
        self._draw_bar(frame, x_start, y_start + 25, bar_width, bar_height,
                      arms, (255, 165, 0), "Arms")

        # Leg movement (nebulas)
        self._draw_bar(frame, x_start, y_start + 50, bar_width, bar_height,
                      legs, (147, 112, 219), "Legs")

    def _draw_bar(self, frame: np.ndarray, x: int, y: int, width: int, height: int,
                  value: float, color: Tuple[int, int, int], label: str):
        """Draw a single movement bar"""
        # Border
        cv2.rectangle(frame, (x, y), (x + width, y + height), (255, 255, 255), 1)

        # Fill
        fill_width = int((value / 100.0) * width)
        if fill_width > 0:
            cv2.rectangle(frame, (x, y), (x + fill_width, y + height), color, -1)

        # Label
        cv2.putText(frame, f"{label}: {value:.1f}", (x, y - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

    def start_osc_server(self):
        """Start OSC server in separate thread"""
        self.osc_server = osc_server.ThreadingOSCUDPServer(
            ('0.0.0.0', self.osc_port),
            self.osc_dispatcher
        )
        print(f"OSC server listening on port {self.osc_port}")
        self.osc_server.serve_forever()

    async def startup(self):
        """Start all background tasks"""
        self.running = True

        # Start OSC server
        self.osc_thread = threading.Thread(target=self.start_osc_server, daemon=True)
        self.osc_thread.start()

        # Start broadcast task
        self.broadcast_task = asyncio.create_task(self.broadcast_frames())

    async def shutdown(self):
        """Stop all background tasks"""
        self.running = False

        if self.broadcast_task:
            self.broadcast_task.cancel()
            try:
                await self.broadcast_task
            except asyncio.CancelledError:
                pass

        if self.osc_server:
            self.osc_server.shutdown()

    def run(self):
        """Run the server"""
        @self.app.on_event("startup")
        async def on_startup():
            await self.startup()

        @self.app.on_event("shutdown")
        async def on_shutdown():
            await self.shutdown()

        print(f"Starting Blur Skeleton Visualizer...")
        print(f"OSC port: {self.osc_port}")
        print(f"Web interface: http://0.0.0.0:{self.web_port}")
        print(f"Blur amount: {self.blur_amount}")

        uvicorn.run(
            self.app,
            host="0.0.0.0",
            port=self.web_port,
            log_level="info"
        )


def main():
    parser = argparse.ArgumentParser(description="Blur skeleton visualizer server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8092, help="Web port to bind to")
    parser.add_argument("--osc-port", type=int, default=5009, help="OSC port to listen on")
    parser.add_argument("--blur", type=int, default=51, help="Blur amount (kernel size, must be odd)")

    args = parser.parse_args()

    # Ensure blur amount is odd
    if args.blur % 2 == 0:
        args.blur += 1

    server = VideoBlurServer(args.osc_port, args.port, args.blur)
    server.run()


if __name__ == "__main__":
    main()
