// Space Journey Visualizer using Three.js
// Driven by dance movement data

class SpaceVisualizer {
    constructor() {
        this.socket = null;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.particles = null;
        this.nebulae = [];
        this.planets = [];

        // Visualization parameters (updated via OSC)
        this.params = {
            speed: 1.0,
            particleCount: 1000,
            colorIntensity: 0.5,
            rotationSpeed: 0.0,
            warpFactor: 0.0,
            nebulaIntensity: 0.0,
            starSize: 1.0
        };

        // Animation state
        this.time = 0;
        this.cameraRotation = 0;

        this.init();
    }

    init() {
        this.setupThreeJS();
        this.createStarField();
        this.createNebulae();
        this.createPlanets();
        this.connectWebSocket();
        this.animate();
        this.setupEventListeners();
    }

    setupThreeJS() {
        // Scene
        this.scene = new THREE.Scene();
        this.scene.fog = new THREE.FogExp2(0x000000, 0.0003);

        // Camera
        this.camera = new THREE.PerspectiveCamera(
            75,
            window.innerWidth / window.innerHeight,
            0.1,
            10000
        );
        this.camera.position.z = 5;

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        document.getElementById('canvas-container').appendChild(this.renderer.domElement);

        // Lighting
        const ambientLight = new THREE.AmbientLight(0x404040);
        this.scene.add(ambientLight);

        const pointLight = new THREE.PointLight(0xffffff, 1, 1000);
        pointLight.position.set(0, 0, 0);
        this.scene.add(pointLight);
    }

    createStarField() {
        const geometry = new THREE.BufferGeometry();
        const vertices = [];
        const colors = [];
        const baseColors = []; // Store original colors for intensity changes
        const sizes = [];

        for (let i = 0; i < 5000; i++) {
            // Distribute stars in a tunnel shape
            const theta = Math.random() * Math.PI * 2;
            const radius = 50 + Math.random() * 100;
            const z = -Math.random() * 2000;

            vertices.push(
                Math.cos(theta) * radius,
                Math.sin(theta) * radius,
                z
            );

            // Random star colors (white, blue, red, yellow)
            let r, g, b;
            const colorChoice = Math.random();
            if (colorChoice < 0.7) {
                r = 1; g = 1; b = 1; // White
            } else if (colorChoice < 0.85) {
                r = 0.5; g = 0.7; b = 1; // Blue
            } else if (colorChoice < 0.95) {
                r = 1; g = 0.8; b = 0.5; // Yellow
            } else {
                r = 1; g = 0.5; b = 0.5; // Red
            }

            colors.push(r, g, b);
            baseColors.push(r, g, b); // Store base color

            sizes.push(Math.random() * 3 + 1);
        }

        geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
        geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
        geometry.setAttribute('size', new THREE.Float32BufferAttribute(sizes, 1));

        const material = new THREE.PointsMaterial({
            size: 2,
            vertexColors: true,
            transparent: true,
            opacity: 0.8,
            sizeAttenuation: true,
            blending: THREE.AdditiveBlending
        });

        this.particles = new THREE.Points(geometry, material);
        this.baseColors = baseColors; // Store for later use
        this.scene.add(this.particles);
    }

    createNebulae() {
        // Create colorful nebula clouds
        const nebulaColors = [
            0xff0080, // Pink
            0x00ffff, // Cyan
            0xff00ff, // Magenta
            0x00ff80, // Green-cyan
            0xff8000  // Orange
        ];

        for (let i = 0; i < 5; i++) {
            const geometry = new THREE.SphereGeometry(30, 32, 32);
            const material = new THREE.MeshBasicMaterial({
                color: nebulaColors[i],
                transparent: true,
                opacity: 0.0,
                blending: THREE.AdditiveBlending
            });

            const nebula = new THREE.Mesh(geometry, material);

            // Position nebulae along the path
            const angle = (i / 5) * Math.PI * 2;
            nebula.position.set(
                Math.cos(angle) * 80,
                Math.sin(angle) * 80,
                -200 - i * 300
            );

            this.nebulae.push(nebula);
            this.scene.add(nebula);
        }
    }

