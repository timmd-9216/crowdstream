#!/usr/bin/env python3
"""
Dance Movement Detector using YOLO Pose Detection
Analyzes dancer movements and sends periodic reports about overall movement,
arms, legs, and head motion.
"""

import cv2
import numpy as np
from ultralytics import YOLO
import time
import json
from collections import defaultdict, deque
from pythonosc import udp_client
import argparse


class MovementStats(object):
    """Statistics for movement analysis"""
    def __init__(self, timestamp, total_movement, arm_movement, leg_movement, head_movement, person_count):
        self.timestamp = timestamp
        self.total_movement = total_movement
        self.arm_movement = arm_movement
        self.leg_movement = leg_movement
        self.head_movement = head_movement
        self.person_count = person_count

    def to_dict(self):
        return {
            'timestamp': self.timestamp,
            'total_movement': self.total_movement,
            'arm_movement': self.arm_movement,
            'leg_movement': self.leg_movement,
            'head_movement': self.head_movement,
            'person_count': self.person_count
        }


class BodyPartTracker:
    """Tracks movement of specific body parts"""

    # YOLO pose keypoint indices
    KEYPOINTS = {
        'nose': 0,
        'left_eye': 1, 'right_eye': 2,
        'left_ear': 3, 'right_ear': 4,
        'left_shoulder': 5, 'right_shoulder': 6,
        'left_elbow': 7, 'right_elbow': 8,
        'left_wrist': 9, 'right_wrist': 10,
        'left_hip': 11, 'right_hip': 12,
        'left_knee': 13, 'right_knee': 14,
        'left_ankle': 15, 'right_ankle': 16
    }

    ARM_KEYPOINTS = [5, 6, 7, 8, 9, 10]  # shoulders, elbows, wrists
    LEG_KEYPOINTS = [11, 12, 13, 14, 15, 16]  # hips, knees, ankles
    HEAD_KEYPOINTS = [0, 1, 2, 3, 4]  # nose, eyes, ears

    def __init__(self, history_size=10):
        """
        Args:
            history_size: Number of frames to keep for movement calculation
        """
        self.history_size = history_size
        self.pose_history = defaultdict(lambda: deque(maxlen=history_size))

    def update(self, person_id, keypoints):
        """Update pose history for a person"""
        self.pose_history[person_id].append(keypoints.copy())

    def calculate_movement(self, person_id, keypoint_indices):
        """Calculate movement for specific keypoints"""
        if person_id not in self.pose_history or len(self.pose_history[person_id]) < 2:
            return 0.0

        history = list(self.pose_history[person_id])
        total_movement = 0.0
        count = 0

        # Calculate movement between consecutive frames
        for i in range(1, len(history)):
            prev_frame = history[i-1]
            curr_frame = history[i]

            for kp_idx in keypoint_indices:
                if kp_idx >= len(prev_frame) or kp_idx >= len(curr_frame):
                    continue

                prev_point = prev_frame[kp_idx]
                curr_point = curr_frame[kp_idx]

                # Check if keypoints are visible (confidence > 0)
                if prev_point[2] > 0 and curr_point[2] > 0:
                    # Euclidean distance
                    dx = curr_point[0] - prev_point[0]
                    dy = curr_point[1] - prev_point[1]
                    distance = np.sqrt(dx*dx + dy*dy)
                    total_movement += distance
                    count += 1

        return total_movement / max(count, 1)

    def get_arm_movement(self, person_id):
        """Calculate arm movement"""
        return self.calculate_movement(person_id, self.ARM_KEYPOINTS)

    def get_leg_movement(self, person_id):
        """Calculate leg movement"""
        return self.calculate_movement(person_id, self.LEG_KEYPOINTS)

    def get_head_movement(self, person_id):
        """Calculate head movement"""
        return self.calculate_movement(person_id, self.HEAD_KEYPOINTS)

    def get_total_movement(self, person_id):
        """Calculate total body movement"""
        all_keypoints = list(range(17))  # All YOLO pose keypoints
        return self.calculate_movement(person_id, all_keypoints)

    def cleanup_old_tracks(self, active_ids: set):
        """Remove tracks for people no longer detected"""
        inactive_ids = set(self.pose_history.keys()) - active_ids
        for pid in inactive_ids:
            del self.pose_history[pid]


