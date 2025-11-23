#!/usr/bin/env python3
"""
GPU-Accelerated Cosmic Visualizer for Jetson TX1
Uses pyglet + OpenGL for Maxwell GPU rendering
Compatible with Python 3.5.2
"""

import pyglet
from pyglet.gl import *
from pythonosc import dispatcher, osc_server
import threading
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
    """A star with GPU rendering"""

    def __init__(self, width, height):
        self.x = random.uniform(-width, width)
        self.y = random.uniform(-height, height)
        self.z = random.uniform(-1000, -100)
        self.brightness = random.uniform(0.3, 1.0)
        self.size = random.uniform(1, 3)


class Planet(object):
    """A planet with orbit"""

    def __init__(self, orbit_radius, speed, color):
        self.orbit_radius = orbit_radius
        self.base_speed = speed
        self.angle = random.uniform(0, 2 * math.pi)
        self.color = color
        self.size = random.uniform(10, 30)

    def update(self, speed_multiplier, dt):
        self.angle += self.base_speed * speed_multiplier * dt * 60
        while self.angle > 2 * math.pi:
            self.angle -= 2 * math.pi

    def get_position(self):
        x = math.cos(self.angle) * self.orbit_radius
        y = math.sin(self.angle) * self.orbit_radius
        return (x, y, -500)