    createPlanets() {
        // Create planets scattered through space
        const planetData = [
            { radius: 10, color: 0xff4444, distance: -300, angle: 0.5 },
            { radius: 15, color: 0x4444ff, distance: -600, angle: 2.0 },
            { radius: 8, color: 0x44ff44, distance: -900, angle: 4.0 },
            { radius: 12, color: 0xffaa44, distance: -1200, angle: 1.5 },
            { radius: 20, color: 0xaa44ff, distance: -1500, angle: 3.5 }
        ];

        planetData.forEach(data => {
            const geometry = new THREE.SphereGeometry(data.radius, 32, 32);
            const material = new THREE.MeshPhongMaterial({
                color: data.color,
                emissive: data.color,
                emissiveIntensity: 0.2,
                shininess: 100
            });

            const planet = new THREE.Mesh(geometry, material);
            planet.position.set(
                Math.cos(data.angle) * 60,
                Math.sin(data.angle) * 60,
                data.distance
            );

            // Add glow effect
            const glowGeometry = new THREE.SphereGeometry(data.radius * 1.3, 32, 32);
            const glowMaterial = new THREE.MeshBasicMaterial({
                color: data.color,
                transparent: true,
                opacity: 0.2,
                blending: THREE.AdditiveBlending
            });
            const glow = new THREE.Mesh(glowGeometry, glowMaterial);
            planet.add(glow);

            this.planets.push({ mesh: planet, rotationSpeed: Math.random() * 0.02 });
            this.scene.add(planet);
        });
    }

    connectWebSocket() {
        this.socket = io();

        this.socket.on('connect', () => {
            console.log('Connected to visualizer server');
            this.updateStatus('Conectado', true);
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from visualizer server');
            this.updateStatus('Desconectado', false);
        });

        this.socket.on('update', (data) => {
            this.handleUpdate(data);
        });
    }

    updateStatus(text, connected) {
        const statusElement = document.getElementById('status');
        statusElement.textContent = text;
        statusElement.className = 'status ' + (connected ? 'connected' : 'disconnected');
    }

    handleUpdate(data) {
        // Smoothly interpolate parameters
        this.params.speed = this.lerp(this.params.speed, data.speed, 0.1);
        this.params.colorIntensity = this.lerp(this.params.colorIntensity, data.color_intensity, 0.1);
        this.params.rotationSpeed = this.lerp(this.params.rotationSpeed, data.rotation_speed, 0.1);
        this.params.warpFactor = this.lerp(this.params.warpFactor, data.warp_factor, 0.1);
        this.params.nebulaIntensity = this.lerp(this.params.nebulaIntensity, data.nebula_intensity, 0.1);
        this.params.starSize = this.lerp(this.params.starSize, data.star_size, 0.1);

        // Update particle count (less frequent updates)
        if (Math.abs(this.params.particleCount - data.particle_count) > 200) {
            this.params.particleCount = data.particle_count;
            this.updateParticleCount();
        }

        // Update UI
        this.updateUI(data);
    }

    lerp(start, end, factor) {
        return start + (end - start) * factor;
    }

    updateParticleCount() {
        // Recreate star field with new particle count
        this.scene.remove(this.particles);
        this.createStarField();
    }

