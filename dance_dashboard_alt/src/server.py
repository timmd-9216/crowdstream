#!/usr/bin/env python3
"""FastAPI-based dance movement dashboard"""

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
class MovementData:
    timestamp: float
    person_count: int = 0
    total_movement: float = 0.0
    arm_movement: float = 0.0
    leg_movement: float = 0.0
    head_movement: float = 0.0

    def to_dict(self) -> Dict:
        ts = datetime.fromtimestamp(self.timestamp)
        return {
            "timestamp": self.timestamp,
            "datetime": ts.strftime("%H:%M:%S"),
            "person_count": self.person_count,
            "total_movement": round(self.total_movement, 2),
            "arm_movement": round(self.arm_movement, 2),
            "leg_movement": round(self.leg_movement, 2),
            "head_movement": round(self.head_movement, 2),
        }


class DashboardState:
    """Holds OSC data and manages WebSocket broadcasts."""

    def __init__(self, history_size: int = 100, min_interval: float = 0.1):
        self.history = deque(maxlen=history_size)
        self.current_data = MovementData(timestamp=time.time())
        self.cumulative = self._empty_cumulative()
        self.lock = threading.Lock()

        self.last_broadcast_time = 0.0
        self.min_interval = min_interval
        self.required_fields: Set[str] = {
            "person_count",
            "total_movement",
            "arm_movement",
            "leg_movement",
            "head_movement",
        }
        self.updated_fields: Set[str] = set()

        self.loop: asyncio.AbstractEventLoop | None = None
        self.clients: Set[WebSocket] = set()

        # OSC bits
        self.osc_dispatcher = dispatcher.Dispatcher()
        base = "/dance"
        self.osc_dispatcher.map(f"{base}/person_count", self._handle_person_count)
        self.osc_dispatcher.map(f"{base}/total_movement", self._handle_total_movement)
        self.osc_dispatcher.map(f"{base}/arm_movement", self._handle_arm_movement)
        self.osc_dispatcher.map(f"{base}/leg_movement", self._handle_leg_movement)
        self.osc_dispatcher.map(f"{base}/head_movement", self._handle_head_movement)
        self.osc_server: osc_server.ThreadingOSCUDPServer | None = None

    def attach_loop(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def start_osc(self, osc_port: int):
        if self.osc_server is not None:
            return

        try:
            server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", osc_port), self.osc_dispatcher)
        except OSError as exc:
            # Bubble up a clear message so the operator immediately sees
            # that the OSC port is already occupied.
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

    # Snapshot helpers -------------------------------------------------
    def _empty_cumulative(self) -> Dict:
        return {
            "total_messages": 0,
            "avg_people": 0.0,
            "max_people": 0,
            "avg_total_movement": 0.0,
            "avg_arm_movement": 0.0,
            "avg_leg_movement": 0.0,
            "avg_head_movement": 0.0,
            "max_total_movement": 0.0,
            "max_arm_movement": 0.0,
            "max_leg_movement": 0.0,
            "max_head_movement": 0.0,
            "start_time": time.time(),
        }

    def snapshot(self) -> Dict:
        with self.lock:
            payload = self._build_payload_locked(include_history=True)
        return payload

    def _build_payload_locked(self, include_history: bool = False) -> Dict:
        current = self.current_data.to_dict()
        data = {
            "current": current,
            "cumulative": dict(self.cumulative),
        }
        if include_history:
            data["history"] = list(self.history)
        return data

    def reset_stats(self) -> Dict:
        with self.lock:
            self.cumulative = self._empty_cumulative()
            self.history.clear()
            self.updated_fields.clear()
            payload = self._build_payload_locked(include_history=True)
        print("Statistics reset")
        return payload

    # OSC handlers -----------------------------------------------------
    def _handle_person_count(self, address, *args):
        with self.lock:
            self.current_data.person_count = int(args[0]) if args else 0
            self.updated_fields.add("person_count")
            self._maybe_broadcast_locked()

    def _handle_total_movement(self, address, *args):
        with self.lock:
            self.current_data.total_movement = float(args[0]) if args else 0.0
            self.updated_fields.add("total_movement")
            self._maybe_broadcast_locked()

    def _handle_arm_movement(self, address, *args):
        with self.lock:
            self.current_data.arm_movement = float(args[0]) if args else 0.0
            self.updated_fields.add("arm_movement")
            self._maybe_broadcast_locked()

    def _handle_leg_movement(self, address, *args):
        with self.lock:
            self.current_data.leg_movement = float(args[0]) if args else 0.0
            self.updated_fields.add("leg_movement")
            self._maybe_broadcast_locked()

    def _handle_head_movement(self, address, *args):
        with self.lock:
            self.current_data.head_movement = float(args[0]) if args else 0.0
            self.updated_fields.add("head_movement")
            self._maybe_broadcast_locked()

    def _maybe_broadcast_locked(self):
        now = time.time()
        self.current_data.timestamp = now

        if not self.required_fields.issubset(self.updated_fields):
            return

        elapsed = now - self.last_broadcast_time
        if elapsed < self.min_interval:
            return

        self._update_cumulative_locked()
        payload = self._materialize_payload_locked()
        self.last_broadcast_time = now
        self.updated_fields.clear()

        print(
            f"[{datetime.fromtimestamp(now).strftime('%H:%M:%S')}] "
            f"People: {self.current_data.person_count} | "
            f"Total: {self.current_data.total_movement:.1f}"
        )
        self.broadcast(payload)

    def _materialize_payload_locked(self) -> Dict:
        current = self.current_data.to_dict()
        self.history.append(current)
        return {
            "current": current,
            "cumulative": dict(self.cumulative),
            "history": list(self.history),
        }

    def _update_cumulative_locked(self):
        self.cumulative["total_messages"] += 1
        n = self.cumulative["total_messages"]
        self.cumulative["avg_people"] += (
            self.current_data.person_count - self.cumulative["avg_people"]
        ) / n
        self.cumulative["avg_total_movement"] += (
            self.current_data.total_movement - self.cumulative["avg_total_movement"]
        ) / n
        self.cumulative["avg_arm_movement"] += (
            self.current_data.arm_movement - self.cumulative["avg_arm_movement"]
        ) / n
        self.cumulative["avg_leg_movement"] += (
            self.current_data.leg_movement - self.cumulative["avg_leg_movement"]
        ) / n
        self.cumulative["avg_head_movement"] += (
            self.current_data.head_movement - self.cumulative["avg_head_movement"]
        ) / n

        self.cumulative["max_people"] = max(
            self.cumulative["max_people"], self.current_data.person_count
        )
        self.cumulative["max_total_movement"] = max(
            self.cumulative["max_total_movement"], self.current_data.total_movement
        )
        self.cumulative["max_arm_movement"] = max(
            self.cumulative["max_arm_movement"], self.current_data.arm_movement
        )
        self.cumulative["max_leg_movement"] = max(
            self.cumulative["max_leg_movement"], self.current_data.leg_movement
        )
        self.cumulative["max_head_movement"] = max(
            self.cumulative["max_head_movement"], self.current_data.head_movement
        )

        for key in [
            "avg_people",
            "avg_total_movement",
            "avg_arm_movement",
            "avg_leg_movement",
            "avg_head_movement",
            "max_total_movement",
            "max_arm_movement",
            "max_leg_movement",
            "max_head_movement",
        ]:
            self.cumulative[key] = round(self.cumulative[key], 2)

    # WebSocket helpers -----------------------------------------------
    def add_client(self, ws: WebSocket):
        self.clients.add(ws)

    def remove_client(self, ws: WebSocket):
        self.clients.discard(ws)

    async def broadcast_async(self, payload: Dict):
        dead: List[WebSocket] = []
        for ws in list(self.clients):
            try:
                await ws.send_json({"type": "update", "data": payload})
            except RuntimeError:
                dead.append(ws)
            except WebSocketDisconnect:
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)

    def broadcast(self, payload: Dict):
        if not self.loop:
            return
        asyncio.run_coroutine_threadsafe(self.broadcast_async(payload), self.loop)