class DanceMovementDetector:
    """Main detector class"""

    def __init__(self, config: dict):
        self.config = config
        self.model = YOLO('yolov8n-pose.pt')  # Nano model for speed
        self.tracker = BodyPartTracker(history_size=config.get('history_frames', 10))

        # OSC clients for sending messages (support multiple destinations)
        self.osc_clients = []
        self.osc_destinations = []

        # Check if multiple destinations are configured
        osc_destinations = config.get('osc_destinations', None)
        if osc_destinations:
            # Multiple destinations
            for dest in osc_destinations:
                client = udp_client.SimpleUDPClient(dest['host'], dest['port'])
                self.osc_clients.append(client)
                self.osc_destinations.append({
                    'host': dest['host'],
                    'port': dest['port'],
                    'description': dest.get('description', '')
                })
        else:
            # Single destination (backward compatibility)
            host = config.get('osc_host', '127.0.0.1')
            port = config.get('osc_port', 5005)
            client = udp_client.SimpleUDPClient(host, port)
            self.osc_clients.append(client)
            self.osc_destinations.append({'host': host, 'port': port, 'description': ''})

        self.last_message_time = 0
        self.message_interval = config.get('message_interval', 10.0)

        # Video source
        self.video_source = config.get('video_source', 0)
        self.cap = None

    def start(self):
        """Start detection and analysis"""
        self.cap = cv2.VideoCapture(self.video_source)

        if not self.cap.isOpened():
            raise RuntimeError("Cannot open video source: {}".format(self.video_source))

        print("Starting dance movement detection...")
        print("Video source: {}".format(self.video_source))
        print("Message interval: {}s".format(self.message_interval))
        print("OSC destinations ({}):".format(len(self.osc_destinations)))
        for i, dest in enumerate(self.osc_destinations, 1):
            desc = " ({})".format(dest['description']) if dest['description'] else ""
            print("  {}. {}:{}{}".format(i, dest['host'], dest['port'], desc))
        print("\nPress 'q' to quit\n")

        try:
            self._detection_loop()
        finally:
            self.cap.release()
            cv2.destroyAllWindows()

    def _detection_loop(self):
        """Main detection loop"""
        frame_count = 0

        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("End of video or cannot read frame")
                break

            frame_count += 1
            current_time = time.time()

            # Run YOLO pose detection
            results = self.model.track(frame, persist=True, verbose=False)

            if results[0].keypoints is not None:
                keypoints = results[0].keypoints.data.cpu().numpy()

                # Get tracking IDs if available
                if results[0].boxes.id is not None:
                    track_ids = results[0].boxes.id.cpu().numpy().astype(int)
                else:
                    track_ids = list(range(len(keypoints)))

                # Update tracker with new poses
                active_ids = set()
                for person_id, kps in zip(track_ids, keypoints):
                    self.tracker.update(person_id, kps)
                    active_ids.add(person_id)

                # Send keypoint data for skeleton visualization
                self._send_keypoint_data(track_ids, keypoints)

                # Cleanup old tracks
                self.tracker.cleanup_old_tracks(active_ids)

                # Send periodic messages
                if current_time - self.last_message_time >= self.message_interval:
                    self._send_movement_report(active_ids, current_time)
                    self.last_message_time = current_time

            # Display results if enabled
            if self.config.get('show_video', True):
                annotated_frame = results[0].plot()
                cv2.imshow('Dance Movement Detector', annotated_frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    def _send_movement_report(self, active_ids, timestamp):
        """Calculate and send movement statistics"""
        if not active_ids:
            print("[{}] No dancers detected".format(time.strftime('%H:%M:%S')))
            return

        # Aggregate movement across all detected people
        total_arm_movement = 0.0
        total_leg_movement = 0.0
        total_head_movement = 0.0
        total_overall_movement = 0.0

        for person_id in active_ids:
            total_arm_movement += self.tracker.get_arm_movement(person_id)
            total_leg_movement += self.tracker.get_leg_movement(person_id)
            total_head_movement += self.tracker.get_head_movement(person_id)
            total_overall_movement += self.tracker.get_total_movement(person_id)

        # Average by number of people
        person_count = len(active_ids)
        stats = MovementStats(
            timestamp=timestamp,
            total_movement=total_overall_movement / person_count,
            arm_movement=total_arm_movement / person_count,
            leg_movement=total_leg_movement / person_count,
            head_movement=total_head_movement / person_count,
            person_count=person_count
        )

        # Send OSC messages
        self._send_osc_messages(stats)

        # Print to console
        print("[{}] People: {} | Total: {:.1f} | Arms: {:.1f} | Legs: {:.1f} | Head: {:.1f}".format(
            time.strftime('%H:%M:%S'),
            stats.person_count,
            stats.total_movement,
            stats.arm_movement,
            stats.leg_movement,
            stats.head_movement
        ))

        # Save to file if configured
        if self.config.get('save_to_file', False):
            self._save_stats(stats)

    def _send_keypoint_data(self, track_ids, keypoints):
        """Send raw keypoint data for skeleton visualization"""
        # Only send to skeleton visualizer (assume it's listening on a different port)
        # Format: /pose/keypoints person_id x0 y0 conf0 x1 y1 conf1 ... (17 keypoints)
        for person_id, kps in zip(track_ids, keypoints):
            # Flatten keypoints array
            message_data = [int(person_id)]
            for kp in kps:
                message_data.extend([float(kp[0]), float(kp[1]), float(kp[2])])

            # Send to all OSC clients
            for client in self.osc_clients:
                try:
                    client.send_message("/pose/keypoints", message_data)
                except Exception as e:
                    # Silently continue if skeleton visualizer is not running
                    pass

    def _send_osc_messages(self, stats):
        """Send movement statistics via OSC to all destinations"""
        base_address = self.config.get('osc_base_address', '/dance')

        # Send to all OSC clients
        for client in self.osc_clients:
            # Convert to native Python types for OSC compatibility
            client.send_message("{}/person_count".format(base_address), int(stats.person_count))
            client.send_message("{}/total_movement".format(base_address), float(stats.total_movement))
            client.send_message("{}/arm_movement".format(base_address), float(stats.arm_movement))
            client.send_message("{}/leg_movement".format(base_address), float(stats.leg_movement))
            client.send_message("{}/head_movement".format(base_address), float(stats.head_movement))

    def _save_stats(self, stats):
        """Save statistics to JSON file"""
        filename = self.config.get('output_file', 'movement_stats.json')

        try:
            with open(filename, 'a') as f:
                json.dump(stats.to_dict(), f)
                f.write('\n')
        except Exception as e:
            print("Error saving stats: {}".format(e))


def main():
    parser = argparse.ArgumentParser(description='Dance Movement Detector for DJ feedback')
    parser.add_argument('--config', type=str, default='config/config.json',
                        help='Path to configuration file')
    parser.add_argument('--video', type=str, default=None,
                        help='Video source (0 for webcam, or path to video file)')
    parser.add_argument('--interval', type=float, default=None,
                        help='Message interval in seconds (default: 10)')
    parser.add_argument('--osc-host', type=str, default=None,
                        help='OSC destination host')
    parser.add_argument('--osc-port', type=int, default=None,
                        help='OSC destination port')
    parser.add_argument('--no-display', action='store_true',
                        help='Disable video display')

    args = parser.parse_args()

    # Load config from file
    config = {}
    try:
        with open(args.config, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Config file not found: {}, using defaults".format(args.config))
        config = {
            'video_source': 0,
            'message_interval': 10.0,
            'osc_host': '127.0.0.1',
            'osc_port': 5005,
            'osc_base_address': '/dance',
            'history_frames': 10,
            'show_video': True,
            'save_to_file': False,
            'output_file': 'movement_stats.json'
        }

    # Override with command line arguments
    if args.video is not None:
        config['video_source'] = int(args.video) if args.video.isdigit() else args.video
    if args.interval is not None:
        config['message_interval'] = args.interval
    if args.osc_host is not None:
        config['osc_host'] = args.osc_host
    if args.osc_port is not None:
        config['osc_port'] = args.osc_port
    if args.no_display:
        config['show_video'] = False

    # Start detector
    detector = DanceMovementDetector(config)
    detector.start()


if __name__ == '__main__':
    main()
