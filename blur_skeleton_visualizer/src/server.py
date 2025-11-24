#!/usr/bin/env python3
"""Blur video visualizer with skeleton overlay"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set

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


class VideoBlurServer:
    """Receives video frames and poses via OSC, applies blur, streams to web."""

    def __init__(self, osc_port: int, web_port: int, blur_amount: int = 25):
        self.osc_port = osc_port
        self.web_port = web_port
        self.blur_amount = blur_amount  # Kernel size for Gaussian blur

        # Video frame storage
        self.current_frame = None
        self.frame_lock = threading.Lock()

        # Pose data storage
        self.poses: Dict[int, PoseData] = {}
        self.pose_lock = threading.Lock()

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

        # Video frame handler (if detector sends frames)
        self.osc_dispatcher.map(f"{base}/video/frame", self._handle_video_frame)

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

    def _handle_video_frame(self, address: str, *args):
        """Handle video frame from OSC (if implemented in detector)"""
        # This would require detector to send frames via OSC
        # For now, we'll rely on detector having a video stream endpoint
        pass

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
        # Simulated camera for now (detector will provide real frames)
        cap = cv2.VideoCapture(0)

        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    await asyncio.sleep(0.1)
                    continue

                # Apply blur
                blurred = cv2.GaussianBlur(frame, (self.blur_amount, self.blur_amount), 0)

                # Draw skeletons on blurred frame
                with self.pose_lock:
                    for person_id, pose in list(self.poses.items()):
                        # Remove old poses (older than 1 second)
                        if time.time() - pose.timestamp > 1.0:
                            del self.poses[person_id]
                            continue

                        self._draw_skeleton(blurred, pose.keypoints)

                # Encode frame to JPEG
                _, buffer = cv2.imencode('.jpg', blurred, [cv2.IMWRITE_JPEG_QUALITY, 85])
                frame_b64 = base64.b64encode(buffer).decode('utf-8')

                # Broadcast to all clients
                message = json.dumps({
                    "type": "frame",
                    "data": frame_b64
                })

                with self.clients_lock:
                    disconnected = set()
                    for client in self.clients:
                        try:
                            await client.send_text(message)
                        except:
                            disconnected.add(client)

                    # Remove disconnected clients
                    self.clients -= disconnected

                # Control frame rate (~30 FPS)
                await asyncio.sleep(0.033)

        finally:
            cap.release()

    def _draw_skeleton(self, frame: np.ndarray, keypoints: List[List[float]]):
        """Draw skeleton lines on frame with high intensity"""
        # YOLO pose keypoint connections
        connections = [
            (0, 1), (0, 2), (1, 3), (2, 4),  # Head
            (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),  # Arms
            (5, 11), (6, 12), (11, 12),  # Torso
            (11, 13), (13, 15), (12, 14), (14, 16)  # Legs
        ]

        h, w = frame.shape[:2]

        # Draw connections
        for start_idx, end_idx in connections:
            if start_idx < len(keypoints) and end_idx < len(keypoints):
                start_kp = keypoints[start_idx]
                end_kp = keypoints[end_idx]

                # Check confidence
                if start_kp[2] > 0.5 and end_kp[2] > 0.5:
                    # Convert normalized coords to pixel coords
                    start_point = (int(start_kp[0] * w), int(start_kp[1] * h))
                    end_point = (int(end_kp[0] * w), int(end_kp[1] * h))

                    # Draw thick, bright line
                    cv2.line(frame, start_point, end_point, (0, 255, 255), 4, cv2.LINE_AA)

        # Draw keypoints
        for kp in keypoints:
            if kp[2] > 0.5:
                point = (int(kp[0] * w), int(kp[1] * h))
                cv2.circle(frame, point, 6, (0, 255, 0), -1, cv2.LINE_AA)

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
    parser.add_argument("--blur", type=int, default=25, help="Blur amount (kernel size, must be odd)")

    args = parser.parse_args()

    # Ensure blur amount is odd
    if args.blur % 2 == 0:
        args.blur += 1

    server = VideoBlurServer(args.osc_port, args.port, args.blur)
    server.run()


if __name__ == "__main__":
    main()