def create_app(state: DashboardState) -> FastAPI:
    base_dir = Path(__file__).resolve().parent.parent
    static_dir = base_dir / "static"
    template_dir = base_dir / "templates"

    app = FastAPI(title="Dance Dashboard (FastAPI)")
    templates = Jinja2Templates(directory=str(template_dir))
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.on_event("startup")
    async def _startup():
        loop = asyncio.get_running_loop()
        state.attach_loop(loop)
        state.start_osc(app.state.osc_port)

    @app.on_event("shutdown")
    async def _shutdown():
        state.stop_osc()

    @app.get("/")
    async def index(request: Request):
        return templates.TemplateResponse("dashboard.html", {"request": request})

    @app.get("/api/current")
    async def api_current():
        return JSONResponse(state.snapshot())

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        state.add_client(websocket)
        try:
            await websocket.send_json({"type": "update", "data": state.snapshot()})
            while True:
                message = await websocket.receive_text()
                try:
                    payload = json.loads(message)
                except json.JSONDecodeError:
                    continue
                action = payload.get("action")
                if action == "reset":
                    data = state.reset_stats()
                    await state.broadcast_async(data)
        except WebSocketDisconnect:
            pass
        finally:
            state.remove_client(websocket)

    return app


def main():
    parser = argparse.ArgumentParser(description="FastAPI Dance Dashboard")
    parser.add_argument("--osc-port", type=int, default=5005, help="OSC listen port")
    parser.add_argument("--web-port", type=int, default=8082, help="Web server port")
    parser.add_argument("--history", type=int, default=100, help="History length")
    args = parser.parse_args()

    state = DashboardState(history_size=args.history)
    app = create_app(state)
    app.state.osc_port = args.osc_port

    uvicorn.run(app, host="0.0.0.0", port=args.web_port)


if __name__ == "__main__":
    main()
