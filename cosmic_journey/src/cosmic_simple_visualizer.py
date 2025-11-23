#!/usr/bin/env python3
"""
Simple Cosmic Visualizer for Jetson TX1
Uses tkinter (pre-installed, no compilation needed)
Compatible with Python 3.5.2
"""

import tkinter as tk
from pythonosc import dispatcher, osc_server
import threading
import time
import math
import random


class CosmicState(object):
    """Current state of the cosmic visualizer"""

    def __init__(self):
        self.person_count = 0
        self.total_movement = 0.0
        self.arm_movement = 0.0
        self.leg_movement = 0.0
        self.head_movement = 0.0

        # Visualization parameters
        self.galaxy_rotation = 0.0
        self.nebula_density = 0.0
        self.asteroid_speed = 1.0
        self.cosmic_zoom = 1.0
        self.star_brightness = 0.5
        self.planet_orbit_speed = 0.0
        self.cosmic_energy = 0.0


class Star(object):
    """A single star"""

    def __init__(self, canvas_width, canvas_height):
        self.x = random.randint(0, canvas_width)
        self.y = random.randint(0, canvas_height)
        self.size = random.randint(1, 3)
        self.brightness = random.uniform(0.5, 1.0)
        self.id = None


class Planet(object):
    """A planet orbiting"""

    def __init__(self, center_x, center_y, radius, speed, color):
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius
        self.base_speed = speed
        self.angle = random.uniform(0, 2 * math.pi)
        self.color = color
        self.size = random.randint(15, 35)
        self.orbit_id = None
        self.id = None

    def update(self, speed_multiplier):
        self.angle += self.base_speed * speed_multiplier
        if self.angle > 2 * math.pi:
            self.angle -= 2 * math.pi

    def get_position(self):
        x = self.center_x + math.cos(self.angle) * self.radius
        y = self.center_y + math.sin(self.angle) * self.radius
        return (x, y)


