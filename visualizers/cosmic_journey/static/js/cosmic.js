// Cosmic Journey Visualizer using Three.js

class CosmicVisualizer {
    constructor() {
        this.socket = null;
        this.scene = null;
        this.camera = null;
        this.renderer = null;

        // Visual elements
        this.galaxy = null;
        this.asteroids = [];
        this.nebulae = [];
        this.planets = [];
        this.energyField = null;

        // Visualization parameters
        this.params = {
            galaxyRotation: 0.0,
            nebulaDensity: 0.0,
            asteroidSpeed: 1.0,
            cosmicZoom: 1.0,
            starBrightness: 0.5,
            planetOrbitSpeed: 0.0,
            cosmicEnergy: 0.0
        };

        // Animation state
        this.time = 0;
        this.galaxyAngle = 0;

        this.init();
    }

    init() {
        this.setupThreeJS();
        this.createGalaxy();
        this.createAsteroidField();
        this.createNebulae();
        this.createPlanets();
        this.createEnergyField();
        this.connectWebSocket();
        this.animate();
    }

    setupThreeJS() {
        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x000011);
        this.scene.fog = new THREE.FogExp2(0x000011, 0.0002);

        // Camera
        this.camera = new THREE.PerspectiveCamera(
            60,
            window.innerWidth / window.innerHeight,
            0.1,
            5000
        );
        this.camera.position.set(0, 100, 200);
        this.camera.lookAt(0, 0, 0);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        document.getElementById('canvas-container').appendChild(this.renderer.domElement);

        // Lighting
        const ambientLight = new THREE.AmbientLight(0x404060, 0.5);
        this.scene.add(ambientLight);

        const pointLight = new THREE.PointLight(0xffffff, 1, 2000);
        pointLight.position.set(0, 0, 0);
        this.scene.add(pointLight);

