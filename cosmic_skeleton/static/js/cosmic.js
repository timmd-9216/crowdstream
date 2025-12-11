/**
 * Cosmic Skeleton Visualizer - Real-time YOLO Pose Detection with Space Effects
 */

class CosmicSkeletonVisualizer {
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

        // Cosmic keypoint colors
        this.keypointColors = {
            0: '#a020f0',  // nose - purple
            1: '#a020f0', 2: '#a020f0',  // eyes - purple
            3: '#a020f0', 4: '#a020f0',  // ears - purple
            5: '#00d4ff', 6: '#00d4ff',  // shoulders - cyan
            7: '#ffd700', 8: '#ffd700',  // elbows - gold
            9: '#ffd700', 10: '#ffd700', // wrists - gold
            11: '#00d4ff', 12: '#00d4ff', // hips - cyan
            13: '#00ff88', 14: '#00ff88', // knees - green
            15: '#00ff88', 16: '#00ff88'  // ankles - green
        };

        // FPS calculation
        this.lastFrameTime = Date.now();
        this.frameCount = 0;
        this.fps = 0;

        // Cosmic effects
        this.particles = [];
        this.trailPoints = [];
        this.glowIntensity = 0;

        this.initCanvas();
        this.connectWebSocket();
        this.setupEventListeners();
        this.createStars();
        this.createPlanets();
        this.animateBackground();
        this.startMeteorShower();
        this.startAsteroidField();
    }

    createStars() {
        const starfield = document.getElementById('starfield');
        // Create additional dynamic stars
        for (let i = 0; i < 100; i++) {
            const star = document.createElement('div');
            star.style.position = 'absolute';
            star.style.width = Math.random() * 3 + 'px';
            star.style.height = star.style.width;
            star.style.background = 'white';
            star.style.borderRadius = '50%';
            star.style.left = Math.random() * 100 + '%';
            star.style.top = Math.random() * 100 + '%';
            star.style.opacity = Math.random();
            star.style.boxShadow = `0 0 ${Math.random() * 10}px white`;
            star.style.animation = `twinkle ${Math.random() * 5 + 3}s infinite`;
            starfield.appendChild(star);
        }
    }

    createPlanets() {
        const planetsLayer = document.getElementById('planets-layer');
        const planets = [
            { class: 'jupiter', duration: 200, top: '15%', left: '10%' },
            { class: 'saturn', duration: 180, top: '60%', left: '75%' },
            { class: 'neptune', duration: 150, top: '25%', left: '85%' },
            { class: 'mars', duration: 120, top: '70%', left: '20%' },
            { class: 'venus', duration: 140, top: '40%', left: '5%' }
        ];

        planets.forEach(planetData => {
            const planet = document.createElement('div');
            planet.className = `planet ${planetData.class}`;
            planet.style.top = planetData.top;
            planet.style.left = planetData.left;
            planet.style.animationDuration = `${planetData.duration}s, 8s`;
            planetsLayer.appendChild(planet);
        });
    }

    startMeteorShower() {
        setInterval(() => {
            // Random chance to spawn meteor (30% each interval)
            if (Math.random() < 0.3) {
                this.createMeteor();
            }
            // Smaller chance for shooting star (10%)
            if (Math.random() < 0.1) {
                this.createShootingStar();
            }
        }, 3000); // Check every 3 seconds
    }

    createMeteor() {
        const meteorsLayer = document.getElementById('meteors-layer');
        const meteor = document.createElement('div');
        meteor.className = 'meteor';

        // Random starting position at top or left edge
        meteor.style.left = Math.random() * 50 + '%';
        meteor.style.top = Math.random() * 30 + '%';

        // Random duration for speed variation
        const duration = Math.random() * 2 + 1.5; // 1.5-3.5 seconds
        meteor.style.animationDuration = `${duration}s`;

        meteorsLayer.appendChild(meteor);

        // Remove after animation
        setTimeout(() => {
            meteor.remove();
        }, duration * 1000);
    }

    createShootingStar() {
        const meteorsLayer = document.getElementById('meteors-layer');
        const star = document.createElement('div');
        star.className = 'shooting-star';

        // Start from top portion of screen
        star.style.left = Math.random() * 40 + '%';
        star.style.top = Math.random() * 20 + '%';

        const duration = Math.random() * 1.5 + 1; // 1-2.5 seconds
        star.style.animationDuration = `${duration}s`;

        meteorsLayer.appendChild(star);

        setTimeout(() => {
            star.remove();
        }, duration * 1000);
    }

    startAsteroidField() {
        setInterval(() => {
            // Spawn asteroid every 15-25 seconds
            if (Math.random() < 0.3) {
                this.createAsteroid();
            }
        }, 8000);
    }

    createAsteroid() {
        const meteorsLayer = document.getElementById('meteors-layer');
        const asteroid = document.createElement('div');
        asteroid.className = 'asteroid';

        // Random size
        const size = Math.random() * 30 + 20; // 20-50px
        asteroid.style.width = size + 'px';
        asteroid.style.height = size + 'px';

        // Random vertical position
        asteroid.style.top = Math.random() * 80 + 10 + '%';

        // Random duration for slow drift
        const duration = Math.random() * 20 + 30; // 30-50 seconds
        asteroid.style.animationDuration = `${duration}s`;

        meteorsLayer.appendChild(asteroid);

        setTimeout(() => {
            asteroid.remove();
        }, duration * 1000);
    }

    animateBackground() {
        // Animate glow intensity
        this.glowIntensity = (Math.sin(Date.now() / 1000) + 1) / 2;
        requestAnimationFrame(() => this.animateBackground());
    }

    initCanvas() {
        const containerWidth = this.canvas.parentElement.clientWidth - 40;
        this.canvas.width = containerWidth;
        this.canvas.height = Math.floor(containerWidth * 9 / 16);

        console.log(`🌌 Cosmic canvas initialized: ${this.canvas.width}x${this.canvas.height}`);
        document.getElementById('canvas-size').textContent =
            `${this.canvas.width}x${this.canvas.height}`;

        this.clearCanvas();
    }

    connectWebSocket() {
        console.log('🚀 Initializing cosmic WebSocket connection...');

        const wsUrl = `ws://${window.location.host}/ws`;
        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
            console.log('✅ Connected to cosmic skeleton server');
            this.updateConnectionStatus(true);
        };

        this.socket.onclose = () => {
            console.log('❌ Disconnected from cosmic skeleton server');
            this.updateConnectionStatus(false);
            this.clearCanvas();

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
        if (typeof data === 'string') {
            try {
                data = JSON.parse(data);
            } catch (e) {
                console.error('Failed to parse data:', e);
                return;
            }
        }

        const poses = data.poses || [];

        // Debug logging for multiple people
        if (poses.length > 1) {
            console.log(`🎭 Received ${poses.length} people:`, poses.map(p => p.person_id));
        }

        document.getElementById('person-count').textContent = poses.length;

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

        // Draw cosmic skeletons
        this.drawCosmicSkeletons(poses);
    }

    clearCanvas() {
        // Deep space background with gradient
        const gradient = this.ctx.createRadialGradient(
            this.canvas.width / 2, this.canvas.height / 2, 0,
            this.canvas.width / 2, this.canvas.height / 2, this.canvas.width / 2
        );
        gradient.addColorStop(0, '#0a0a1a');
        gradient.addColorStop(1, '#000000');
        this.ctx.fillStyle = gradient;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }

    drawCosmicSkeletons(poses) {
        this.clearCanvas();

        // Debug logging for drawing
        if (poses.length > 1) {
            console.log(`🎨 Drawing ${poses.length} skeletons`);
        }

        // Draw each person's cosmic skeleton
        for (let i = 0; i < poses.length; i++) {
            console.log(`  Drawing person ${i}/${poses.length} (ID: ${poses[i].person_id})`);
            this.drawCosmicSkeleton(poses[i].keypoints, i, poses.length);
        }

        // Update and draw particles
        this.updateParticles();
    }

    drawCosmicSkeleton(keypoints, personIndex = 0, totalPeople = 1) {
        if (!keypoints || keypoints.length === 0) {
            return;
        }

        const normalizedKeypoints = this.normalizeKeypoints(keypoints, personIndex, totalPeople);

        // Draw glowing connections (cosmic energy beams)
        this.ctx.lineWidth = 4;
        this.ctx.lineCap = 'round';

        for (const [start, end] of this.connections) {
            if (start >= normalizedKeypoints.length || end >= normalizedKeypoints.length) {
                continue;
            }

            const startKp = normalizedKeypoints[start];
            const endKp = normalizedKeypoints[end];

            if (startKp[2] > 0.5 && endKp[2] > 0.5) {
                // Draw outer glow
                this.ctx.shadowBlur = 20 + (this.glowIntensity * 10);
                this.ctx.shadowColor = this.keypointColors[start];

                // Main beam with gradient
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

                // Add energy particles along the beam
                if (Math.random() < 0.1) {
                    const t = Math.random();
                    const x = startKp[0] + (endKp[0] - startKp[0]) * t;
                    const y = startKp[1] + (endKp[1] - startKp[1]) * t;
                    this.addParticle(x, y, this.keypointColors[start]);
                }
            }
        }

        // Reset shadow for keypoints
        this.ctx.shadowBlur = 0;

        // Draw cosmic keypoints (energy nodes)
        for (let i = 0; i < normalizedKeypoints.length; i++) {
            const kp = normalizedKeypoints[i];

            if (kp[2] > 0.5) {
                this.drawCosmicKeypoint(kp[0], kp[1], this.keypointColors[i]);
            }
        }
    }

    drawCosmicKeypoint(x, y, color) {
        const baseSize = 6;
        const glowSize = baseSize + (this.glowIntensity * 4);

        // Outer glow rings
        for (let i = 3; i > 0; i--) {
            this.ctx.beginPath();
            this.ctx.arc(x, y, glowSize + (i * 3), 0, 2 * Math.PI);
            this.ctx.fillStyle = color + Math.floor((0.1 / i) * 255).toString(16).padStart(2, '0');
            this.ctx.fill();
        }

        // Main keypoint with gradient
        const gradient = this.ctx.createRadialGradient(x, y, 0, x, y, baseSize);
        gradient.addColorStop(0, '#ffffff');
        gradient.addColorStop(0.4, color);
        gradient.addColorStop(1, color + '80');

        this.ctx.beginPath();
        this.ctx.arc(x, y, baseSize, 0, 2 * Math.PI);
        this.ctx.fillStyle = gradient;
        this.ctx.fill();

        // Bright center
        this.ctx.beginPath();
        this.ctx.arc(x, y, 2, 0, 2 * Math.PI);
        this.ctx.fillStyle = '#ffffff';
        this.ctx.fill();
    }

    addParticle(x, y, color) {
        this.particles.push({
            x: x,
            y: y,
            vx: (Math.random() - 0.5) * 2,
            vy: (Math.random() - 0.5) * 2,
            color: color,
            life: 1.0,
            size: Math.random() * 3 + 1
        });
    }

    updateParticles() {
        // Update and draw particles
        this.particles = this.particles.filter(p => {
            p.x += p.vx;
            p.y += p.vy;
            p.life -= 0.02;
            p.size *= 0.98;

            if (p.life > 0) {
                this.ctx.beginPath();
                this.ctx.arc(p.x, p.y, p.size, 0, 2 * Math.PI);
                this.ctx.fillStyle = p.color + Math.floor(p.life * 255).toString(16).padStart(2, '0');
                this.ctx.fill();
                return true;
            }
            return false;
        });
    }

    normalizeKeypoints(keypoints, personIndex = 0, totalPeople = 1) {
        let minX = Infinity, maxX = -Infinity;
        let minY = Infinity, maxY = -Infinity;

        const visibleKeypoints = keypoints.filter(kp => kp[2] > 0.5);

        if (visibleKeypoints.length === 0) {
            console.warn(`⚠️  Person ${personIndex}: No visible keypoints`);
            return keypoints;
        }

        if (totalPeople > 1) {
            console.log(`  🔧 Normalizing person ${personIndex}/${totalPeople}, visible keypoints: ${visibleKeypoints.length}`);
        }

        for (const kp of visibleKeypoints) {
            minX = Math.min(minX, kp[0]);
            maxX = Math.max(maxX, kp[0]);
            minY = Math.min(minY, kp[1]);
            maxY = Math.max(maxY, kp[1]);
        }

        const width = maxX - minX;
        const height = maxY - minY;

        // If already normalized (0-1 range), just scale to canvas
        if (maxX <= 1.0 && maxY <= 1.0) {
            return keypoints.map(kp => [
                kp[0] * this.canvas.width,
                kp[1] * this.canvas.height,
                kp[2]
            ]);
        }

        // Calculate section width for multiple people
        const sectionWidth = this.canvas.width / totalPeople;
        const sectionPadding = 0.1;

        // Calculate scale to fit person in their section
        const availableWidth = sectionWidth * (1 - 2 * sectionPadding);
        const availableHeight = this.canvas.height * (1 - 2 * sectionPadding);

        const scale = Math.min(
            availableWidth / width,
            availableHeight / height
        );

        // Center person in their section
        const sectionCenterX = sectionWidth * (personIndex + 0.5);
        const sectionCenterY = this.canvas.height / 2;

        const offsetX = sectionCenterX - (minX + width / 2) * scale;
        const offsetY = sectionCenterY - (minY + height / 2) * scale;

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
        document.getElementById('reset-btn').addEventListener('click', () => {
            if (confirm('¿Estás seguro de que quieres reiniciar?')) {
                console.log('🔄 Resetting cosmic visualizer...');
                if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                    this.socket.send('reset');
                }
                this.clearCanvas();
                this.particles = [];
                document.getElementById('person-count').textContent = '0';
            }
        });

        window.addEventListener('resize', () => {
            this.initCanvas();
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('🌌 Cosmic Skeleton Visualizer starting...');
    new CosmicSkeletonVisualizer();
});
