// Blur Skeleton Visualizer Client

class BlurVisualizer {
    constructor() {
        this.ws = null;
        this.videoFrame = document.getElementById('videoFrame');
        this.statusElement = document.getElementById('status');
        this.fpsElement = document.getElementById('fps');

        this.frameCount = 0;
        this.lastFpsUpdate = Date.now();

        this.connect();
        this.startFpsCounter();
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.updateStatus('Connected', true);
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this.handleMessage(message);
            } catch (error) {
                console.error('Error parsing message:', error);
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateStatus('Error', false);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.updateStatus('Disconnected', false);

            // Reconnect after 2 seconds
            setTimeout(() => this.connect(), 2000);
        };
    }

    handleMessage(message) {
        if (message.type === 'frame') {
            this.displayFrame(message.data);
            this.frameCount++;
        }
    }

    displayFrame(frameData) {
        // Display base64 encoded JPEG
        this.videoFrame.src = `data:image/jpeg;base64,${frameData}`;
    }

    updateStatus(text, connected) {
        this.statusElement.textContent = text;
        this.statusElement.className = connected ? 'connected' : 'disconnected';
    }

    startFpsCounter() {
        setInterval(() => {
            const now = Date.now();
            const elapsed = (now - this.lastFpsUpdate) / 1000;
            const fps = Math.round(this.frameCount / elapsed);

            this.fpsElement.textContent = fps;

            this.frameCount = 0;
            this.lastFpsUpdate = now;
        }, 1000);
    }
}

// Initialize visualizer when page loads
document.addEventListener('DOMContentLoaded', () => {
    new BlurVisualizer();
});
