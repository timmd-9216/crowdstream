#!/usr/bin/env python3
"""FastAPI-based skeleton visualizer for YOLO pose detection from video files"""

from __future__ import annotations

import argparse
import asyncio
import json
import threading
import time
from pathlib import Path
from typing import Dict, List, Set

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from ultralytics import YOLO
import uvicorn


class VideoProcessor:
    """Process video file with YOLO pose detection"""

    def __init__(self, video_path: str, model_name: str = "yolo11n-pose.pt"):
        self.video_path = video_path
        self.model = YOLO(model_name)
        self.cap = None
        self.running = False
        self.thread = None
        self.current_poses = []
        self.lock = threading.Lock()
        self.broadcast_callback = None

    def start(self):
        """Start video processing in background thread"""
        if self.running:
            return

        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open video file: {self.video_path}")

        self.running = True
        self.thread = threading.Thread(target=self._process_video, daemon=True)
        self.thread.start()
        print(f"📹 Video processing started: {self.video_path}")

    def stop(self):
        """Stop video processing"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()

    def _process_video(self):
        """Process video frames with YOLO pose detection"""
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        frame_delay = 1.0 / fps

        while self.running:
            ret, frame = self.cap.read()

            # Loop video if reached end
            if not ret:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            # Run YOLO pose detection
            results = self.model(frame, verbose=False)

            # Extract poses
            poses = []
            if results and len(results) > 0:
                result = results[0]
                if result.keypoints is not None:
                    keypoints_data = result.keypoints.data.cpu().numpy()
                    h, w = frame.shape[:2]

                    for person_id, person_kpts in enumerate(keypoints_data):
                        keypoints = []
                        for kpt in person_kpts:
                            x, y, conf = kpt
                            # Normalize to 0-1 range
                            keypoints.append([float(x / w), float(y / h), float(conf)])

                        poses.append({
                            "person_id": person_id,
                            "keypoints": keypoints,
                            "timestamp": time.time()
                        })

            # Update current poses
            with self.lock:
                self.current_poses = poses

            # Trigger broadcast
            if self.broadcast_callback:
                self.broadcast_callback()

            # Maintain video frame rate
            time.sleep(frame_delay)

    def get_poses(self) -> List[Dict]:
        """Get current poses snapshot"""
        with self.lock:
            return self.current_poses.copy()


class SkeletonState:
    """Holds pose data and manages WebSocket broadcasts."""

    def __init__(self, video_processor: VideoProcessor):
        self.video_processor = video_processor
        self.loop: asyncio.AbstractEventLoop | None = None
        self.clients: Set[WebSocket] = set()
        self.last_broadcast_time = 0.0
        self.min_interval = 0.05  # 20 FPS max

        # Set broadcast callback
        self.video_processor.broadcast_callback = self._maybe_broadcast

    def attach_loop(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def _maybe_broadcast(self):
        now = time.time()
        if now - self.last_broadcast_time < self.min_interval:
            return

        self.last_broadcast_time = now

        if self.loop and self.clients:
            payload = {"poses": self.video_processor.get_poses()}
            asyncio.run_coroutine_threadsafe(self._broadcast(payload), self.loop)

    async def _broadcast(self, payload: Dict):
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

    def snapshot(self) -> Dict:
        """Get current state snapshot"""
        return {"poses": self.video_processor.get_poses()}


def create_app(state: SkeletonState) -> FastAPI:
    """Create FastAPI application"""
    app = FastAPI(title="Video Skeleton Visualizer")

    # Get paths relative to this file
    base_path = Path(__file__).parent.parent
    static_path = base_path / "static"
    templates_path = base_path / "templates"

    # Templates
    templates = Jinja2Templates(directory=str(templates_path))

    # Mount static files BEFORE defining routes
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    @app.get("/")
    async def index(request: Request):
        return templates.TemplateResponse("cosmic.html", {"request": request})

    @app.get("/api/snapshot")
    async def snapshot():
        return JSONResponse(state.snapshot())

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        state.clients.add(websocket)
        print(f"Client connected (total: {len(state.clients)})")

        # Send initial snapshot
        try:
            await websocket.send_json(state.snapshot())
        except Exception:
            pass

        try:
            while True:
                # Just keep connection alive, actual updates come from video processor
                data = await websocket.receive_text()

                # Handle reset if needed
                if data == "reset":
                    await websocket.send_json(state.snapshot())

        except WebSocketDisconnect:
            pass
        finally:
            state.clients.discard(websocket)
            print(f"Client disconnected (total: {len(state.clients)})")

    return app


def main():
    parser = argparse.ArgumentParser(description="Video skeleton visualizer server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8094, help="Port to bind to")
    parser.add_argument("--video", required=True, help="Path to video file")
    parser.add_argument("--model", default="yolo11n-pose.pt", help="YOLO model to use")
    args = parser.parse_args()

    # Validate video file
    video_path = Path(args.video)
    if not video_path.exists():
        print(f"Error: Video file not found: {args.video}")
        return 1

    # Create video processor
    processor = VideoProcessor(str(video_path), args.model)

    # Create state and app
    state = SkeletonState(processor)
    app = create_app(state)

    # Start video processing
    processor.start()

    # Run FastAPI with uvicorn
    config = uvicorn.Config(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
    )
    server = uvicorn.Server(config)

    # Attach event loop to state
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    state.attach_loop(loop)

    print(f"🌌 Video Skeleton visualizer starting on http://{args.host}:{args.port}")
    print(f"📹 Processing video: {args.video}")

    try:
        loop.run_until_complete(server.serve())
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        processor.stop()


if __name__ == "__main__":
    main()
