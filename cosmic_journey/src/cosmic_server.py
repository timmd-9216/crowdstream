#!/usr/bin/env python3
"""
Cosmic Journey Visualizer
Alternative space visualization with different visual style
"""

from flask import Flask, render_template, make_response
from flask_socketio import SocketIO
from pythonosc import dispatcher, osc_server
import threading
import time
import json
from datetime import datetime
import argparse


class CosmicState(object):
    """Current state of the cosmic visualizer - Python 3.5 compatible"""

    def __init__(self):
        # Movement data
        self.person_count = 0
        self.total_movement = 0.0
        self.arm_movement = 0.0
        self.leg_movement = 0.0
        self.head_movement = 0.0
        self.timestamp = 0.0

        # Visualization parameters
        self.galaxy_rotation = 0.0      # Galaxy spiral rotation
        self.nebula_density = 0.0       # Nebula cloud density
        self.asteroid_speed = 1.0       # Asteroid field speed
        self.cosmic_zoom = 1.0          # Camera zoom level
        self.star_brightness = 0.5      # Overall brightness
        self.planet_orbit_speed = 0.0   # Planet orbital speed
        self.cosmic_energy = 0.0        # Energy field intensity

    def to_dict(self):
        return {
            'person_count': self.person_count,
            'total_movement': round(self.total_movement, 2),
            'arm_movement': round(self.arm_movement, 2),
            'leg_movement': round(self.leg_movement, 2),
            'head_movement': round(self.head_movement, 2),
            'timestamp': self.timestamp,
            'galaxy_rotation': round(self.galaxy_rotation, 3),
            'nebula_density': round(self.nebula_density, 3),
            'asteroid_speed': round(self.asteroid_speed, 3),
            'cosmic_zoom': round(self.cosmic_zoom, 3),
            'star_brightness': round(self.star_brightness, 3),
            'planet_orbit_speed': round(self.planet_orbit_speed, 3),
            'cosmic_energy': round(self.cosmic_energy, 3)
        }


