#!/usr/bin/env python3
"""
Service Controller - Remote management system for all dance movement services
Provides web interface to start, stop, restart and monitor services
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import subprocess
import threading
import time
import json
import os
import signal
import psutil
from pathlib import Path
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Dict, Optional, List
import argparse


@dataclass
class ServiceConfig:
    """Configuration for a managed service"""
    name: str
    directory: str
    command: str
    description: str
    port: int
    auto_restart: bool = False
    enabled: bool = True
    monitor_ports: List[int] = field(default_factory=list)


@dataclass
class ServiceStatus:
    """Status of a managed service"""
    name: str
    status: str  # stopped, starting, running, stopping, error
    pid: Optional[int] = None
    uptime: float = 0.0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    last_started: Optional[float] = None
    last_stopped: Optional[float] = None
    restart_count: int = 0
    error_message: Optional[str] = None
    port: int = 0
    logs: List[str] = None
    managed: bool = False

    def __post_init__(self):
        if self.logs is None:
            self.logs = []

    def to_dict(self):
        data = asdict(self)
        if self.last_started:
            data['last_started_str'] = datetime.fromtimestamp(self.last_started).strftime('%Y-%m-%d %H:%M:%S')
        if self.last_stopped:
            data['last_stopped_str'] = datetime.fromtimestamp(self.last_stopped).strftime('%Y-%m-%d %H:%M:%S')
        data['uptime_str'] = self._format_uptime(self.uptime)
        return data

    def _format_uptime(self, seconds):
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds/60)}m {int(seconds%60)}s"
        else:
            hours = int(seconds/3600)
            minutes = int((seconds%3600)/60)
            return f"{hours}h {minutes}m"


class ServiceManager:
    """Manages multiple services with process monitoring"""

    def __init__(self, config_path: str, base_dir: str):
        self.base_dir = Path(base_dir)
        self.services: Dict[str, ServiceConfig] = {}
        self.statuses: Dict[str, ServiceStatus] = {}
        self.processes: Dict[str, subprocess.Popen] = {}
        self.log_threads: Dict[str, threading.Thread] = {}
        self.stop_flags: Dict[str, bool] = {}

        self.load_config(config_path)
        self.monitoring_thread = None
        self.monitoring_active = False

    def _get_ports_to_monitor(self, service: ServiceConfig) -> List[int]:
        return [port for port in service.monitor_ports if port]

    def _find_pid_for_port(self, port: int) -> Optional[int]:
        if not port:
            return None
        for proto in ('TCP', 'UDP'):
            try:
                output = subprocess.check_output(
                    ['lsof', '-nP', f'-ti{proto}:{port}'],
                    stderr=subprocess.DEVNULL
                ).decode().strip()
                if output:
                    for line in output.splitlines():
                        line = line.strip()
                        if line.isdigit():
                            return int(line)
            except subprocess.CalledProcessError:
                continue
            except FileNotFoundError:
                # lsof not available
                break
        return None

    def _find_pid_for_service(self, service: ServiceConfig) -> Optional[int]:
        for port in self._get_ports_to_monitor(service):
            pid = self._find_pid_for_port(port)
            if pid:
                return pid
        return None

    def _attach_external_process(self, service_name: str, pid: int):
        status = self.statuses[service_name]
        status.status = 'running'
        status.pid = pid
        status.managed = False
        status.error_message = None
        if not status.last_started:
            status.last_started = time.time()
        print(f"Service {service_name} already running externally (PID {pid})")

    def load_config(self, config_path: str):
        """Load service configurations from JSON file"""
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)

            for service_data in config_data['services']:
                service = ServiceConfig(**service_data)
                # Ensure primary port is monitored even if monitor_ports not defined
                if service.port and service.port not in service.monitor_ports:
                    service.monitor_ports.append(service.port)
                # Remove duplicates while preserving order
                service.monitor_ports = list(dict.fromkeys(service.monitor_ports))

                self.services[service.name] = service
                self.statuses[service.name] = ServiceStatus(
                    name=service.name,
                    status='stopped',
                    port=service.port
                )
                self.stop_flags[service.name] = False

            print(f"Loaded {len(self.services)} service configurations")

        except Exception as e:
            print(f"Error loading config: {e}")
            raise

    def start_service(self, service_name: str) -> bool:
        """Start a service"""
        if service_name not in self.services:
            return False

        if self.statuses[service_name].status == 'running':
            print(f"Service {service_name} is already running")
            return False

        service = self.services[service_name]
        if not service.enabled:
            print(f"Service {service_name} is disabled")
            return False

        try:
            existing_pid = self._find_pid_for_service(service)
            if existing_pid:
                self._attach_external_process(service_name, existing_pid)
                return True

            self.statuses[service_name].status = 'starting'
            self.statuses[service_name].error_message = None
            self.statuses[service_name].logs = []
            self.stop_flags[service_name] = False

            # Change to service directory
            service_dir = self.base_dir / service.directory

            if not service_dir.exists():
                raise Exception(f"Service directory not found: {service_dir}")

            # Start process
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'  # Disable Python output buffering

            process = subprocess.Popen(
                service.command,
                shell=True,
                cwd=str(service_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                preexec_fn=os.setsid  # Create new process group
            )

            self.processes[service_name] = process

            # Start log monitoring thread
            log_thread = threading.Thread(
                target=self._monitor_logs,
                args=(service_name,),
                daemon=True
            )
            log_thread.start()
            self.log_threads[service_name] = log_thread

            # Wait a bit to check if process started successfully
            time.sleep(2)

            if process.poll() is not None:
                # Process already died
                raise Exception(f"Process exited immediately with code {process.returncode}")

            self.statuses[service_name].status = 'running'
            self.statuses[service_name].pid = process.pid
            self.statuses[service_name].last_started = time.time()
            self.statuses[service_name].restart_count += 1
            self.statuses[service_name].managed = True

            print(f"Service {service_name} started with PID {process.pid}")
            return True

        except Exception as e:
            self.statuses[service_name].status = 'error'
            self.statuses[service_name].error_message = str(e)
            print(f"Error starting service {service_name}: {e}")
            return False

    def stop_service(self, service_name: str) -> bool:
        """Stop a service"""
        if service_name not in self.services:
            return False

        if self.statuses[service_name].status == 'stopped':
            print(f"Service {service_name} is already stopped")
            return False

        try:
            self.statuses[service_name].status = 'stopping'
            self.stop_flags[service_name] = True

            if service_name in self.processes:
                process = self.processes[service_name]

                if process.poll() is None:  # Process is still running
                    # Try graceful shutdown first (SIGTERM to process group)
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        print(f"Sent SIGTERM to service {service_name} (PID {process.pid})")

                        # Wait up to 5 seconds for graceful shutdown
                        for _ in range(50):
                            if process.poll() is not None:
                                break
                            time.sleep(0.1)

                        # Force kill if still running
                        if process.poll() is None:
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                            print(f"Sent SIGKILL to service {service_name}")
                            time.sleep(0.5)

                    except Exception as e:
                        print(f"Error killing process: {e}")

                del self.processes[service_name]
            elif self.statuses[service_name].pid:
                pid = self.statuses[service_name].pid
                try:
                    os.kill(pid, signal.SIGTERM)
                    print(f"Sent SIGTERM to external process for {service_name} (PID {pid})")
                except ProcessLookupError:
                    print(f"Process {pid} already stopped")
                except Exception as e:
                    print(f"Error stopping external process: {e}")

            self.statuses[service_name].status = 'stopped'
            self.statuses[service_name].pid = None
            self.statuses[service_name].last_stopped = time.time()
            self.statuses[service_name].uptime = 0.0
            self.statuses[service_name].cpu_percent = 0.0
            self.statuses[service_name].memory_mb = 0.0
            self.statuses[service_name].managed = False

            print(f"Service {service_name} stopped")
            return True

        except Exception as e:
            self.statuses[service_name].status = 'error'
            self.statuses[service_name].error_message = str(e)
            print(f"Error stopping service {service_name}: {e}")
            return False

    def restart_service(self, service_name: str) -> bool:
        """Restart a service"""
        print(f"Restarting service {service_name}")
        self.stop_service(service_name)
        time.sleep(1)
        return self.start_service(service_name)

    def get_service_status(self, service_name: str) -> Optional[ServiceStatus]:
        """Get status of a specific service"""
        return self.statuses.get(service_name)

    def get_all_statuses(self) -> Dict[str, ServiceStatus]:
        """Get status of all services"""
        return self.statuses

    def _monitor_logs(self, service_name: str):
        """Monitor service logs in background thread"""
        process = self.processes.get(service_name)
        if not process:
            return

        try:
            for line in iter(process.stdout.readline, ''):
                if self.stop_flags[service_name]:
                    break

                if line:
                    line = line.rstrip()
                    # Keep last 100 log lines
                    logs = self.statuses[service_name].logs
                    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {line}")
                    if len(logs) > 100:
                        logs.pop(0)

        except Exception as e:
            print(f"Log monitoring error for {service_name}: {e}")

    def start_monitoring(self):
        """Start monitoring thread for all services"""
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitoring_thread.start()
        print("Service monitoring started")

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            for service_name in self.services:
                if service_name in self.processes:
                    process = self.processes[service_name]
                    status = self.statuses[service_name]

                    # Check if process is still alive
                    if process.poll() is not None:
                        # Process died
                        print(f"Service {service_name} died unexpectedly")
                        status.status = 'error'
                        status.error_message = f"Process exited with code {process.returncode}"
                        status.pid = None
                        del self.processes[service_name]

                        # Auto-restart if configured
                        if self.services[service_name].auto_restart:
                            print(f"Auto-restarting {service_name}")
                            time.sleep(2)
                            self.start_service(service_name)

                    else:
                        # Update process stats
                        try:
                            proc = psutil.Process(process.pid)
                            status.cpu_percent = proc.cpu_percent(interval=0.1)
                            status.memory_mb = proc.memory_info().rss / 1024 / 1024

                            if status.last_started:
                                status.uptime = time.time() - status.last_started

                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass

                else:
                    service = self.services[service_name]
                    status = self.statuses[service_name]

                    pid = self._find_pid_for_service(service)
                    if pid:
                        if status.status != 'running' or status.pid != pid:
                            self._attach_external_process(service_name, pid)
                        try:
                            proc = psutil.Process(pid)
                            status.cpu_percent = proc.cpu_percent(interval=0.1)
                            status.memory_mb = proc.memory_info().rss / 1024 / 1024
                            if status.last_started:
                                status.uptime = time.time() - status.last_started
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    else:
                        if status.status == 'running' and not status.managed:
                            status.status = 'stopped'
                            status.pid = None
                            status.uptime = 0

            time.sleep(1)

    def start_all(self):
        """Start all enabled services"""
        print("Starting all enabled services...")
        for service_name, service in self.services.items():
            if service.enabled:
                self.start_service(service_name)
                time.sleep(2)  # Stagger startups

    def stop_all(self):
        """Stop all running services"""
        print("Stopping all services...")
        self.monitoring_active = False
        for service_name in list(self.processes.keys()):
            self.stop_service(service_name)


class ControllerApp:
    """Flask application for service control"""

    def __init__(self, manager: ServiceManager, port: int):
        self.manager = manager
        self.port = port

        self.app = Flask(__name__,
                         template_folder='../templates',
                         static_folder='../static')
        self.app.config['SECRET_KEY'] = 'service-controller-secret'
        # Force threading async mode to avoid eventlet monkey-patching conflicts
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='threading')

        self.setup_routes()
        self.setup_socketio()

    def setup_routes(self):
        """Setup Flask routes"""

        @self.app.route('/')
        def index():
            return render_template('controller.html')

        @self.app.route('/api/services')
        def get_services():
            """Get all service configurations and statuses"""
            services_data = []
            for name, service in self.manager.services.items():
                status = self.manager.statuses[name]
                services_data.append({
                    'config': asdict(service),
                    'status': status.to_dict()
                })
            return jsonify(services_data)

        @self.app.route('/api/service/<service_name>/start', methods=['POST'])
        def start_service(service_name):
            success = self.manager.start_service(service_name)
            return jsonify({'success': success})

        @self.app.route('/api/service/<service_name>/stop', methods=['POST'])
        def stop_service(service_name):
            success = self.manager.stop_service(service_name)
            return jsonify({'success': success})

        @self.app.route('/api/service/<service_name>/restart', methods=['POST'])
        def restart_service(service_name):
            success = self.manager.restart_service(service_name)
            return jsonify({'success': success})

        @self.app.route('/api/service/<service_name>/logs')
        def get_logs(service_name):
            status = self.manager.get_service_status(service_name)
            if status:
                return jsonify({'logs': status.logs})
            return jsonify({'logs': []})

        @self.app.route('/api/start-all', methods=['POST'])
        def start_all():
            threading.Thread(target=self.manager.start_all, daemon=True).start()
            return jsonify({'success': True})

        @self.app.route('/api/stop-all', methods=['POST'])
        def stop_all():
            threading.Thread(target=self.manager.stop_all, daemon=True).start()
            return jsonify({'success': True})

    def setup_socketio(self):
        """Setup SocketIO events for real-time updates"""

        @self.socketio.on('connect')
        def handle_connect():
            print('Client connected to controller')

        @self.socketio.on('disconnect')
        def handle_disconnect():
            print('Client disconnected from controller')

        # Broadcast status updates
        def broadcast_status():
            while True:
                time.sleep(2)
                statuses = []
                for name in self.manager.services:
                    status = self.manager.statuses[name]
                    statuses.append(status.to_dict())
                self.socketio.emit('status_update', statuses)

        threading.Thread(target=broadcast_status, daemon=True).start()

    def run(self):
        """Start the Flask server"""
        print(f"Service Controller starting on http://0.0.0.0:{self.port}")
        self.socketio.run(self.app, host='0.0.0.0', port=self.port, debug=False)


def main():
    parser = argparse.ArgumentParser(description='Service Controller')
    parser.add_argument('--port', type=int, default=8000,
                        help='Web interface port (default: 8000)')
    parser.add_argument('--config', type=str, default='config/services.json',
                        help='Services configuration file')
    parser.add_argument('--base-dir', type=str, default='..',
                        help='Base directory for services (default: ..)')

    args = parser.parse_args()

    print("=== Service Controller ===")
    print(f"Port: {args.port}")
    print(f"Config: {args.config}")
    print(f"Base Directory: {args.base_dir}")
    print()

    # Create service manager
    manager = ServiceManager(args.config, args.base_dir)

    # Start monitoring
    manager.start_monitoring()

    # Create and run web app
    app = ControllerApp(manager, args.port)

    try:
        app.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
        manager.stop_all()


if __name__ == '__main__':
    main()