class SimpleCosmicVisualizer(object):
    """Simple visualizer using tkinter"""

    def __init__(self, osc_port=5007, width=1280, height=720, fullscreen=False):
        self.osc_port = osc_port
        self.width = width
        self.height = height
        self.fullscreen = fullscreen

        # State
        self.state = CosmicState()
        self.lock = threading.Lock()
        self.running = False

        # Visual elements
        self.stars = []
        self.planets = []
        self.rotation = 0.0

        # Tkinter
        self.root = None
        self.canvas = None

        # OSC
        self.osc_dispatcher = dispatcher.Dispatcher()
        self.osc_server = None
        self.osc_thread = None

        self.setup_osc_handlers()

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
        self.state.galaxy_rotation = min(self.state.leg_movement / 30.0, 3.0)
        self.state.nebula_density = min(self.state.total_movement / 100.0, 1.0)
        self.state.asteroid_speed = 0.5 + min(self.state.arm_movement / 10.0, 9.5)
        self.state.cosmic_zoom = 0.5 + min(self.state.head_movement / 20.0, 2.5)
        self.state.star_brightness = 0.2 + min(self.state.total_movement / 125.0, 0.8)
        combined = (self.state.arm_movement + self.state.leg_movement) / 2.0
        self.state.planet_orbit_speed = min(combined / 50.0, 2.0)
        self.state.cosmic_energy = min(self.state.total_movement / 80.0, 1.0)

    def start_osc_server(self):
        """Start OSC server in separate thread"""
        self.osc_server = osc_server.ThreadingOSCUDPServer(
            ('0.0.0.0', self.osc_port),
            self.osc_dispatcher
        )
        print("OSC server listening on port {}".format(self.osc_port))
        self.osc_server.serve_forever()

    def rgb_to_hex(self, r, g, b):
        """Convert RGB (0-1) to hex color"""
        return "#{:02x}{:02x}{:02x}".format(
            int(r * 255),
            int(g * 255),
            int(b * 255)
        )

    def init_tkinter(self):
        """Initialize tkinter window"""
        self.root = tk.Tk()
        self.root.title("Cosmic Journey - Simple Visualizer")

        if self.fullscreen:
            self.root.attributes('-fullscreen', True)
            self.root.bind("<Escape>", lambda e: self.stop())
        else:
            self.root.geometry("{}x{}".format(self.width, self.height))

        self.root.configure(bg='black')
        self.root.bind("q", lambda e: self.stop())

        # Canvas
        self.canvas = tk.Canvas(
            self.root,
            width=self.width,
            height=self.height,
            bg='#000010',
            highlightthickness=0
        )
        self.canvas.pack()

    def create_stars(self, count=200):
        """Create star field"""
        self.stars = []
        for _ in range(count):
            star = Star(self.width, self.height)
            brightness = int(star.brightness * 255)
            color = self.rgb_to_hex(
                brightness / 255.0,
                brightness / 255.0,
                min(brightness * 1.2, 255) / 255.0
            )
            star.id = self.canvas.create_oval(
                star.x, star.y,
                star.x + star.size, star.y + star.size,
                fill=color,
                outline=color
            )
            self.stars.append(star)

    def create_planets(self):
        """Create planets"""
        center_x = self.width // 2
        center_y = self.height // 2

        self.planets = [
            Planet(center_x, center_y, 120, 0.005, '#ff4444'),  # Red
            Planet(center_x, center_y, 180, 0.003, '#4488ff'),  # Blue
            Planet(center_x, center_y, 240, 0.002, '#ffff44'),  # Yellow
            Planet(center_x, center_y, 300, 0.0015, '#44ff88'), # Green
        ]

        # Create orbit paths and planet circles
        for planet in self.planets:
            # Orbit path
            x0 = planet.center_x - planet.radius
            y0 = planet.center_y - planet.radius
            x1 = planet.center_x + planet.radius
            y1 = planet.center_y + planet.radius
            planet.orbit_id = self.canvas.create_oval(
                x0, y0, x1, y1,
                outline='#334455',
                width=1
            )

            # Planet
            x, y = planet.get_position()
            planet.id = self.canvas.create_oval(
                x - planet.size, y - planet.size,
                x + planet.size, y + planet.size,
                fill=planet.color,
                outline=planet.color
            )

    def update_stars(self):
        """Update star brightness"""
        for star in self.stars:
            brightness = int(star.brightness * self.state.star_brightness * 255)
            color = self.rgb_to_hex(
                brightness / 255.0,
                brightness / 255.0,
                min(brightness * 1.2, 255) / 255.0
            )
            self.canvas.itemconfig(star.id, fill=color, outline=color)

    def update_planets(self):
        """Update planet positions"""
        with self.lock:
            speed = self.state.planet_orbit_speed + 1.0

        for planet in self.planets:
            planet.update(speed * 0.1)  # Slow down for smoother animation
            x, y = planet.get_position()

            # Update position
            self.canvas.coords(
                planet.id,
                x - planet.size, y - planet.size,
                x + planet.size, y + planet.size
            )

            # Update color with energy glow
            glow = 1.0 + self.state.cosmic_energy * 0.5
            # Parse original color
            original = planet.color
            r = int(original[1:3], 16) / 255.0
            g = int(original[3:5], 16) / 255.0
            b = int(original[5:7], 16) / 255.0

            new_color = self.rgb_to_hex(
                min(r * glow, 1.0),
                min(g * glow, 1.0),
                min(b * glow, 1.0)
            )
            self.canvas.itemconfig(planet.id, fill=new_color, outline=new_color)

    def draw_hud(self):
        """Draw HUD with energy bar"""
        # Clear previous HUD
        self.canvas.delete("hud")

        # Background
        self.canvas.create_rectangle(
            self.width - 210, 10,
            self.width - 10, 100,
            fill='#000000',
            outline='#334455',
            tags="hud"
        )

        # Energy bar background
        self.canvas.create_rectangle(
            self.width - 200, 30,
            self.width - 20, 50,
            fill='#111111',
            outline='#445566',
            tags="hud"
        )

        # Energy bar fill
        bar_width = 180 * self.state.cosmic_energy
        if bar_width > 0:
            self.canvas.create_rectangle(
                self.width - 200, 30,
                self.width - 200 + bar_width, 50,
                fill='#ffcc00',
                outline='',
                tags="hud"
            )

        # Text labels
        self.canvas.create_text(
            self.width - 110, 20,
            text="COSMIC ENERGY",
            fill='#aabbcc',
            font=('Arial', 10, 'bold'),
            tags="hud"
        )

        self.canvas.create_text(
            self.width - 110, 65,
            text="Movement: {:.0f}".format(self.state.total_movement),
            fill='#aabbcc',
            font=('Arial', 9),
            tags="hud"
        )

        self.canvas.create_text(
            self.width - 110, 85,
            text="Persons: {}".format(self.state.person_count),
            fill='#aabbcc',
            font=('Arial', 9),
            tags="hud"
        )

    def render(self):
        """Update visualization"""
        if not self.running:
            return

        # Update elements
        self.update_stars()
        self.update_planets()
        self.draw_hud()

        # Schedule next frame (30 FPS)
        self.root.after(33, self.render)

    def stop(self):
        """Stop visualizer"""
        self.running = False
        if self.root:
            self.root.quit()

    def run(self):
        """Main loop"""
        print("\n=== Simple Cosmic Visualizer ===")
        print("Using tkinter (no OpenGL, no compilation needed)")
        print("Resolution: {}x{}".format(self.width, self.height))
        print("OSC Port: {}".format(self.osc_port))
        print("\nInitializing...")

        # Start OSC server
        self.osc_thread = threading.Thread(target=self.start_osc_server, daemon=True)
        self.osc_thread.start()

        # Initialize graphics
        self.init_tkinter()
        self.create_stars()
        self.create_planets()

        print("\n[OK] Visualizer running!")
        print("Controls:")
        print("  ESC or Q - Quit")
        print("\nWaiting for OSC messages on port {}...".format(self.osc_port))

        self.running = True

        # Start render loop
        self.root.after(100, self.render)

        # Run tkinter main loop
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        finally:
            self.running = False
            if self.osc_server:
                self.osc_server.shutdown()


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Simple Cosmic Visualizer for Jetson TX1')
    parser.add_argument('--osc-port', type=int, default=5007,
                        help='OSC listening port (default: 5007)')
    parser.add_argument('--width', type=int, default=1280,
                        help='Window width (default: 1280)')
    parser.add_argument('--height', type=int, default=720,
                        help='Window height (default: 720)')
    parser.add_argument('--fullscreen', action='store_true',
                        help='Run in fullscreen mode')

    args = parser.parse_args()

    visualizer = SimpleCosmicVisualizer(
        osc_port=args.osc_port,
        width=args.width,
        height=args.height,
        fullscreen=args.fullscreen
    )

    visualizer.run()


if __name__ == '__main__':
    main()
