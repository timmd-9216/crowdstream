#!/usr/bin/env python3
"""
Simplified Dance Energy Analyzer - No ML Dependencies
Real-time webcam analysis using only OpenCV for movement detection.
Controls audio engine via OSC based on dance movement energy.
"""

import cv2
import numpy as np
import time
from collections import deque
from pythonosc import udp_client
import argparse


class SimpleDanceEnergyAnalyzer:
    """Simplified dance energy analyzer using frame difference and optical flow"""

    def __init__(self, camera_id=0, osc_host="localhost", osc_port=57120, target_fps=30):
        # Video capture
        self.cap = cv2.VideoCapture(camera_id)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, target_fps)

        # OSC client
        self.osc_client = udp_client.SimpleUDPClient(osc_host, osc_port)

        # State
        self.prev_frame = None
        self.prev_gray = None
        self.energy_history = deque(maxlen=60)  # 2 seconds at 30fps
        self.smoothed_energy = 0.0

        # Audio control
        self.current_volume = 0.5
        self.current_crossfade = 0.5
        self.last_audio_update = 0.0

        # Performance
        self.frame_count = 0
        self.start_time = time.time()

        print(f"Simple Dance Energy Analyzer initialized:")
        print(f"  Camera: {camera_id}, OSC: {osc_host}:{osc_port}")

    def calculate_movement_energy(self, frame):
        """Calculate movement energy using frame difference and optical flow"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if self.prev_gray is None:
            self.prev_gray = gray.copy()
            return 0.0

        # Frame difference energy
        diff = cv2.absdiff(gray, self.prev_gray)
        diff = cv2.GaussianBlur(diff, (5, 5), 0)
        frame_energy = np.sum(diff) / (diff.shape[0] * diff.shape[1] * 255.0)

        # Optical flow energy (simplified)
        try:
            # Create feature points to track
            corners = cv2.goodFeaturesToTrack(self.prev_gray, 100, 0.3, 7)

            if corners is not None:
                # Calculate optical flow
                new_corners, status, error = cv2.calcOpticalFlowPyrLK(
                    self.prev_gray, gray, corners, None
                )

                # Calculate movement vectors
                if new_corners is not None:
                    movement_vectors = new_corners - corners
                    flow_energy = np.mean(np.linalg.norm(movement_vectors, axis=2))
                else:
                    flow_energy = 0.0
            else:
                flow_energy = 0.0

        except Exception:
            flow_energy = 0.0

        # Combine energies
        combined_energy = 0.6 * frame_energy + 0.4 * (flow_energy / 10.0)
        combined_energy = min(combined_energy, 1.0)  # Clamp to [0,1]

        self.prev_gray = gray.copy()
        return combined_energy

    def smooth_energy(self, energy):
        """Apply temporal smoothing"""
        self.energy_history.append(energy)

        # Exponential moving average
        alpha = 0.3
        self.smoothed_energy = alpha * energy + (1 - alpha) * self.smoothed_energy
        return self.smoothed_energy

    def control_audio(self, energy):
        """Control audio engine based on energy"""
        current_time = time.time()

        if current_time - self.last_audio_update < 0.1:  # 100ms rate limit
            return

        try:
            # Map energy to audio parameters
            target_volume = 0.3 + (energy * 0.7)  # 0.3 to 1.0
            target_crossfade = energy  # 0.0 to 1.0

            # Smooth transitions
            self.current_volume = 0.1 * target_volume + 0.9 * self.current_volume
            self.current_crossfade = 0.2 * target_crossfade + 0.8 * self.current_crossfade

            # Send OSC commands
            deck_a = 1.0 - self.current_crossfade
            deck_b = self.current_crossfade

            self.osc_client.send_message("/crossfade_levels", [deck_a, deck_b])
            self.osc_client.send_message("/stem_volume", [1000, self.current_volume])

            self.last_audio_update = current_time

        except Exception as e:
            print(f"OSC error: {e}")

    def draw_visualization(self, frame, energy):
        """Draw energy visualization"""
        h, w = frame.shape[:2]

        # Energy bar
        bar_height = int(h * 0.8)
        bar_width = 30
        bar_x = w - 50
        bar_y = int(h * 0.1)

        # Fill based on energy
        fill_height = int(bar_height * energy)
        color = (0, int(255 * energy), int(255 * (1 - energy)))

        cv2.rectangle(frame, (bar_x, bar_y + bar_height - fill_height),
                     (bar_x + bar_width, bar_y + bar_height), color, -1)
        cv2.rectangle(frame, (bar_x, bar_y),
                     (bar_x + bar_width, bar_y + bar_height), (255, 255, 255), 2)

        # Text info
        cv2.putText(frame, f"Energy: {energy:.3f}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Volume: {self.current_volume:.2f}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Crossfade: {self.current_crossfade:.2f}", (10, 85),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # FPS
        fps = self.frame_count / (time.time() - self.start_time + 0.001)
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, 110),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return frame

    def run(self):
        """Main processing loop"""
        print("Starting simple dance energy analysis... Press 'q' to quit")

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    break

                # Flip for mirror effect
                frame = cv2.flip(frame, 1)

                # Calculate energy
                energy = self.calculate_movement_energy(frame)
                smoothed_energy = self.smooth_energy(energy)

                # Control audio
                self.control_audio(smoothed_energy)

                # Visualize
                display_frame = self.draw_visualization(frame, smoothed_energy)
                cv2.imshow('Simple Dance Energy Analyzer', display_frame)

                # Handle input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord(' '):
                    cv2.waitKey(0)

                self.frame_count += 1

        except KeyboardInterrupt:
            print("Interrupted by user")
        finally:
            self.cap.release()
            cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description='Simple Dance Energy Analyzer')
    parser.add_argument('--camera', type=int, default=0)
    parser.add_argument('--osc-host', type=str, default='localhost')
    parser.add_argument('--osc-port', type=int, default=57120)
    parser.add_argument('--fps', type=int, default=30)

    args = parser.parse_args()

    analyzer = SimpleDanceEnergyAnalyzer(
        camera_id=args.camera,
        osc_host=args.osc_host,
        osc_port=args.osc_port,
        target_fps=args.fps
    )

    analyzer.run()


if __name__ == "__main__":
    main()