#!/usr/bin/env python3
"""
Space Journey Visualizer
Real-time space visualization driven by dance movement data via OSC
"""

from flask import Flask, render_template
from flask_socketio import SocketIO
from pythonosc import dispatcher, osc_server
import threading
import time
import json
from dataclasses import dataclass
from datetime import datetime
import argparse


@dataclass
class VisualizerState:
    """Current state of the visualizer"""
    person_count: int = 0
    total_movement: float = 0.0
    arm_movement: float = 0.0
    leg_movement: float = 0.0
    head_movement: float = 0.0
    timestamp: float = 0.0

    # Derived parameters for visualization
    speed: float = 1.0          # Travel speed through space
    particle_count: int = 1000  # Number of stars/particles
    color_intensity: float = 0.5  # Color vibrancy
    rotation_speed: float = 0.0   # Camera rotation
    warp_factor: float = 0.0      # Warp drive effect
    nebula_intensity: float = 0.0 # Nebula clouds
    star_size: float = 1.0        # Star size multiplier

    def to_dict(self):
        return {
            'person_count': self.person_count,
            'total_movement': round(self.total_movement, 2),
            'arm_movement': round(self.arm_movement, 2),
            'leg_movement': round(self.leg_movement, 2),
            'head_movement': round(self.head_movement, 2),
            'timestamp': self.timestamp,
            'speed': round(self.speed, 3),
            'particle_count': self.particle_count,
            'color_intensity': round(self.color_intensity, 3),
            'rotation_speed': round(self.rotation_speed, 3),
            'warp_factor': round(self.warp_factor, 3),
            'nebula_intensity': round(self.nebula_intensity, 3),
            'star_size': round(self.star_size, 3)
        }