class CosmicVisualizerServer(object):
    """Server for cosmic journey visualization"""

    def __init__(self, osc_port, web_port):
        self.osc_port = osc_port
        self.web_port = web_port

        # Current state
        self.state = CosmicState()
        self.lock = threading.Lock()

        # Broadcast throttling
        self.last_broadcast_time = 0
        self.min_broadcast_interval = 0.1  # 10 Hz max

        # Flask app
        self.app = Flask(__name__,
                         template_folder='../templates',
                         static_folder='../static')
        self.app.config['SECRET_KEY'] = 'cosmic-visualizer-secret'
        # Use threading mode for Python 3.5 / Jetson TX1 compatibility
        self.socketio = SocketIO(self.app, async_mode='threading', cors_allowed_origins="*")

        # OSC dispatcher
        self.osc_dispatcher = dispatcher.Dispatcher()
        self.setup_osc_handlers()
        self.setup_flask_routes()

        # Threads
        self.osc_thread = None
        self.osc_server = None

    def setup_osc_handlers(self):
        """Setup OSC message handlers"""
        base = "/dance"

        self.osc_dispatcher.map("{}/person_count".format(base), self._handle_person_count)
        self.osc_dispatcher.map("{}/total_movement".format(base), self._handle_total_movement)
        self.osc_dispatcher.map("{}/arm_movement".format(base), self._handle_arm_movement)
        self.osc_dispatcher.map("{}/leg_movement".format(base), self._handle_leg_movement)
        self.osc_dispatcher.map("{}/head_movement".format(base), self._handle_head_movement)

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
        """Map movement data to cosmic visualization parameters"""
        self.state.timestamp = time.time()

        # Galaxy rotation: driven by leg movement (0-3 rad/s)
        self.state.galaxy_rotation = min(self.state.leg_movement / 30.0, 3.0)

        # Nebula density: driven by total movement (0-1)
        self.state.nebula_density = min(self.state.total_movement / 100.0, 1.0)

        # Asteroid speed: driven by arm movement (0.5-10)
        self.state.asteroid_speed = 0.5 + min(self.state.arm_movement / 10.0, 9.5)

        # Cosmic zoom: driven by head movement (0.5-3.0)
        self.state.cosmic_zoom = 0.5 + min(self.state.head_movement / 20.0, 2.5)

        # Star brightness: driven by total movement (0.2-1.0)
        self.state.star_brightness = 0.2 + min(self.state.total_movement / 125.0, 0.8)

        # Planet orbit speed: driven by arm + leg movement (0-2)
        combined = (self.state.arm_movement + self.state.leg_movement) / 2.0
        self.state.planet_orbit_speed = min(combined / 50.0, 2.0)

        # Cosmic energy: driven by total movement with boost (0-1)
        self.state.cosmic_energy = min(self.state.total_movement / 80.0, 1.0)

        # Throttle broadcasts
        current_time = self.state.timestamp
        time_since_last_broadcast = current_time - self.last_broadcast_time

        if time_since_last_broadcast >= self.min_broadcast_interval:
            state_dict = self.state.to_dict()
            self.socketio.emit('update', state_dict)
            self.last_broadcast_time = current_time

            print("[{}] Galaxy: {:.2f} | Asteroids: {:.2f} | Energy: {:.2f} | Zoom: {:.2f}".format(
                datetime.fromtimestamp(self.state.timestamp).strftime('%H:%M:%S'),
                self.state.galaxy_rotation,
                self.state.asteroid_speed,
                self.state.cosmic_energy,
                self.state.cosmic_zoom))

    def setup_flask_routes(self):
        """Setup Flask routes"""
        @self.app.route('/')
        def index():
            response = render_template('cosmic.html')
            resp = make_response(response)
            resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            resp.headers['Pragma'] = 'no-cache'
            resp.headers['Expires'] = '0'
            return resp

        @self.app.route('/api/state')
        def api_state():
            with self.lock:
                return self.state.to_dict()

        @self.socketio.on('connect')
        def handle_connect():
            print('[OK] Client connected to cosmic visualizer')
            with self.lock:
                state_dict = self.state.to_dict()
                self.socketio.emit('update', state_dict)

        @self.socketio.on('disconnect')
        def handle_disconnect():
            print('[X] Client disconnected from cosmic visualizer')

    def start_osc_server(self):
        """Start OSC server in separate thread"""
        self.osc_server = osc_server.ThreadingOSCUDPServer(
            ('0.0.0.0', self.osc_port),
            self.osc_dispatcher
        )
        print("OSC server listening on port {}".format(self.osc_port))
        self.osc_server.serve_forever()

    def start(self):
        """Start both OSC and web servers"""
        self.osc_thread = threading.Thread(target=self.start_osc_server, daemon=True)
        self.osc_thread.start()

        print("Cosmic visualizer starting on http://localhost:{}".format(self.web_port))
        print("Open your browser to http://localhost:{}".format(self.web_port))
        print("\nVisualization mapping:")
        print("  - Leg movement -> Galaxy rotation")
        print("  - Arm movement -> Asteroid speed")
        print("  - Head movement -> Cosmic zoom")
        print("  - Total movement -> Energy & Nebula")
        print("  - Person count -> (future: multiple galaxies)")
        print()
        self.socketio.run(self.app, host='0.0.0.0', port=self.web_port, debug=False, allow_unsafe_werkzeug=True)

    def stop(self):
        """Stop servers"""
        if self.osc_server:
            self.osc_server.shutdown()


def main():
    parser = argparse.ArgumentParser(description='Cosmic Journey Visualizer')
    parser.add_argument('--osc-port', type=int, default=5007,
                        help='OSC listening port (default: 5007)')
    parser.add_argument('--web-port', type=int, default=8091,
                        help='Web visualizer port (default: 8091)')

    args = parser.parse_args()

    print("=== Cosmic Journey Visualizer ===")
    print("OSC Port: {}".format(args.osc_port))
    print("Web Port: {}".format(args.web_port))
    print("\nStarting servers...\n")

    server = CosmicVisualizerServer(
        osc_port=args.osc_port,
        web_port=args.web_port
    )

    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.stop()


if __name__ == '__main__':
    main()