    updateUI(data) {
        document.getElementById('speed-value').textContent = data.speed.toFixed(2);
        document.getElementById('particles-value').textContent = data.particle_count;
        document.getElementById('warp-value').textContent = (data.warp_factor * 100).toFixed(0) + '%';
        document.getElementById('color-value').textContent = (data.color_intensity * 100).toFixed(0) + '%';
        document.getElementById('people-value').textContent = data.person_count;

        // Update rotation indicator (for debugging)
        const rotationElement = document.getElementById('rotation-value');
        if (rotationElement) {
            rotationElement.textContent = data.rotation_speed.toFixed(2);
        }
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        this.time += 0.016; // Roughly 60fps

        // Move stars towards camera (travel through space)
        const positions = this.particles.geometry.attributes.position.array;
        for (let i = 0; i < positions.length; i += 3) {
            positions[i + 2] += this.params.speed * 0.5;

            // Warp effect: stretch stars
            if (this.params.warpFactor > 0.3) {
                positions[i + 2] += this.params.warpFactor * 2;
            }

            // Reset stars that passed the camera
            if (positions[i + 2] > 10) {
                positions[i + 2] = -2000;
            }
        }
        this.particles.geometry.attributes.position.needsUpdate = true;

        // Update particle colors based on color intensity
        // Use base colors to avoid accumulation
        const colors = this.particles.geometry.attributes.color.array;
        const boost = this.params.colorIntensity;
        for (let i = 0; i < colors.length; i += 3) {
            // Apply boost to base colors to get more vibrant colors
            colors[i] = Math.min(this.baseColors[i] * (0.5 + boost), 1);
            colors[i + 1] = Math.min(this.baseColors[i + 1] * (0.5 + boost), 1);
            colors[i + 2] = Math.min(this.baseColors[i + 2] * (0.5 + boost), 1);
        }
        this.particles.geometry.attributes.color.needsUpdate = true;

        // Update particle size based on starSize parameter
        this.particles.material.size = 2 * this.params.starSize;

        // Camera rotation
        // Only rotate if there's actual rotation speed (avoid drift when no movement)
        if (this.params.rotationSpeed > 0.1) {
            this.cameraRotation += this.params.rotationSpeed * 0.02;
            this.camera.position.x = Math.sin(this.cameraRotation) * 8;
            this.camera.position.y = Math.cos(this.cameraRotation) * 8;
            this.camera.lookAt(0, 0, -100);
        } else {
            // Smoothly return to center when no rotation
            this.camera.position.x *= 0.95;
            this.camera.position.y *= 0.95;
            this.camera.lookAt(0, 0, -100);
        }

        // Update nebulae
        this.nebulae.forEach((nebula, index) => {
            nebula.position.z += this.params.speed * 0.3;

            if (nebula.position.z > 100) {
                nebula.position.z = -2000;
            }

            // Opacity based on nebula intensity
            nebula.material.opacity = this.params.nebulaIntensity * 0.3;

            // Rotate and pulse
            nebula.rotation.y += 0.001;
            nebula.rotation.x += 0.0005;
            const pulse = Math.sin(this.time + index) * 0.1 + 1;
            nebula.scale.setScalar(pulse);
        });

        // Update planets
        this.planets.forEach(planetData => {
            const planet = planetData.mesh;
            planet.position.z += this.params.speed * 0.2;

            if (planet.position.z > 50) {
                planet.position.z = -2000;
            }

            // Rotate planets
            planet.rotation.y += planetData.rotationSpeed;

            // Enhance glow based on color intensity
            if (planet.children[0]) {
                planet.children[0].material.opacity = 0.2 + this.params.colorIntensity * 0.3;
            }
        });

        // Render
        this.renderer.render(this.scene, this.camera);
    }

    setupEventListeners() {
        window.addEventListener('resize', () => {
            this.camera.aspect = window.innerWidth / window.innerHeight;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(window.innerWidth, window.innerHeight);
        });

        // Fullscreen toggle
        document.getElementById('fullscreen-btn').addEventListener('click', () => {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen();
            } else {
                document.exitFullscreen();
            }
        });

        // Toggle UI
        document.getElementById('toggle-ui-btn').addEventListener('click', () => {
            const ui = document.getElementById('ui-panel');
            ui.style.display = ui.style.display === 'none' ? 'block' : 'none';
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new SpaceVisualizer();
});
