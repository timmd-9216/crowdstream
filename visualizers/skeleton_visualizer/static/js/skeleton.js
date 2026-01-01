/**
 * Skeleton Visualizer - Real-time YOLO Pose Detection
 */

class SkeletonVisualizer {
    constructor() {
        this.canvas = document.getElementById('skeleton-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.socket = null;

        // YOLO Pose connections (skeleton structure)
        this.connections = [
            // Head
            [0, 1], [0, 2],  // nose to eyes
            [1, 3], [2, 4],  // eyes to ears

            // Torso
            [5, 6],   // shoulders
            [5, 11],  // left shoulder to left hip
            [6, 12],  // right shoulder to right hip
            [11, 12], // hips

            // Arms
            [5, 7], [7, 9],   // left arm (shoulder -> elbow -> wrist)
            [6, 8], [8, 10],  // right arm

            // Legs
            [11, 13], [13, 15],  // left leg (hip -> knee -> ankle)
            [12, 14], [14, 16]   // right leg
        ];

        // Keypoint colors based on body part
        this.keypointColors = {
            0: '#ff6b6b',  // nose - head
            1: '#ff6b6b', 2: '#ff6b6b',  // eyes - head
            3: '#ff6b6b', 4: '#ff6b6b',  // ears - head
            5: '#4ecdc4', 6: '#4ecdc4',  // shoulders - torso
            7: '#ffe66d', 8: '#ffe66d',  // elbows - arms
            9: '#ffe66d', 10: '#ffe66d', // wrists - arms
            11: '#4ecdc4', 12: '#4ecdc4', // hips - torso
            13: '#95e1d3', 14: '#95e1d3', // knees - legs
            15: '#95e1d3', 16: '#95e1d3'  // ankles - legs
        };

        // FPS calculation
        this.lastFrameTime = Date.now();
        this.frameCount = 0;
        this.fps = 0;

        this.initCanvas();
        this.connectWebSocket();
        this.setupEventListeners();
    }

    initCanvas() {
        // Set canvas size based on typical video dimensions (16:9 aspect ratio)
        const containerWidth = this.canvas.parentElement.clientWidth - 40; // 40px for padding
        this.canvas.width = containerWidth;
        this.canvas.height = Math.floor(containerWidth * 9 / 16);

        console.log(`Canvas initialized: ${this.canvas.width}x${this.canvas.height}`);
        document.getElementById('canvas-size').textContent =
            `${this.canvas.width}x${this.canvas.height}`;

        // Clear canvas
        this.clearCanvas();
    }

    connectWebSocket() {
        console.log('🚀 Initializing WebSocket connection...');

        const wsUrl = `ws://${window.location.host}/ws`;
        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
            console.log('✅ Connected to skeleton server');
            this.updateConnectionStatus(true);
        };

        this.socket.onclose = () => {
            console.log('❌ Disconnected from skeleton server');
            this.updateConnectionStatus(false);
            this.clearCanvas();

            // Attempt to reconnect after 2 seconds
            setTimeout(() => {
                console.log('🔄 Attempting to reconnect...');
                this.connectWebSocket();
            }, 2000);
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleUpdate(data);
            } catch (e) {
                console.error('Failed to parse WebSocket message:', e);
            }
        };
    }

    handleUpdate(data) {
        // Parse if string
        if (typeof data === 'string') {
            try {
                data = JSON.parse(data);
            } catch (e) {
                console.error('Failed to parse data:', e);
                return;
            }
        }

        // Update person count
        const poses = data.poses || [];
        document.getElementById('person-count').textContent = poses.length;

        // Update last update time
        const now = new Date();
        document.getElementById('last-update').textContent = now.toLocaleTimeString();

        // Calculate FPS
        this.frameCount++;
        const currentTime = Date.now();
        if (currentTime - this.lastFrameTime >= 1000) {
            this.fps = this.frameCount;
            document.getElementById('fps').textContent = this.fps;
            this.frameCount = 0;
            this.lastFrameTime = currentTime;
        }

        // Draw skeletons
        this.drawSkeletons(poses);
    }

    clearCanvas() {
        this.ctx.fillStyle = '#1a1a1a';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }

    drawSkeletons(poses) {
        // Clear canvas
        this.clearCanvas();

        // Draw each person's skeleton
        for (const pose of poses) {
            this.drawSkeleton(pose.keypoints);
        }
    }

    drawSkeleton(keypoints) {
        if (!keypoints || keypoints.length === 0) {
            return;
        }

        // Normalize coordinates to canvas size
        // YOLO coordinates are typically in image space, we need to scale them
        const normalizedKeypoints = this.normalizeKeypoints(keypoints);

        // Draw connections (bones)
        this.ctx.lineWidth = 3;
        this.ctx.lineCap = 'round';

        for (const [start, end] of this.connections) {
            if (start >= normalizedKeypoints.length || end >= normalizedKeypoints.length) {
                continue;
            }

            const startKp = normalizedKeypoints[start];
            const endKp = normalizedKeypoints[end];

            // Only draw if both keypoints are visible (confidence > 0.5)
            if (startKp[2] > 0.5 && endKp[2] > 0.5) {
                // Use gradient for connection
                const gradient = this.ctx.createLinearGradient(
                    startKp[0], startKp[1],
                    endKp[0], endKp[1]
                );
                gradient.addColorStop(0, this.keypointColors[start]);
                gradient.addColorStop(1, this.keypointColors[end]);

                this.ctx.strokeStyle = gradient;
                this.ctx.beginPath();
                this.ctx.moveTo(startKp[0], startKp[1]);
                this.ctx.lineTo(endKp[0], endKp[1]);
                this.ctx.stroke();
            }
        }

        // Draw keypoints (joints)
        for (let i = 0; i < normalizedKeypoints.length; i++) {
            const kp = normalizedKeypoints[i];

            // Only draw if visible (confidence > 0.5)
            if (kp[2] > 0.5) {
                // Draw outer circle (glow)
                this.ctx.fillStyle = this.keypointColors[i] + '40'; // 25% opacity
                this.ctx.beginPath();
                this.ctx.arc(kp[0], kp[1], 8, 0, 2 * Math.PI);
                this.ctx.fill();

                // Draw inner circle
                this.ctx.fillStyle = this.keypointColors[i];
                this.ctx.beginPath();
                this.ctx.arc(kp[0], kp[1], 5, 0, 2 * Math.PI);
                this.ctx.fill();

                // Draw white center
                this.ctx.fillStyle = '#ffffff';
                this.ctx.beginPath();
                this.ctx.arc(kp[0], kp[1], 2, 0, 2 * Math.PI);
                this.ctx.fill();
            }
        }
    }

    normalizeKeypoints(keypoints) {
        // Keypoints from YOLO are typically normalized [0-1] or in pixel space
        // We need to scale them to canvas dimensions

        // First, find bounding box to auto-scale
        let minX = Infinity, maxX = -Infinity;
        let minY = Infinity, maxY = -Infinity;

        const visibleKeypoints = keypoints.filter(kp => kp[2] > 0.5);

        if (visibleKeypoints.length === 0) {
            return keypoints;
        }

        for (const kp of visibleKeypoints) {
            minX = Math.min(minX, kp[0]);
            maxX = Math.max(maxX, kp[0]);
            minY = Math.min(minY, kp[1]);
            maxY = Math.max(maxY, kp[1]);
        }

        const width = maxX - minX;
        const height = maxY - minY;

        // If coordinates are already normalized (0-1), scale to canvas
        if (maxX <= 1.0 && maxY <= 1.0) {
            return keypoints.map(kp => [
                kp[0] * this.canvas.width,
                kp[1] * this.canvas.height,
                kp[2]
            ]);
        }

        // If coordinates are in pixel space, scale proportionally
        // Add some padding (10% on each side)
        const padding = 0.1;
        const scale = Math.min(
            this.canvas.width * (1 - 2 * padding) / width,
            this.canvas.height * (1 - 2 * padding) / height
        );

        const offsetX = (this.canvas.width - width * scale) / 2 - minX * scale;
        const offsetY = (this.canvas.height - height * scale) / 2 - minY * scale;

        return keypoints.map(kp => [
            kp[0] * scale + offsetX,
            kp[1] * scale + offsetY,
            kp[2]
        ]);
    }

    updateConnectionStatus(connected) {
        const statusDot = document.getElementById('connection-status');
        const statusText = document.getElementById('connection-text');

        if (connected) {
            statusDot.classList.remove('disconnected');
            statusDot.classList.add('connected');
            statusText.textContent = 'Conectado';
        } else {
            statusDot.classList.remove('connected');
            statusDot.classList.add('disconnected');
            statusText.textContent = 'Desconectado';
        }
    }

    setupEventListeners() {
        // Reset button
        document.getElementById('reset-btn').addEventListener('click', () => {
            if (confirm('¿Estás seguro de que quieres reiniciar?')) {
                console.log('🔄 Resetting...');
                if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                    this.socket.send('reset');
                }
                this.clearCanvas();
                document.getElementById('person-count').textContent = '0';
            }
        });

        // Handle window resize
        window.addEventListener('resize', () => {
            this.initCanvas();
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('🎭 Skeleton Visualizer starting...');
    new SkeletonVisualizer();
});