        // Window resize
        window.addEventListener('resize', () => {
            this.camera.aspect = window.innerWidth / window.innerHeight;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(window.innerWidth, window.innerHeight);
        });
    }

    createGalaxy() {
        const galaxyGeometry = new THREE.BufferGeometry();
        const galaxyVertices = [];
        const galaxyColors = [];

        // Spiral galaxy arms
        const arms = 3;
        const particlesPerArm = 3000;

        for (let arm = 0; arm < arms; arm++) {
            for (let i = 0; i < particlesPerArm; i++) {
                const t = i / particlesPerArm;
                const angle = (arm / arms) * Math.PI * 2 + t * Math.PI * 4;
                const radius = t * 150;

                const x = Math.cos(angle) * radius + (Math.random() - 0.5) * 10;
                const y = (Math.random() - 0.5) * 5;
                const z = Math.sin(angle) * radius + (Math.random() - 0.5) * 10;

                galaxyVertices.push(x, y, z);

                // Color gradient from center (blue) to edge (purple)
                const r = 0.3 + t * 0.5;
                const g = 0.2 + t * 0.3;
                const b = 0.8 + t * 0.2;
                galaxyColors.push(r, g, b);
            }
        }

        galaxyGeometry.setAttribute('position', new THREE.Float32BufferAttribute(galaxyVertices, 3));
        galaxyGeometry.setAttribute('color', new THREE.Float32BufferAttribute(galaxyColors, 3));

        const galaxyMaterial = new THREE.PointsMaterial({
            size: 2,
            vertexColors: true,
            transparent: true,
            opacity: 0.8,
            blending: THREE.AdditiveBlending,
            sizeAttenuation: true
        });

        this.galaxy = new THREE.Points(galaxyGeometry, galaxyMaterial);
        this.scene.add(this.galaxy);
    }

    createAsteroidField() {
        const asteroidGeometry = new THREE.SphereGeometry(0.5, 6, 6);

        for (let i = 0; i < 200; i++) {
            const material = new THREE.MeshStandardMaterial({
                color: new THREE.Color().setHSL(0.1, 0.5, 0.3 + Math.random() * 0.2),
                roughness: 0.8,
                metalness: 0.2
            });

            const asteroid = new THREE.Mesh(asteroidGeometry, material);

            // Random position in a ring around the galaxy
            const angle = Math.random() * Math.PI * 2;
            const radius = 180 + Math.random() * 100;
            asteroid.position.set(
                Math.cos(angle) * radius,
                (Math.random() - 0.5) * 50,
                Math.sin(angle) * radius
            );

            asteroid.userData = {
                velocity: new THREE.Vector3(
                    (Math.random() - 0.5) * 0.5,
                    (Math.random() - 0.5) * 0.2,
                    (Math.random() - 0.5) * 0.5
                ),
                rotationSpeed: new THREE.Vector3(
                    Math.random() * 0.02,
                    Math.random() * 0.02,
                    Math.random() * 0.02
                )
            };

            this.asteroids.push(asteroid);
            this.scene.add(asteroid);
        }
    }

    createNebulae() {
        const nebulaColors = [
            0x8b00ff, // Purple
            0x00ffff, // Cyan
            0xff00ff, // Magenta
            0x0080ff, // Blue
            0xff0080  // Pink
        ];

        for (let i = 0; i < 5; i++) {
            const geometry = new THREE.SphereGeometry(40, 32, 32);
            const material = new THREE.MeshBasicMaterial({
                color: nebulaColors[i],
                transparent: true,
                opacity: 0.0,
                blending: THREE.AdditiveBlending,
                side: THREE.BackSide
            });

            const nebula = new THREE.Mesh(geometry, material);

            const angle = (i / 5) * Math.PI * 2;
            const radius = 120;
            nebula.position.set(
                Math.cos(angle) * radius,
                (Math.random() - 0.5) * 40,
                Math.sin(angle) * radius
            );

            this.nebulae.push(nebula);
            this.scene.add(nebula);
        }
    }

    createPlanets() {
        const planetData = [
            { radius: 8, color: 0xff6b6b, distance: 80, speed: 0.5 },
            { radius: 12, color: 0x4ecdc4, distance: 110, speed: 0.3 },
            { radius: 6, color: 0xffe66d, distance: 140, speed: 0.2 },
            { radius: 10, color: 0x95e1d3, distance: 170, speed: 0.15 }
        ];

        planetData.forEach((data, index) => {
            const geometry = new THREE.SphereGeometry(data.radius, 32, 32);
            const material = new THREE.MeshStandardMaterial({
                color: data.color,
                emissive: data.color,
                emissiveIntensity: 0.3,
                roughness: 0.5,
                metalness: 0.5
            });

            const planet = new THREE.Mesh(geometry, material);

            // Add ring to some planets
            if (index % 2 === 0) {
                const ringGeometry = new THREE.RingGeometry(data.radius * 1.5, data.radius * 2, 32);
                const ringMaterial = new THREE.MeshBasicMaterial({
                    color: data.color,
                    side: THREE.DoubleSide,
                    transparent: true,
                    opacity: 0.5
                });
                const ring = new THREE.Mesh(ringGeometry, ringMaterial);
                ring.rotation.x = Math.PI / 2;
                planet.add(ring);
            }

            planet.userData = {
                distance: data.distance,
                speed: data.speed,
                angle: (index / planetData.length) * Math.PI * 2
            };

            this.planets.push(planet);
            this.scene.add(planet);
        });
    }

    createEnergyField() {
        const geometry = new THREE.SphereGeometry(250, 64, 64);
        const material = new THREE.ShaderMaterial({
            uniforms: {
                time: { value: 0 },
                energy: { value: 0.0 }
            },
            vertexShader: `
                varying vec3 vNormal;
                varying vec3 vPosition;
                void main() {
                    vNormal = normalize(normalMatrix * normal);
                    vPosition = position;
                    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
                }
            `,
            fragmentShader: `
                uniform float time;
                uniform float energy;
                varying vec3 vNormal;
                varying vec3 vPosition;

                void main() {
                    float intensity = pow(0.7 - dot(vNormal, vec3(0, 0, 1.0)), 2.0);
                    vec3 glow = vec3(0.5, 0.2, 1.0) * intensity * energy;
                    gl_FragColor = vec4(glow, intensity * energy * 0.5);
                }
            `,
            transparent: true,
            blending: THREE.AdditiveBlending,
            side: THREE.BackSide
        });

        this.energyField = new THREE.Mesh(geometry, material);
        this.scene.add(this.energyField);
    }

    connectWebSocket() {
        console.log('🌌 Initializing WebSocket connection...');
        this.socket = io({
            transports: ['websocket', 'polling']
        });

        this.socket.on('connect', () => {
            console.log('✅ Connected to cosmic visualizer');
            this.updateStatus('Conectado', true);
        });

        this.socket.on('disconnect', () => {
            console.log('❌ Disconnected from cosmic visualizer');
            this.updateStatus('Desconectado', false);
        });

        this.socket.on('connect_error', (error) => {
            console.error('❌ Connection error:', error);
        });

        this.socket.on('update', (data) => {
            console.log('🌌 Received update:', data);
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
        this.params.galaxyRotation = this.lerp(this.params.galaxyRotation, data.galaxy_rotation, 0.1);
        this.params.nebulaDensity = this.lerp(this.params.nebulaDensity, data.nebula_density, 0.1);
        this.params.asteroidSpeed = this.lerp(this.params.asteroidSpeed, data.asteroid_speed, 0.1);
        this.params.cosmicZoom = this.lerp(this.params.cosmicZoom, data.cosmic_zoom, 0.05);
        this.params.starBrightness = this.lerp(this.params.starBrightness, data.star_brightness, 0.1);
        this.params.planetOrbitSpeed = this.lerp(this.params.planetOrbitSpeed, data.planet_orbit_speed, 0.1);
        this.params.cosmicEnergy = this.lerp(this.params.cosmicEnergy, data.cosmic_energy, 0.1);

        // Update UI
        this.updateUI(data);
    }

    lerp(start, end, factor) {
        return start + (end - start) * factor;
    }

    updateUI(data) {
        const galaxyEl = document.getElementById('galaxy-value');
        const asteroidEl = document.getElementById('asteroid-value');
        const zoomEl = document.getElementById('zoom-value');
        const energyEl = document.getElementById('energy-value');
        const nebulaEl = document.getElementById('nebula-value');
        const orbitEl = document.getElementById('orbit-value');

        if (galaxyEl) galaxyEl.textContent = data.galaxy_rotation.toFixed(2);
        if (asteroidEl) asteroidEl.textContent = data.asteroid_speed.toFixed(2);
        if (zoomEl) zoomEl.textContent = data.cosmic_zoom.toFixed(1) + 'x';
        if (energyEl) energyEl.textContent = (data.cosmic_energy * 100).toFixed(0) + '%';
        if (nebulaEl) nebulaEl.textContent = (data.nebula_density * 100).toFixed(0) + '%';
        if (orbitEl) orbitEl.textContent = data.planet_orbit_speed.toFixed(2);
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        this.time += 0.016;

        // Rotate galaxy
        this.galaxyAngle += this.params.galaxyRotation * 0.001;
        this.galaxy.rotation.y = this.galaxyAngle;

        // Update galaxy brightness
        this.galaxy.material.opacity = 0.5 + this.params.starBrightness * 0.5;

        // Update asteroids
        this.asteroids.forEach(asteroid => {
            asteroid.position.add(asteroid.userData.velocity.clone().multiplyScalar(this.params.asteroidSpeed * 0.1));
            asteroid.rotation.x += asteroid.userData.rotationSpeed.x;
            asteroid.rotation.y += asteroid.userData.rotationSpeed.y;
            asteroid.rotation.z += asteroid.userData.rotationSpeed.z;

            // Wrap around
            const maxDist = 300;
            if (asteroid.position.length() > maxDist) {
                const angle = Math.random() * Math.PI * 2;
                const radius = 180;
                asteroid.position.set(
                    Math.cos(angle) * radius,
                    (Math.random() - 0.5) * 50,
                    Math.sin(angle) * radius
                );
            }
        });

        // Update nebulae
        this.nebulae.forEach((nebula, index) => {
            nebula.material.opacity = this.params.nebulaDensity * 0.3;
            nebula.rotation.y += 0.0005;
            const pulse = Math.sin(this.time + index) * 0.1 + 1;
            nebula.scale.setScalar(pulse);
        });

        // Update planets
        this.planets.forEach(planet => {
            planet.userData.angle += planet.userData.speed * this.params.planetOrbitSpeed * 0.01;
            planet.position.x = Math.cos(planet.userData.angle) * planet.userData.distance;
            planet.position.z = Math.sin(planet.userData.angle) * planet.userData.distance;
            planet.rotation.y += 0.01;
        });

        // Update energy field
        this.energyField.material.uniforms.time.value = this.time;
        this.energyField.material.uniforms.energy.value = this.params.cosmicEnergy;
        this.energyField.rotation.y += 0.0002;

        // Update camera zoom
        const targetZ = 200 / this.params.cosmicZoom;
        this.camera.position.z += (targetZ - this.camera.position.z) * 0.05;

        // Render
        this.renderer.render(this.scene, this.camera);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new CosmicVisualizer();
});
