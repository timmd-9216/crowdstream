#!/usr/bin/env python3
"""
Native OpenGL Cosmic Visualizer for Jetson TX1
Uses pygame + PyOpenGL for direct GPU rendering (no browser needed)
Compatible with Python 3.5.2
"""

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
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
    """A single star in the visualization"""

    def __init__(self, width, height):
        self.x = random.uniform(-width, width)
        self.y = random.uniform(-height, height)
        self.z = random.uniform(-1000, -100)
        self.brightness = random.uniform(0.3, 1.0)
        self.size = random.uniform(1, 3)


class Planet(object):
    """A planet orbiting in the visualization"""

    def __init__(self, orbit_radius, speed, color):
        self.orbit_radius = orbit_radius
        self.base_speed = speed
        self.angle = random.uniform(0, 2 * math.pi)
        self.color = color
        self.size = random.uniform(10, 30)

    def update(self, speed_multiplier):
        self.angle += self.base_speed * speed_multiplier
        if self.angle > 2 * math.pi:
            self.angle -= 2 * math.pi

    def get_position(self):
        x = math.cos(self.angle) * self.orbit_radius
        y = math.sin(self.angle) * self.orbit_radius
        return (x, y)


class NativeCosmicVisualizer(object):
    """Native OpenGL visualizer for Jetson TX1"""

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
        # Galaxy rotation
        self.state.galaxy_rotation = min(self.state.leg_movement / 30.0, 3.0)

        # Nebula density
        self.state.nebula_density = min(self.state.total_movement / 100.0, 1.0)

        # Asteroid speed
        self.state.asteroid_speed = 0.5 + min(self.state.arm_movement / 10.0, 9.5)

        # Cosmic zoom
        self.state.cosmic_zoom = 0.5 + min(self.state.head_movement / 20.0, 2.5)

        # Star brightness
        self.state.star_brightness = 0.2 + min(self.state.total_movement / 125.0, 0.8)

        # Planet orbit speed
        combined = (self.state.arm_movement + self.state.leg_movement) / 2.0
        self.state.planet_orbit_speed = min(combined / 50.0, 2.0)

        # Cosmic energy
        self.state.cosmic_energy = min(self.state.total_movement / 80.0, 1.0)

    def start_osc_server(self):
        """Start OSC server in separate thread"""
        self.osc_server = osc_server.ThreadingOSCUDPServer(
            ('0.0.0.0', self.osc_port),
            self.osc_dispatcher
        )
        print("OSC server listening on port {}".format(self.osc_port))
        self.osc_server.serve_forever()

    def init_pygame(self):
        """Initialize Pygame and OpenGL"""
        pygame.init()

        flags = DOUBLEBUF | OPENGL
        if self.fullscreen:
            flags |= FULLSCREEN

        pygame.display.set_mode((self.width, self.height), flags)
        pygame.display.set_caption("Cosmic Journey - Native Visualizer")

        # OpenGL settings
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(0.0, 0.0, 0.05, 1.0)

        # Perspective
        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, (self.width / self.height), 0.1, 2000.0)
        glMatrixMode(GL_MODELVIEW)

    def create_stars(self, count=300):
        """Create star field"""
        self.stars = []
        for _ in range(count):
            self.stars.append(Star(self.width, self.height))

    def create_planets(self):
        """Create planets with orbits"""
        self.planets = [
            Planet(150, 0.002, (1.0, 0.3, 0.3)),  # Red
            Planet(250, 0.001, (0.3, 0.5, 1.0)),  # Blue
            Planet(350, 0.0007, (1.0, 1.0, 0.3)), # Yellow
            Planet(450, 0.0005, (0.5, 1.0, 0.5)), # Green
        ]

    def draw_stars(self):
        """Draw star field"""
        glPointSize(2.0)
        glBegin(GL_POINTS)

        for star in self.stars:
            brightness = star.brightness * self.state.star_brightness
            glColor4f(brightness, brightness, brightness * 1.2, 1.0)
            glVertex3f(star.x, star.y, star.z)

        glEnd()

    def draw_planets(self):
        """Draw orbiting planets"""
        for planet in self.planets:
            # Update orbit
            planet.update(self.state.planet_orbit_speed + 1.0)

            # Get position
            x, y = planet.get_position()

            # Draw orbit path
            glColor4f(0.2, 0.2, 0.3, 0.3)
            glBegin(GL_LINE_LOOP)
            for i in range(64):
                angle = (i / 64.0) * 2 * math.pi
                ox = math.cos(angle) * planet.orbit_radius
                oy = math.sin(angle) * planet.orbit_radius
                glVertex3f(ox, oy, -500)
            glEnd()

            # Draw planet
            glPushMatrix()
            glTranslatef(x, y, -500)

            # Glow effect based on energy
            glow = 1.0 + self.state.cosmic_energy * 0.5
            glColor4f(
                planet.color[0] * glow,
                planet.color[1] * glow,
                planet.color[2] * glow,
                1.0
            )

            # Draw sphere
            quadric = gluNewQuadric()
            gluSphere(quadric, planet.size, 16, 16)
            gluDeleteQuadric(quadric)

            glPopMatrix()

    def draw_galaxy_center(self):
        """Draw central galaxy/nebula effect"""
        glPushMatrix()

        # Rotate based on leg movement
        self.rotation += self.state.galaxy_rotation * 0.5
        glRotatef(self.rotation, 0, 0, 1)

        # Draw spiral arms
        glBegin(GL_LINES)
        for arm in range(3):
            arm_offset = (arm / 3.0) * 2 * math.pi
            for i in range(100):
                t = i / 100.0
                angle = t * 4 * math.pi + arm_offset
                radius = t * 200

                x = math.cos(angle) * radius
                y = math.sin(angle) * radius

                # Color based on nebula density
                alpha = self.state.nebula_density * (1.0 - t) * 0.5
                glColor4f(0.5, 0.3, 0.8, alpha)
                glVertex3f(x, y, -600)

                # Next point
                t2 = (i + 1) / 100.0
                angle2 = t2 * 4 * math.pi + arm_offset
                radius2 = t2 * 200
                x2 = math.cos(angle2) * radius2
                y2 = math.sin(angle2) * radius2
                glVertex3f(x2, y2, -600)

        glEnd()
        glPopMatrix()

    def draw_energy_field(self):
        """Draw energy field particles"""
        if self.state.cosmic_energy < 0.1:
            return

        glPointSize(3.0)
        glBegin(GL_POINTS)

        # Random energy particles
        random.seed(int(time.time() * 10))
        for _ in range(int(self.state.cosmic_energy * 100)):
            x = random.uniform(-400, 400)
            y = random.uniform(-300, 300)
            z = random.uniform(-800, -200)

            alpha = self.state.cosmic_energy * random.uniform(0.3, 1.0)
            glColor4f(1.0, 0.8, 0.3, alpha)
            glVertex3f(x, y, z)

        glEnd()

    def draw_hud(self):
        """Draw HUD with stats (2D overlay)"""
        # Switch to 2D mode
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glDisable(GL_DEPTH_TEST)

        # Draw stats background
        glColor4f(0.0, 0.0, 0.0, 0.5)
        glBegin(GL_QUADS)
        glVertex2f(self.width - 210, 10)
        glVertex2f(self.width - 10, 10)
        glVertex2f(self.width - 10, 150)
        glVertex2f(self.width - 210, 150)
        glEnd()

        # Draw energy bar
        bar_width = 180 * self.state.cosmic_energy
        glColor4f(1.0, 0.8, 0.2, 0.8)
        glBegin(GL_QUADS)
        glVertex2f(self.width - 200, 30)
        glVertex2f(self.width - 200 + bar_width, 30)
        glVertex2f(self.width - 200 + bar_width, 50)
        glVertex2f(self.width - 200, 50)
        glEnd()

        glEnable(GL_DEPTH_TEST)

        # Restore 3D mode
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def render(self):
        """Main render loop"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # Camera position affected by zoom
        zoom = self.state.cosmic_zoom
        gluLookAt(
            0, 0, 100 / zoom,  # Eye position
            0, 0, -500,         # Look at
            0, 1, 0             # Up vector
        )

        with self.lock:
            # Draw everything
            self.draw_stars()
            self.draw_galaxy_center()
            self.draw_planets()
            self.draw_energy_field()
            self.draw_hud()

        pygame.display.flip()

    def run(self):
        """Main loop"""
        print("\n=== Native Cosmic Visualizer ===")
        print("Resolution: {}x{}".format(self.width, self.height))
        print("OSC Port: {}".format(self.osc_port))
        print("\nInitializing...")

        # Start OSC server
        self.osc_thread = threading.Thread(target=self.start_osc_server, daemon=True)
        self.osc_thread.start()

        # Initialize graphics
        self.init_pygame()
        self.create_stars()
        self.create_planets()

        print("\n[OK] Visualizer running!")
        print("Controls:")
        print("  ESC or Q - Quit")
        print("  F - Toggle fullscreen")
        print("\nWaiting for OSC messages on port {}...".format(self.osc_port))

        self.running = True
        clock = pygame.time.Clock()

        while self.running:
            # Handle events
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.running = False
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE or event.key == K_q:
                        self.running = False
                    elif event.key == K_f:
                        pygame.display.toggle_fullscreen()

            # Render
            self.render()

            # Target 30 FPS for Jetson TX1
            clock.tick(30)

        print("\nShutting down...")
        if self.osc_server:
            self.osc_server.shutdown()
        pygame.quit()


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Native Cosmic Visualizer for Jetson TX1')
    parser.add_argument('--osc-port', type=int, default=5007,
                        help='OSC listening port (default: 5007)')
    parser.add_argument('--width', type=int, default=1280,
                        help='Window width (default: 1280)')
    parser.add_argument('--height', type=int, default=720,
                        help='Window height (default: 720)')
    parser.add_argument('--fullscreen', action='store_true',
                        help='Run in fullscreen mode')

    args = parser.parse_args()

    visualizer = NativeCosmicVisualizer(
        osc_port=args.osc_port,
        width=args.width,
        height=args.height,
        fullscreen=args.fullscreen
    )

    try:
        visualizer.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user")


if __name__ == '__main__':
    main()