class GPUCosmicVisualizer(pyglet.window.Window):
    """GPU-accelerated visualizer using pyglet + OpenGL"""

    def __init__(self, osc_port=5007, width=1280, height=720, fullscreen=False):
        super(GPUCosmicVisualizer, self).__init__(
            width=width,
            height=height,
            caption="Cosmic Journey - GPU Visualizer",
            resizable=False,
            fullscreen=fullscreen,
            vsync=True
        )

        self.osc_port = osc_port

        # State
        self.state = CosmicState()
        self.lock = threading.Lock()

        # Visual elements
        self.stars = []
        self.planets = []
        self.rotation = 0.0

        # OSC
        self.osc_dispatcher = dispatcher.Dispatcher()
        self.osc_server = None
        self.osc_thread = None

        self.setup_osc_handlers()
        self.setup_opengl()
        self.create_stars(300)
        self.create_planets()

        print("\n=== GPU Cosmic Visualizer ===")
        print("Using OpenGL with Maxwell GPU")
        print("Resolution: {}x{}".format(width, height))
        print("OSC Port: {}".format(self.osc_port))
        print("\nControls:")
        print("  ESC or Q - Quit")
        print("  F - Toggle fullscreen")
        print("\nStarting OSC server...")

        # Start OSC server
        self.osc_thread = threading.Thread(target=self.start_osc_server, daemon=True)
        self.osc_thread.start()

        print("[OK] Ready! Waiting for OSC messages...")

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
        self.osc_server.serve_forever()

    def setup_opengl(self):
        """Setup OpenGL state"""
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        glClearColor(0.0, 0.0, 0.05, 1.0)

    def create_stars(self, count):
        """Create star field"""
        self.stars = []
        for _ in range(count):
            self.stars.append(Star(self.width, self.height))

    def create_planets(self):
        """Create planets"""
        self.planets = [
            Planet(150, 0.002, (1.0, 0.3, 0.3)),  # Red
            Planet(250, 0.001, (0.3, 0.5, 1.0)),  # Blue
            Planet(350, 0.0007, (1.0, 1.0, 0.3)), # Yellow
            Planet(450, 0.0005, (0.5, 1.0, 0.5)), # Green
        ]

    def on_draw(self):
        """Render frame"""
        self.clear()

        # Setup 3D projection
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, float(self.width) / float(self.height), 0.1, 2000.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # Camera position with zoom
        zoom = self.state.cosmic_zoom
        gluLookAt(
            0, 0, 100 / zoom,
            0, 0, -500,
            0, 1, 0
        )

        with self.lock:
            self.draw_stars()
            self.draw_galaxy_center()
            self.draw_planets()
            self.draw_energy_field()

        # Switch to 2D for HUD
        self.draw_hud()

    def draw_stars(self):
        """Draw star field"""
        glPointSize(2.0)
        glBegin(GL_POINTS)

        for star in self.stars:
            brightness = star.brightness * self.state.star_brightness
            glColor4f(brightness, brightness, brightness * 1.2, 1.0)
            glVertex3f(star.x, star.y, star.z)

        glEnd()

    def draw_galaxy_center(self):
        """Draw galaxy spiral"""
        glPushMatrix()

        self.rotation += self.state.galaxy_rotation * 0.01
        glRotatef(self.rotation, 0, 0, 1)

        glBegin(GL_LINES)
        for arm in range(3):
            arm_offset = (arm / 3.0) * 2 * math.pi
            for i in range(50):
                t = i / 50.0
                angle = t * 4 * math.pi + arm_offset
                radius = t * 200

                x = math.cos(angle) * radius
                y = math.sin(angle) * radius

                alpha = self.state.nebula_density * (1.0 - t) * 0.5
                glColor4f(0.5, 0.3, 0.8, alpha)
                glVertex3f(x, y, -600)

                # Next point
                t2 = (i + 1) / 50.0
                angle2 = t2 * 4 * math.pi + arm_offset
                radius2 = t2 * 200
                x2 = math.cos(angle2) * radius2
                y2 = math.sin(angle2) * radius2
                glVertex3f(x2, y2, -600)

        glEnd()
        glPopMatrix()

    def draw_planets(self):
        """Draw planets"""
        for planet in self.planets:
            # Draw orbit
            glColor4f(0.2, 0.2, 0.3, 0.3)
            glBegin(GL_LINE_LOOP)
            for i in range(64):
                angle = (i / 64.0) * 2 * math.pi
                x = math.cos(angle) * planet.orbit_radius
                y = math.sin(angle) * planet.orbit_radius
                glVertex3f(x, y, -500)
            glEnd()

            # Draw planet
            x, y, z = planet.get_position()
            glPushMatrix()
            glTranslatef(x, y, z)

            glow = 1.0 + self.state.cosmic_energy * 0.5
            glColor4f(
                planet.color[0] * glow,
                planet.color[1] * glow,
                planet.color[2] * glow,
                1.0
            )

            # Draw sphere using GL_TRIANGLE_FAN (simple)
            slices = 16
            stacks = 16
            for j in range(stacks):
                lat0 = math.pi * (-0.5 + float(j) / stacks)
                z0 = planet.size * math.sin(lat0)
                zr0 = planet.size * math.cos(lat0)

                lat1 = math.pi * (-0.5 + float(j + 1) / stacks)
                z1 = planet.size * math.sin(lat1)
                zr1 = planet.size * math.cos(lat1)

                glBegin(GL_TRIANGLE_STRIP)
                for i in range(slices + 1):
                    lng = 2 * math.pi * float(i) / slices
                    x_coord = math.cos(lng)
                    y_coord = math.sin(lng)

                    glVertex3f(x_coord * zr0, y_coord * zr0, z0)
                    glVertex3f(x_coord * zr1, y_coord * zr1, z1)
                glEnd()

            glPopMatrix()

    def draw_energy_field(self):
        """Draw energy particles"""
        if self.state.cosmic_energy < 0.1:
            return

        glPointSize(3.0)
        glBegin(GL_POINTS)

        random.seed(int(self.rotation * 100))
        for _ in range(int(self.state.cosmic_energy * 100)):
            x = random.uniform(-400, 400)
            y = random.uniform(-300, 300)
            z = random.uniform(-800, -200)

            alpha = self.state.cosmic_energy * random.uniform(0.3, 1.0)
            glColor4f(1.0, 0.8, 0.3, alpha)
            glVertex3f(x, y, z)

        glEnd()

    def draw_hud(self):
        """Draw 2D HUD overlay"""
        # Switch to 2D orthographic projection
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, 0, self.height, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glDisable(GL_DEPTH_TEST)

        # Background box
        glColor4f(0.0, 0.0, 0.0, 0.5)
        glBegin(GL_QUADS)
        glVertex2f(self.width - 210, self.height - 10)
        glVertex2f(self.width - 10, self.height - 10)
        glVertex2f(self.width - 10, self.height - 100)
        glVertex2f(self.width - 210, self.height - 100)
        glEnd()

        # Energy bar
        bar_width = 180 * self.state.cosmic_energy
        glColor4f(1.0, 0.8, 0.2, 0.8)
        glBegin(GL_QUADS)
        glVertex2f(self.width - 200, self.height - 30)
        glVertex2f(self.width - 200 + bar_width, self.height - 30)
        glVertex2f(self.width - 200 + bar_width, self.height - 50)
        glVertex2f(self.width - 200, self.height - 50)
        glEnd()

        glEnable(GL_DEPTH_TEST)

        # Restore matrices
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

    def on_key_press(self, symbol, modifiers):
        """Handle keyboard input"""
        if symbol == pyglet.window.key.ESCAPE or symbol == pyglet.window.key.Q:
            self.close()
        elif symbol == pyglet.window.key.F:
            self.set_fullscreen(not self.fullscreen)

    def update(self, dt):
        """Update animation"""
        with self.lock:
            speed = self.state.planet_orbit_speed + 1.0

        for planet in self.planets:
            planet.update(speed, dt)

    def run(self):
        """Start the visualizer"""
        pyglet.clock.schedule_interval(self.update, 1/30.0)  # 30 FPS
        pyglet.app.run()

    def close(self):
        """Cleanup on exit"""
        if self.osc_server:
            self.osc_server.shutdown()
        super(GPUCosmicVisualizer, self).close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description='GPU Cosmic Visualizer for Jetson TX1')
    parser.add_argument('--osc-port', type=int, default=5007,
                        help='OSC listening port (default: 5007)')
    parser.add_argument('--width', type=int, default=1280,
                        help='Window width (default: 1280)')
    parser.add_argument('--height', type=int, default=720,
                        help='Window height (default: 720)')
    parser.add_argument('--fullscreen', action='store_true',
                        help='Run in fullscreen mode')

    args = parser.parse_args()

    visualizer = GPUCosmicVisualizer(
        osc_port=args.osc_port,
        width=args.width,
        height=args.height,
        fullscreen=args.fullscreen
    )

    try:
        visualizer.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
        visualizer.close()


if __name__ == '__main__':
    main()
