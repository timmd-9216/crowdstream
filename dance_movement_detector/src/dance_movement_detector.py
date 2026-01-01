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
import platform
import torch
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple
from pythonosc import udp_client
import argparse


@dataclass
class MovementStats:
    """Statistics for movement analysis"""
    timestamp: float
    total_movement: float
    arm_movement: float
    leg_movement: float
    head_movement: float
    person_count: int

    def to_dict(self):
        return asdict(self)


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

    def __init__(self, history_size: int = 10):
        """
        Args:
            history_size: Number of frames to keep for movement calculation
        """
        self.history_size = history_size
        self.pose_history: Dict[int, deque] = defaultdict(lambda: deque(maxlen=history_size))
        self.bbox_size_history: Dict[int, deque] = defaultdict(lambda: deque(maxlen=history_size))  # Store bbox size for normalization

    def update(self, person_id: int, keypoints: np.ndarray, bbox_size: float = None):
        """Update pose history for a person
        
        Args:
            person_id: Tracking ID of the person
            keypoints: Array of keypoints (x, y, confidence)
            bbox_size: Size of bounding box (diagonal or average dimension) for normalization
        """
        self.pose_history[person_id].append(keypoints.copy())
        if bbox_size is not None:
            self.bbox_size_history[person_id].append(bbox_size)
        elif person_id in self.bbox_size_history and len(self.bbox_size_history[person_id]) > 0:
            # Reuse last known bbox size if not provided
            self.bbox_size_history[person_id].append(self.bbox_size_history[person_id][-1])

    def calculate_movement(self, person_id: int, keypoint_indices: List[int]) -> float:
        """Calculate movement for specific keypoints, normalized by bounding box size
        Uses enhanced sensitivity to better detect arm and body movements"""
        if person_id not in self.pose_history or len(self.pose_history[person_id]) < 2:
            return 0.0

        history = list(self.pose_history[person_id])
        bbox_history = list(self.bbox_size_history[person_id]) if person_id in self.bbox_size_history else []
        total_movement = 0.0
        count = 0
        
        # Sensitivity multiplier to amplify movement detection
        SENSITIVITY_MULTIPLIER = 2.5  # Increase sensitivity by 2.5x

        # Calculate movement between consecutive frames
        for i in range(1, len(history)):
            prev_frame = history[i-1]
            curr_frame = history[i]
            
            # Get average bbox size for normalization (use current frame's bbox or previous)
            bbox_size = 1.0  # Default: no normalization if bbox size not available
            if len(bbox_history) >= i:
                bbox_size = bbox_history[i-1] if i-1 < len(bbox_history) else (bbox_history[-1] if bbox_history else 1.0)
            elif len(bbox_history) > 0:
                bbox_size = bbox_history[-1]  # Use last known bbox size
            
            # Skip normalization if bbox_size is invalid
            if bbox_size <= 0:
                bbox_size = 1.0

            for kp_idx in keypoint_indices:
                if kp_idx >= len(prev_frame) or kp_idx >= len(curr_frame):
                    continue

                prev_point = prev_frame[kp_idx]
                curr_point = curr_frame[kp_idx]

                # Check if keypoints are visible (confidence > 0)
                if prev_point[2] > 0 and curr_point[2] > 0:
                    # Euclidean distance in pixels
                    dx = curr_point[0] - prev_point[0]
                    dy = curr_point[1] - prev_point[1]
                    distance = np.sqrt(dx*dx + dy*dy)
                    
                    # Normalize by bounding box size (movement relative to person size)
                    # This makes movement independent of distance from camera
                    normalized_distance = distance / bbox_size if bbox_size > 0 else distance
                    
                    # Apply sensitivity multiplier to amplify movement detection
                    # This makes the sensor more responsive to arm and body movements
                    amplified_movement = normalized_distance * SENSITIVITY_MULTIPLIER
                    
                    total_movement += amplified_movement
                    count += 1

        return total_movement / max(count, 1)

    def get_arm_movement(self, person_id: int) -> float:
        """Calculate arm movement"""
        return self.calculate_movement(person_id, self.ARM_KEYPOINTS)

    def get_leg_movement(self, person_id: int) -> float:
        """Calculate leg movement"""
        return self.calculate_movement(person_id, self.LEG_KEYPOINTS)

    def get_head_movement(self, person_id: int) -> float:
        """Calculate head movement"""
        return self.calculate_movement(person_id, self.HEAD_KEYPOINTS)

    def get_total_movement(self, person_id: int) -> float:
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

        # Model selection (configurable for performance tuning)
        model_name = config.get('model', 'yolov8n-pose.pt')
        self.model = YOLO(model_name)

        # Raspberry Pi optimizations
        self.imgsz = config.get('imgsz', 640)  # Input image size (try 320 or 416 for speed)
        self.conf_threshold = config.get('conf_threshold', 0.25)  # Confidence threshold
        self.iou_threshold = config.get('iou_threshold', 0.45)  # IoU threshold for NMS
        self.max_det = config.get('max_det', 10)  # Maximum detections per image

        self.tracker = BodyPartTracker(history_size=config.get('history_frames', 10))

        # Device detection for optimal performance
        self.device = self._detect_device()
        self.use_half = self._should_use_half()

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

    def _detect_device(self) -> str:
        """Detect the best device for YOLO inference based on platform"""
        # Allow override from config
        device_override = self.config.get('device', None)
        if device_override:
            return device_override

        # Detect platform
        system = platform.system()
        
        if system == 'Darwin':  # macOS
            # Check if MPS (Metal Performance Shaders) is available for Apple Silicon
            if torch.backends.mps.is_available():
                return 'mps'
            else:
                # Mac Intel or MPS not available - let YOLO auto-detect
                return None  # None = auto-detect
        elif system == 'Linux':
            # Raspberry Pi or other Linux - use CPU
            return 'cpu'
        else:
            # Windows or other - let YOLO auto-detect (will use CUDA if available)
            return None

    def _should_use_half(self) -> bool:
        """Determine if FP16 (half precision) should be used"""
        # Allow override from config
        half_override = self.config.get('half', None)
        if half_override is not None:
            return half_override

        # FP16 is beneficial on:
        # - Apple Silicon Macs with MPS
        # - NVIDIA GPUs with CUDA
        # Not recommended on CPU
        if self.device == 'mps':
            return True  # MPS supports FP16 well
        elif self.device == 'cpu':
            return False  # CPU doesn't benefit from FP16
        elif self.device is None:
            # Auto-detect: check if CUDA is available
            if torch.cuda.is_available():
                return True
            return False
        else:
            return False

    def start(self):
        """Start detection and analysis"""
        self.cap = cv2.VideoCapture(self.video_source)

        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open video source: {self.video_source}")

        # Reduce camera buffer to minimize latency
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Set camera resolution (lower = faster)
        camera_width = self.config.get('camera_width', 640)
        camera_height = self.config.get('camera_height', 480)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_height)

        # Set FPS if specified
        camera_fps = self.config.get('camera_fps', None)
        if camera_fps:
            self.cap.set(cv2.CAP_PROP_FPS, camera_fps)

        print(f"Starting dance movement detection...")
        print(f"Video source: {self.video_source}")
        device_info = self.device if self.device else "auto-detect"
        print(f"Device: {device_info} | FP16: {self.use_half}")
        print(f"Message interval: {self.message_interval}s")
        print(f"OSC destinations ({len(self.osc_destinations)}):")
        for i, dest in enumerate(self.osc_destinations, 1):
            desc = f" ({dest['description']})" if dest['description'] else ""
            print(f"  {i}. {dest['host']}:{dest['port']}{desc}")
        print("\nPress 'q' to quit\n")

        try:
            self._detection_loop()
        finally:
            self.cap.release()
            cv2.destroyAllWindows()

    def _detection_loop(self):
        """Main detection loop"""
        frame_count = 0
        skip_frames = self.config.get('skip_frames', 0)  # Process every Nth frame

        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("End of video or cannot read frame")
                break

            frame_count += 1

            # Skip frames for performance (process every Nth frame)
            if skip_frames > 0 and frame_count % (skip_frames + 1) != 0:
                continue

            current_time = time.time()

            # Get frame dimensions
            h, w = frame.shape[:2]

            # Run YOLO pose detection with optimizations
            track_kwargs = {
                'persist': True,
                'verbose': False,
                'imgsz': self.imgsz,
                'conf': self.conf_threshold,
                'iou': self.iou_threshold,
                'max_det': self.max_det,
                'half': self.use_half
            }
            
            # Only set device if explicitly specified (None = auto-detect)
            if self.device is not None:
                track_kwargs['device'] = self.device
            
            results = self.model.track(frame, **track_kwargs)

            if results[0].keypoints is not None:
                # Extract keypoints and IDs efficiently
                keypoints = results[0].keypoints.data.cpu().numpy()

                # DEBUG: Check what YOLO detected
                num_keypoints = len(keypoints)
                num_boxes = len(results[0].boxes) if results[0].boxes is not None else 0

                # Get tracking IDs if available
                if results[0].boxes.id is not None:
                    track_ids = results[0].boxes.id.cpu().numpy().astype(int)
                    num_tracked = len(track_ids)

                    # CRITICAL: Verify alignment between boxes and keypoints
                    if num_tracked != num_keypoints:
                        print(f"⚠️ Mismatch: {num_tracked} tracked IDs but {num_keypoints} keypoints! Using sequential IDs.")
                        track_ids = np.arange(num_keypoints, dtype=int)
                else:
                    # Generate sequential IDs for untracked detections
                    track_ids = np.arange(num_keypoints, dtype=int)
                    if num_keypoints > 0:
                        print(f"⚠️ Tracking failed: {num_keypoints} people detected but no IDs assigned")

                # Extract bounding boxes for normalization
                bbox_sizes = []
                if results[0].boxes is not None and len(results[0].boxes) > 0:
                    boxes_xyxy = results[0].boxes.xyxy.cpu().numpy()  # [x1, y1, x2, y2]
                    for box in boxes_xyxy:
                        # Calculate bounding box size (average of width and height)
                        width = box[2] - box[0]  # x2 - x1
                        height = box[3] - box[1]  # y2 - y1
                        # Use average of width and height as normalization factor
                        # This makes movement relative to person size, independent of camera distance
                        bbox_size = (width + height) / 2.0
                        bbox_sizes.append(bbox_size)
                else:
                    # Fallback: estimate from keypoints if boxes not available
                    for kps in keypoints:
                        # Get bounding box from keypoint extents
                        visible_kps = kps[kps[:, 2] > 0]  # Only visible keypoints
                        if len(visible_kps) > 0:
                            min_x, min_y = visible_kps[:, :2].min(axis=0)
                            max_x, max_y = visible_kps[:, :2].max(axis=0)
                            width = max_x - min_x
                            height = max_y - min_y
                            bbox_size = (width + height) / 2.0
                        else:
                            bbox_size = 100.0  # Default fallback
                        bbox_sizes.append(bbox_size)

                # Update tracker with new poses and bounding box sizes
                active_ids = set()
                for idx, (person_id, kps) in enumerate(zip(track_ids, keypoints)):
                    bbox_size = bbox_sizes[idx] if idx < len(bbox_sizes) else 100.0
                    self.tracker.update(person_id, kps, bbox_size)
                    active_ids.add(person_id)

                # Send keypoint data for skeleton visualization
                self._send_keypoint_data(track_ids, keypoints, w, h)

                # Send person count immediately with keypoints (critical for visualizers)
                self._send_person_count(len(active_ids))

                # DEBUG: Log detection info every 30 frames
                if frame_count % 30 == 0:
                    print(f"[DEBUG] Frame {frame_count}: {len(active_ids)} people, IDs: {sorted(active_ids)}, keypoints shape: {keypoints.shape}")

                # Cleanup old tracks
                self.tracker.cleanup_old_tracks(active_ids)

                # Send periodic messages
                if current_time - self.last_message_time >= self.message_interval:
                    self._send_movement_report(active_ids, current_time)
                    self.last_message_time = current_time

            # Display results if enabled
            # NOTE: Disable on headless Raspberry Pi to save ~30% CPU
            if self.config.get('show_video', True):
                annotated_frame = results[0].plot()
                cv2.imshow('Dance Movement Detector', annotated_frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                # Still check for 'q' even without display (for SSH sessions with X forwarding)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    def _send_movement_report(self, active_ids: set, timestamp: float):
        """Calculate and send movement statistics"""
        if not active_ids:
            print(f"[{time.strftime('%H:%M:%S')}] No dancers detected")
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
        print(f"[{time.strftime('%H:%M:%S')}] People: {stats.person_count} | "
              f"Total: {stats.total_movement:.1f} | "
              f"Arms: {stats.arm_movement:.1f} | "
              f"Legs: {stats.leg_movement:.1f} | "
              f"Head: {stats.head_movement:.1f}")

        # Save to file if configured
        if self.config.get('save_to_file', False):
            self._save_stats(stats)

    def _send_keypoint_data(self, track_ids, keypoints, frame_width, frame_height):
        """Send raw keypoint data for skeleton visualization"""
        base_address = self.config.get('osc_base_address', '/dance')

        # Pre-calculate inverse dimensions to avoid repeated division (faster)
        inv_width = 1.0 / frame_width
        inv_height = 1.0 / frame_height

        # DEBUG: Verify we're iterating over all people
        num_people = len(track_ids)
        if self.config.get('debug_osc', False) and num_people > 1:
            print(f"[OSC] Sending keypoints for {num_people} people: IDs {track_ids.tolist()}")

        # Send keypoints for each person in BOTH formats for compatibility
        for person_id, kps in zip(track_ids, keypoints):
            # Normalize keypoints to 0-1 range based on frame dimensions
            # Use list comprehension for ~2x speed vs extend in loop
            normalized_kps = [
                val
                for kp in kps
                for val in (float(kp[0] * inv_width), float(kp[1] * inv_height), float(kp[2]))
            ]

            # Send to all OSC clients in BOTH formats
            for client in self.osc_clients:
                try:
                    # NEW FORMAT: /dance/pose/person/{id}/keypoints [x0, y0, c0, x1, y1, c1, ...]
                    # Used by blur_skeleton_visualizer
                    address = f"{base_address}/pose/person/{int(person_id)}/keypoints"
                    client.send_message(address, normalized_kps)

                    # OLD FORMAT: /pose/keypoints person_id x0 y0 c0 x1 y1 c1 ...
                    # Used by cosmic_skeleton, skeleton_visualizer
                    # Send NORMALIZED coordinates (0-1 range) for compatibility
                    old_format_kps = [int(person_id)] + normalized_kps
                    client.send_message("/pose/keypoints", old_format_kps)

                except Exception:
                    # Silently continue if visualizer is not running
                    pass

    def _send_person_count(self, count: int):
        """Send person count immediately (called every frame for visualizers)"""
        base_address = self.config.get('osc_base_address', '/dance')
        for client in self.osc_clients:
            try:
                client.send_message(f"{base_address}/person_count", int(count))
            except Exception:
                pass

    def _send_osc_messages(self, stats: MovementStats):
        """Send movement statistics via OSC to all destinations"""
        base_address = self.config.get('osc_base_address', '/dance')

        # Send to all OSC clients
        for client in self.osc_clients:
            # Convert to native Python types for OSC compatibility
            client.send_message(f"{base_address}/person_count", int(stats.person_count))
            client.send_message(f"{base_address}/total_movement", float(stats.total_movement))
            client.send_message(f"{base_address}/arm_movement", float(stats.arm_movement))
            client.send_message(f"{base_address}/leg_movement", float(stats.leg_movement))
            client.send_message(f"{base_address}/head_movement", float(stats.head_movement))

    def _save_stats(self, stats: MovementStats):
        """Save statistics to JSON file"""
        filename = self.config.get('output_file', 'movement_stats.json')

        try:
            with open(filename, 'a') as f:
                json.dump(stats.to_dict(), f)
                f.write('\n')
        except Exception as e:
            print(f"Error saving stats: {e}")


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
        print(f"Config file not found: {args.config}, using defaults")
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
