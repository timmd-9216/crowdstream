#!/usr/bin/env python3
"""FastAPI-based skeleton visualizer for YOLO pose detection"""

from __future__ import annotations

import argparse
import asyncio
import json
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
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


class SkeletonState:
    """Holds pose data and manages WebSocket broadcasts."""

    def __init__(self, max_people: int = 10):
        self.max_people = max_people
        self.poses: Dict[int, PoseData] = {}  # person_id -> PoseData
        self.lock = threading.Lock()

        self.last_broadcast_time = 0.0
        self.min_interval = 0.05  # 20 FPS max

        self.loop: asyncio.AbstractEventLoop | None = None
        self.clients: Set[WebSocket] = set()

        # OSC dispatcher
        self.osc_dispatcher = dispatcher.Dispatcher()
        self.osc_dispatcher.map("/pose/keypoints", self._handle_keypoints)
        self.osc_server: osc_server.ThreadingOSCUDPServer | None = None

    def attach_loop(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def start_osc(self, osc_port: int):
        if self.osc_server is not None:
            return

        try:
            server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", osc_port), self.osc_dispatcher)
        except OSError as exc:
            raise RuntimeError(f"No se pudo abrir el puerto OSC {osc_port}: {exc}") from exc

        self.osc_server = server

        def _serve():
            print(f"OSC server listening on port {osc_port}")
            self.osc_server.serve_forever()

        thread = threading.Thread(target=_serve, daemon=True)
        thread.start()

    def stop_osc(self):
        if self.osc_server:
            self.osc_server.shutdown()

    def _handle_keypoints(self, address, *args):
        """Handle incoming pose keypoints from OSC"""
        # Expected format: /pose/keypoints person_id kp0_x kp0_y kp0_conf kp1_x kp1_y kp1_conf ...
        # YOLO has 17 keypoints, so we expect 1 + (17 * 3) = 52 values
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

        with self.lock:
            self.poses[person_id] = PoseData(
                timestamp=time.time(),
                person_id=person_id,
                keypoints=keypoints
            )

            # Remove stale poses (older than 1 second)
            current_time = time.time()
            stale_ids = [
                pid for pid, pose in self.poses.items()
                if current_time - pose.timestamp > 1.0
            ]
            for pid in stale_ids:
                del self.poses[pid]

        # Trigger broadcast
        self._maybe_broadcast()

    def _maybe_broadcast(self):
        now = time.time()
        if now - self.last_broadcast_time < self.min_interval:
            return

        self.last_broadcast_time = now

        if self.loop and self.clients:
            with self.lock:
                payload = {
                    "poses": [pose.to_dict() for pose in self.poses.values()]
                }
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
        with self.lock:
            return {
                "poses": [pose.to_dict() for pose in self.poses.values()]
            }


def create_app(state: SkeletonState) -> FastAPI:
    """Create FastAPI application"""
    app = FastAPI(title="Cosmic Skeleton Visualizer")

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
                # Just keep connection alive, actual updates come from OSC
                data = await websocket.receive_text()

                # Handle reset if needed
                if data == "reset":
                    with state.lock:
                        state.poses.clear()
                    await websocket.send_json(state.snapshot())

        except WebSocketDisconnect:
            pass
        finally:
            state.clients.discard(websocket)
            print(f"Client disconnected (total: {len(state.clients)})")

    return app


def main():
    parser = argparse.ArgumentParser(description="Cosmic skeleton visualizer server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8093, help="Port to bind to")
    parser.add_argument("--osc-port", type=int, default=5008, help="OSC port to listen on")
    args = parser.parse_args()

    state = SkeletonState()
    app = create_app(state)

    # Start OSC server
    state.start_osc(args.osc_port)

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

    print(f"🌌 Cosmic Skeleton visualizer starting on http://{args.host}:{args.port}")
    print(f"OSC listening on port {args.osc_port}")

    try:
        loop.run_until_complete(server.serve())
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        state.stop_osc()


if __name__ == "__main__":
    main()
