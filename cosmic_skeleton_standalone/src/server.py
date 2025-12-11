#!/usr/bin/env python3
"""
Cosmic Skeleton Standalone Visualizer
Combines YOLO pose detection with cosmic visual effects - no external detector needed
"""

from __future__ import annotations

import argparse
import asyncio
import json
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set

import cv2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from ultralytics import YOLO
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


class CosmicSkeletonStandalone:
    """Standalone cosmic skeleton visualizer with integrated YOLO detection"""

    def __init__(self, video_source: int = 0, web_port: int = 8094,
                 model: str = "yolov8n-pose.pt", imgsz: int = 416):
        self.video_source = video_source
        self.web_port = web_port
        self.imgsz = imgsz

        # YOLO model
        print(f"Loading YOLO model: {model}")
        self.model = YOLO(model)

        # Pose data storage
        self.poses: Dict[int, PoseData] = {}
        self.lock = threading.Lock()

        # WebSocket clients
        self.clients: Set[WebSocket] = set()

        # Control
        self.running = False
        self.loop: asyncio.AbstractEventLoop | None = None

        # FastAPI app
        self.app = self._create_app()

    def _create_app(self) -> FastAPI:
        """Create FastAPI application"""
        app = FastAPI(title="Cosmic Skeleton Standalone")

        base_path = Path(__file__).parent.parent
        static_path = base_path / "static"
        templates_path = base_path / "templates"

        # Mount static files
        if static_path.exists():
            app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

        # Templates
        templates = Jinja2Templates(directory=str(templates_path))

        @app.get("/")
        async def index(request: Request):
            return templates.TemplateResponse("cosmic.html", {"request": request})

        @app.get("/api/snapshot")
        async def snapshot():
            with self.lock:
                return JSONResponse({
                    "poses": [pose.to_dict() for pose in self.poses.values()]
                })

        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.clients.add(websocket)
            print(f"Client connected (total: {len(self.clients)})")

            # Send initial snapshot
            try:
                with self.lock:
                    await websocket.send_json({
                        "poses": [pose.to_dict() for pose in self.poses.values()]
                    })
            except Exception:
                pass

            try:
                while True:
                    # Keep connection alive
                    data = await websocket.receive_text()
                    if data == "reset":
                        with self.lock:
                            self.poses.clear()
                        await websocket.send_json({"poses": []})
            except WebSocketDisconnect:
                pass
            finally:
                self.clients.discard(websocket)
                print(f"Client disconnected (total: {len(self.clients)})")

        return app

    def attach_loop(self, loop: asyncio.AbstractEventLoop):
        """Attach event loop for async operations"""
        self.loop = loop

    async def _broadcast(self, payload: Dict):
        """Broadcast data to all connected clients"""
        if not self.clients:
            return

        message = json.dumps(payload)
        disconnected = set()

        for ws in self.clients:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.add(ws)

        for ws in disconnected:
            self.clients.discard(ws)

    def _process_video(self):
        """Process video with YOLO detection in background thread"""
        cap = cv2.VideoCapture(self.video_source)

        # Set camera properties for lower latency
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not cap.isOpened():
            print(f"❌ Cannot open video source: {self.video_source}")
            return

        print(f"📹 Video capture started: {self.video_source}")
        print(f"🎨 Cosmic Skeleton running on http://0.0.0.0:{self.web_port}")

        frame_count = 0
        last_broadcast = 0.0
        min_broadcast_interval = 0.05  # 20 FPS max

        while self.running:
            ret, frame = cap.read()
            if not ret:
                print("❌ Cannot read frame")
                break

            frame_count += 1
            h, w = frame.shape[:2]

            # Run YOLO detection
            results = self.model.track(
                frame,
                persist=True,
                verbose=False,
                imgsz=self.imgsz,
                conf=0.3,
                iou=0.45,
                max_det=10,
                device='cpu',
                half=False
            )

            # Extract poses
            current_poses = {}
            if results and results[0].keypoints is not None:
                keypoints_data = results[0].keypoints.data.cpu().numpy()

                # Get tracking IDs if available
                if results[0].boxes.id is not None:
                    track_ids = results[0].boxes.id.cpu().numpy().astype(int)
                else:
                    track_ids = list(range(len(keypoints_data)))

                for person_id, kps in zip(track_ids, keypoints_data):
                    # Normalize keypoints to 0-1 range
                    keypoints = []
                    for kp in kps:
                        x, y, conf = kp
                        keypoints.append([float(x / w), float(y / h), float(conf)])

                    current_poses[person_id] = PoseData(
                        timestamp=time.time(),
                        person_id=int(person_id),
                        keypoints=keypoints
                    )

            # Update poses and cleanup stale ones
            with self.lock:
                current_time = time.time()
                self.poses = current_poses

                # Remove stale poses (older than 1 second)
                stale_ids = [
                    pid for pid, pose in self.poses.items()
                    if current_time - pose.timestamp > 1.0
                ]
                for pid in stale_ids:
                    del self.poses[pid]

            # Broadcast to clients
            if self.loop and self.clients:
                current_time = time.time()
                if current_time - last_broadcast >= min_broadcast_interval:
                    last_broadcast = current_time
                    with self.lock:
                        payload = {
                            "poses": [pose.to_dict() for pose in self.poses.values()]
                        }
                    asyncio.run_coroutine_threadsafe(self._broadcast(payload), self.loop)

        cap.release()
        print("📹 Video capture stopped")

    def start(self):
        """Start the standalone visualizer"""
        self.running = True

        # Start video processing thread
        video_thread = threading.Thread(target=self._process_video, daemon=True)
        video_thread.start()

        # Run FastAPI with uvicorn
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.web_port,
            log_level="info",
        )
        server = uvicorn.Server(config)

        # Attach event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.attach_loop(loop)

        print(f"🌌 Cosmic Skeleton Standalone starting...")
        print(f"   Web UI: http://0.0.0.0:{self.web_port}")
        print(f"   Video source: {self.video_source}")
        print(f"   Model: yolov8n-pose.pt (imgsz={self.imgsz})")

        try:
            loop.run_until_complete(server.serve())
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
        finally:
            self.running = False


def main():
    parser = argparse.ArgumentParser(description="Cosmic Skeleton Standalone Visualizer")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8094, help="Web port (default: 8094)")
    parser.add_argument("--source", type=int, default=0, help="Video source (default: 0 = webcam)")
    parser.add_argument("--model", default="yolov8n-pose.pt", help="YOLO model to use")
    parser.add_argument("--imgsz", type=int, default=416, help="Input image size (default: 416)")

    args = parser.parse_args()

    visualizer = CosmicSkeletonStandalone(
        video_source=args.source,
        web_port=args.port,
        model=args.model,
        imgsz=args.imgsz
    )
    visualizer.start()


if __name__ == "__main__":
    main()
