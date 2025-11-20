#!/usr/bin/env python3
"""
Dance Movement Dashboard
Real-time web dashboard for visualizing dance movement data from OSC messages
"""

from flask import Flask, render_template
from flask_socketio import SocketIO
from pythonosc import dispatcher, osc_server
import threading
import time
import json
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime
import argparse


@dataclass
class MovementData:
    """Movement data point"""
    timestamp: float
    person_count: int = 0
    total_movement: float = 0.0
    arm_movement: float = 0.0
    leg_movement: float = 0.0
    head_movement: float = 0.0

    def to_dict(self):
        return {
            'timestamp': self.timestamp,
            'datetime': datetime.fromtimestamp(self.timestamp).strftime('%H:%M:%S'),
            'person_count': self.person_count,
            'total_movement': round(self.total_movement, 2),
            'arm_movement': round(self.arm_movement, 2),
            'leg_movement': round(self.leg_movement, 2),
            'head_movement': round(self.head_movement, 2)
        }


class DashboardServer:
    """Main dashboard server combining OSC receiver and web server"""

    def __init__(self, osc_port: int, web_port: int, history_size: int = 100):
        self.osc_port = osc_port
        self.web_port = web_port
        self.history_size = history_size

        # Data storage
        self.history = deque(maxlen=history_size)
        self.current_data = MovementData(timestamp=time.time())
        self.lock = threading.Lock()

        # Broadcast throttling (to avoid sending multiple updates per second)
        self.last_broadcast_time = 0
        self.min_broadcast_interval = 0.1  # Minimum 0.1 seconds between broadcasts (10 Hz max)
        self.pending_broadcast = False
        self.data_updated = False

        # Keep track of which OSC fields have been refreshed since the last
        # broadcast so we only emit once the detector reported all metrics.
        self.required_fields = {
            'person_count',
            'total_movement',
            'arm_movement',
            'leg_movement',
            'head_movement'
        }
        self.updated_fields = set()

        # Cumulative statistics
        self.cumulative_stats = {
            'total_messages': 0,
            'avg_people': 0.0,
            'max_people': 0,
            'avg_total_movement': 0.0,
            'avg_arm_movement': 0.0,
            'avg_leg_movement': 0.0,
            'avg_head_movement': 0.0,
            'max_total_movement': 0.0,
            'max_arm_movement': 0.0,
            'max_leg_movement': 0.0,
            'max_head_movement': 0.0,
            'start_time': time.time()
        }

        # Flask app
        self.app = Flask(__name__,
                         template_folder='../templates',
                         static_folder='../static')
        self.app.config['SECRET_KEY'] = 'dance-movement-secret'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")

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

        self.osc_dispatcher.map(f"{base}/person_count", self._handle_person_count)
        self.osc_dispatcher.map(f"{base}/total_movement", self._handle_total_movement)
        self.osc_dispatcher.map(f"{base}/arm_movement", self._handle_arm_movement)
        self.osc_dispatcher.map(f"{base}/leg_movement", self._handle_leg_movement)
        self.osc_dispatcher.map(f"{base}/head_movement", self._handle_head_movement)

    def _handle_person_count(self, address, *args):
        with self.lock:
            self.current_data.person_count = int(args[0]) if args else 0
            self.updated_fields.add('person_count')
            self._check_complete_message()

    def _handle_total_movement(self, address, *args):
        with self.lock:
            self.current_data.total_movement = float(args[0]) if args else 0.0
            self.updated_fields.add('total_movement')
            self._check_complete_message()

    def _handle_arm_movement(self, address, *args):
        with self.lock:
            self.current_data.arm_movement = float(args[0]) if args else 0.0
            self.updated_fields.add('arm_movement')
            self._check_complete_message()

    def _handle_leg_movement(self, address, *args):
        with self.lock:
            self.current_data.leg_movement = float(args[0]) if args else 0.0
            self.updated_fields.add('leg_movement')
            self._check_complete_message()

    def _handle_head_movement(self, address, *args):
        with self.lock:
            self.current_data.head_movement = float(args[0]) if args else 0.0
            self.updated_fields.add('head_movement')
            self._check_complete_message()

    def _check_complete_message(self):
        """Check if we have a complete set of data and broadcast it with throttling"""
        current_time = time.time()

        # Update timestamp
        self.current_data.timestamp = current_time

        # Skip broadcasting until all required metrics were updated to
        # avoid emitting stale/partial data when OSC messages arrive
        # sequentially within the same batch.
        if not self.required_fields.issubset(self.updated_fields):
            return

        # Throttle broadcasts to avoid sending multiple updates per second
        time_since_last_broadcast = current_time - self.last_broadcast_time

        if time_since_last_broadcast >= self.min_broadcast_interval:
            # Enough time has passed, broadcast now
            self._update_cumulative_stats()
            self._broadcast_update()
            self.last_broadcast_time = current_time
            self.pending_broadcast = False

            print(f"[{datetime.fromtimestamp(current_time).strftime('%H:%M:%S')}] "
                  f"People: {self.current_data.person_count} | "
                  f"Total: {self.current_data.total_movement:.1f} | "
                  f"Arms: {self.current_data.arm_movement:.1f} | "
                  f"Legs: {self.current_data.leg_movement:.1f} | "
                  f"Head: {self.current_data.head_movement:.1f}")
        else:
            # Too soon, will broadcast on next eligible message
            pass

    def _broadcast_update(self):
        """Broadcast current state to all connected clients"""
        # Add to history
        data_dict = self.current_data.to_dict()
        self.history.append(data_dict)

        # Prepare update message
        update_msg = {
            'current': data_dict,
            'cumulative': self.cumulative_stats,
            'history': list(self.history)
        }

        # Broadcast to web clients
        self.socketio.emit('update', update_msg)
        print(f"[WebSocket] Broadcast sent to clients (history: {len(self.history)} items)")

        # Reset tracker so the next OSC batch must refresh all metrics again
        self.updated_fields.clear()

    def _update_cumulative_stats(self):
        """Update cumulative statistics"""
        self.cumulative_stats['total_messages'] += 1
        n = self.cumulative_stats['total_messages']

        # Update averages (running average)
        self.cumulative_stats['avg_people'] += \
            (self.current_data.person_count - self.cumulative_stats['avg_people']) / n
        self.cumulative_stats['avg_total_movement'] += \
            (self.current_data.total_movement - self.cumulative_stats['avg_total_movement']) / n
        self.cumulative_stats['avg_arm_movement'] += \
            (self.current_data.arm_movement - self.cumulative_stats['avg_arm_movement']) / n
        self.cumulative_stats['avg_leg_movement'] += \
            (self.current_data.leg_movement - self.cumulative_stats['avg_leg_movement']) / n
        self.cumulative_stats['avg_head_movement'] += \
            (self.current_data.head_movement - self.cumulative_stats['avg_head_movement']) / n

        # Update maximums
        self.cumulative_stats['max_people'] = max(
            self.cumulative_stats['max_people'],
            self.current_data.person_count
        )
        self.cumulative_stats['max_total_movement'] = max(
            self.cumulative_stats['max_total_movement'],
            self.current_data.total_movement
        )
        self.cumulative_stats['max_arm_movement'] = max(
            self.cumulative_stats['max_arm_movement'],
            self.current_data.arm_movement
        )
        self.cumulative_stats['max_leg_movement'] = max(
            self.cumulative_stats['max_leg_movement'],
            self.current_data.leg_movement
        )
        self.cumulative_stats['max_head_movement'] = max(
            self.cumulative_stats['max_head_movement'],
            self.current_data.head_movement
        )

        # Round for display
        for key in ['avg_people', 'avg_total_movement', 'avg_arm_movement', 'avg_leg_movement',
                    'avg_head_movement', 'max_total_movement', 'max_arm_movement',
                    'max_leg_movement', 'max_head_movement']:
            self.cumulative_stats[key] = round(self.cumulative_stats[key], 2)

    def setup_flask_routes(self):
        """Setup Flask routes"""
        @self.app.route('/')
        def index():
            response = render_template('dashboard.html')
            # Disable caching to ensure fresh content
            from flask import make_response
            resp = make_response(response)
            resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            resp.headers['Pragma'] = 'no-cache'
            resp.headers['Expires'] = '0'
            return resp

        @self.app.route('/test')
        def test():
            from flask import send_from_directory
            import os
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            return send_from_directory(base_dir, 'test_websocket.html')

        @self.app.route('/api/current')
        def api_current():
            with self.lock:
                return {
                    'current': self.current_data.to_dict(),
                    'cumulative': self.cumulative_stats,
                    'history': list(self.history)
                }

        @self.socketio.on('connect')
        def handle_connect():
            print('Client connected')
            # Send current data to newly connected client
            with self.lock:
                self.socketio.emit('update', {
                    'current': self.current_data.to_dict(),
                    'cumulative': self.cumulative_stats,
                    'history': list(self.history)
                })

        @self.socketio.on('disconnect')
        def handle_disconnect():
            print('Client disconnected')

        @self.socketio.on('reset_stats')
        def handle_reset():
            """Reset cumulative statistics"""
            with self.lock:
                self.cumulative_stats = {
                    'total_messages': 0,
                    'avg_people': 0.0,
                    'max_people': 0,
                    'avg_total_movement': 0.0,
                    'avg_arm_movement': 0.0,
                    'avg_leg_movement': 0.0,
                    'avg_head_movement': 0.0,
                    'max_total_movement': 0.0,
                    'max_arm_movement': 0.0,
                    'max_leg_movement': 0.0,
                    'max_head_movement': 0.0,
                    'start_time': time.time()
                }
                self.history.clear()
                self.updated_fields.clear()
                print('Statistics reset')

                # Prepare reset data
                reset_data = {
                    'current': self.current_data.to_dict(),
                    'cumulative': self.cumulative_stats,
                    'history': list(self.history)
                }

                # Broadcast the reset to all clients (include initiator)
                self.socketio.emit('update', reset_data)
                print('[WebSocket] Reset broadcast sent to all clients')

                # Return data so Socket.IO acknowledgements update the caller
                return reset_data

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
        print(f"Web dashboard starting on http://localhost:{self.web_port}")
        print(f"Open your browser to http://localhost:{self.web_port}")
        self.socketio.run(self.app, host='0.0.0.0', port=self.web_port, debug=False, allow_unsafe_werkzeug=True)

    def stop(self):
        """Stop servers"""
        if self.osc_server:
            self.osc_server.shutdown()


def main():
    parser = argparse.ArgumentParser(description='Dance Movement Dashboard')
    parser.add_argument('--osc-port', type=int, default=5005,
                        help='OSC listening port (default: 5005)')
    parser.add_argument('--web-port', type=int, default=8081,
                        help='Web dashboard port (default: 8081)')
    parser.add_argument('--history', type=int, default=100,
                        help='Number of data points to keep in history (default: 100)')

    args = parser.parse_args()

    print("=== Dance Movement Dashboard ===")
    print(f"OSC Port: {args.osc_port}")
    print(f"Web Port: {args.web_port}")
    print(f"History Size: {args.history}")
    print("\nStarting servers...\n")

    server = DashboardServer(
        osc_port=args.osc_port,
        web_port=args.web_port,
        history_size=args.history
    )

    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.stop()


if __name__ == '__main__':
    main()