class SpaceVisualizerServer:
    """Server that receives OSC and broadcasts to web visualizer"""

    def __init__(self, osc_port: int, web_port: int, mapping_file: str = None):
        self.osc_port = osc_port
        self.web_port = web_port

        # Load mapping configuration
        self.mapping = self._load_mapping(mapping_file)

        # Current state
        self.state = VisualizerState()
        self.lock = threading.Lock()

        # Flask app
        self.app = Flask(__name__,
                         template_folder='../templates',
                         static_folder='../static')
        self.app.config['SECRET_KEY'] = 'space-visualizer-secret'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")

        # OSC dispatcher
        self.osc_dispatcher = dispatcher.Dispatcher()
        self.setup_osc_handlers()
        self.setup_flask_routes()

        # Threads
        self.osc_thread = None
        self.osc_server = None

    def _load_mapping(self, mapping_file: str = None):
        """Load mapping configuration from JSON file"""
        if mapping_file is None:
            mapping_file = 'config/mapping.json'

        try:
            # Try to load from file
            from pathlib import Path
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / mapping_file

            with open(config_path, 'r') as f:
                mapping = json.load(f)
            print(f"Loaded mapping configuration from {mapping_file}")
            return mapping
        except Exception as e:
            print(f"Warning: Could not load mapping file ({e}), using defaults")
            # Return default mapping
            return {
                "mappings": {
                    "speed": {"source": "arm_movement", "min_input": 0, "max_input": 80, "min_output": 0.5, "max_output": 10.0},
                    "star_size": {"source": "head_movement", "min_input": 0, "max_input": 60, "min_output": 1.0, "max_output": 4.0},
                    "rotation_speed": {"source": "leg_movement", "min_input": 0, "max_input": 100, "min_output": 0.0, "max_output": 3.0},
                    "color_intensity": {"source": "total_movement", "min_input": 0, "max_input": 100, "min_output": 0.2, "max_output": 1.0},
                    "warp_factor": {"source": "total_movement", "min_input": 0, "max_input": 150, "min_output": 0.0, "max_output": 1.0},
                    "particle_count": {"source": "person_count", "base": 500, "multiplier": 500, "min_output": 500, "max_output": 5000}
                }
            }

    def _apply_mapping(self, param_name: str, value: float) -> float:
        """Apply mapping configuration to a parameter"""
        if param_name not in self.mapping.get("mappings", {}):
            return value

        config = self.mapping["mappings"][param_name]

        # Handle particle_count special case (multiplicative)
        if "multiplier" in config:
            result = config.get("base", 0) + (value * config["multiplier"])
            return min(max(result, config["min_output"]), config["max_output"])

        # Handle standard linear mapping
        min_in = config["min_input"]
        max_in = config["max_input"]
        min_out = config["min_output"]
        max_out = config["max_output"]

        # Normalize input
        normalized = min(value / max_in, 1.0) if max_in > 0 else 0.0

        # Map to output range
        result = min_out + (normalized * (max_out - min_out))
        return result

    def setup_osc_handlers(self):
        """Setup OSC message handlers"""
        base = "/dance"

        self.osc_dispatcher.map(f"{base}/person_count", self._handle_person_count)
        self.osc_dispatcher.map(f"{base}/total_movement", self._handle_total_movement)
        self.osc_dispatcher.map(f"{base}/arm_movement", self._handle_arm_movement)
        self.osc_dispatcher.map(f"{base}/leg_movement", self._handle_leg_movement)
        self.osc_dispatcher.map(f"{base}/head_movement", self._handle_head_movement)

    def _handle_person_count(self, address, *args):
        with self.lock:
            self.state.person_count = int(args[0]) if args else 0
            self._update_visualization_params()

    def _handle_total_movement(self, address, *args):
        with self.lock:
            self.state.total_movement = float(args[0]) if args else 0.0
            self._update_visualization_params()

    def _handle_arm_movement(self, address, *args):
        with self.lock:
            self.state.arm_movement = float(args[0]) if args else 0.0
            self._update_visualization_params()

    def _handle_leg_movement(self, address, *args):
        with self.lock:
            self.state.leg_movement = float(args[0]) if args else 0.0
            self._update_visualization_params()

    def _handle_head_movement(self, address, *args):
        with self.lock:
            self.state.head_movement = float(args[0]) if args else 0.0
            self._update_visualization_params()

    def _update_visualization_params(self):
        """Map movement data to visualization parameters using configuration"""
        self.state.timestamp = time.time()

        # Get source values
        sources = {
            'arm_movement': self.state.arm_movement,
            'leg_movement': self.state.leg_movement,
            'head_movement': self.state.head_movement,
            'total_movement': self.state.total_movement,
            'person_count': self.state.person_count
        }

        # Apply mappings based on configuration
        mappings = self.mapping.get("mappings", {})

        # Speed
        if "speed" in mappings:
            source = mappings["speed"]["source"]
            self.state.speed = self._apply_mapping("speed", sources.get(source, 0))

        # Particle count
        if "particle_count" in mappings:
            source = mappings["particle_count"]["source"]
            self.state.particle_count = int(self._apply_mapping("particle_count", sources.get(source, 0)))

        # Color intensity
        if "color_intensity" in mappings:
            source = mappings["color_intensity"]["source"]
            self.state.color_intensity = self._apply_mapping("color_intensity", sources.get(source, 0))

        # Rotation speed
        if "rotation_speed" in mappings:
            source = mappings["rotation_speed"]["source"]
            self.state.rotation_speed = self._apply_mapping("rotation_speed", sources.get(source, 0))

        # Star size
        if "star_size" in mappings:
            source = mappings["star_size"]["source"]
            self.state.star_size = self._apply_mapping("star_size", sources.get(source, 0))

        # Warp factor
        if "warp_factor" in mappings:
            source = mappings["warp_factor"]["source"]
            self.state.warp_factor = self._apply_mapping("warp_factor", sources.get(source, 0))

        # Nebula intensity (special case: average of multiple sources)
        if "nebula_intensity" in mappings:
            nebula_config = mappings["nebula_intensity"]
            if nebula_config.get("source") == "average" and "sources" in nebula_config:
                avg_value = sum(sources.get(s, 0) for s in nebula_config["sources"]) / len(nebula_config["sources"])
                self.state.nebula_intensity = self._apply_mapping("nebula_intensity", avg_value)
            else:
                source = nebula_config.get("source", "total_movement")
                self.state.nebula_intensity = self._apply_mapping("nebula_intensity", sources.get(source, 0))

        # Broadcast to clients
        self.socketio.emit('update', self.state.to_dict())

        print(f"[{datetime.fromtimestamp(self.state.timestamp).strftime('%H:%M:%S')}] "
              f"Speed: {self.state.speed:.2f} | "
              f"StarSize: {self.state.star_size:.2f} | "
              f"Rotation: {self.state.rotation_speed:.2f} | "
              f"Color: {self.state.color_intensity:.2f}")

    def setup_flask_routes(self):
        """Setup Flask routes"""
        @self.app.route('/')
        def index():
            return render_template('visualizer.html')

        @self.app.route('/api/state')
        def api_state():
            with self.lock:
                return self.state.to_dict()

        @self.socketio.on('connect')
        def handle_connect():
            print('Client connected to visualizer')
            # Send current state to newly connected client
            with self.lock:
                self.socketio.emit('update', self.state.to_dict())

        @self.socketio.on('disconnect')
        def handle_disconnect():
            print('Client disconnected from visualizer')

    def start_osc_server(self):
        """Start OSC server in separate thread"""
        self.osc_server = osc_server.ThreadingOSCUDPServer(
            ('0.0.0.0', self.osc_port),
            self.osc_dispatcher
        )
        print(f"OSC server listening on port {self.osc_port}")
        self.osc_server.serve_forever()

    def start(self):
        """Start both OSC and web servers"""
        # Start OSC server in background thread
        self.osc_thread = threading.Thread(target=self.start_osc_server, daemon=True)
        self.osc_thread.start()

        # Start web server
        print(f"Space visualizer starting on http://localhost:{self.web_port}")
        print(f"Open your browser to http://localhost:{self.web_port}")
        print("\nVisualization mapping:")
        print("  - Arm movement → Travel speed")
        print("  - Head movement → Star size")
        print("  - Leg movement → Camera rotation")
        print("  - Total movement → Color intensity & Warp")
        print("  - Person count → Star density")
        print()
        self.socketio.run(self.app, host='0.0.0.0', port=self.web_port, debug=False)

    def stop(self):
        """Stop servers"""
        if self.osc_server:
            self.osc_server.shutdown()


def main():
    parser = argparse.ArgumentParser(description='Space Journey Visualizer')
    parser.add_argument('--osc-port', type=int, default=5005,
                        help='OSC listening port (default: 5005)')
    parser.add_argument('--web-port', type=int, default=8090,
                        help='Web visualizer port (default: 8090)')
    parser.add_argument('--mapping', type=str, default='config/mapping.json',
                        help='Mapping configuration file (default: config/mapping.json)')

    args = parser.parse_args()

    print("=== Space Journey Visualizer ===")
    print(f"OSC Port: {args.osc_port}")
    print(f"Web Port: {args.web_port}")
    print(f"Mapping File: {args.mapping}")
    print("\nStarting servers...\n")

    server = SpaceVisualizerServer(
        osc_port=args.osc_port,
        web_port=args.web_port,
        mapping_file=args.mapping
    )

    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.stop()


if __name__ == '__main__':
    main()
