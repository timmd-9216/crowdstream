// Service Controller - Frontend JavaScript

class ServiceController {
    constructor() {
        this.socket = null;
        this.services = [];
        this.currentLogService = null;
        this.init();
    }

    init() {
        this.connectWebSocket();
        this.loadServices();
        this.setupEventListeners();
    }

    connectWebSocket() {
        this.socket = io();

        this.socket.on('connect', () => {
            console.log('Connected to controller server');
            this.updateConnectionStatus(true);
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from controller server');
            this.updateConnectionStatus(false);
        });

        this.socket.on('status_update', (statuses) => {
            this.handleStatusUpdate(statuses);
        });
    }

    updateConnectionStatus(connected) {
        const indicator = document.getElementById('status-indicator');
        const text = document.getElementById('status-text');

        if (connected) {
            indicator.classList.remove('disconnected');
            indicator.classList.add('connected');
            text.textContent = 'Conectado';
        } else {
            indicator.classList.remove('connected');
            indicator.classList.add('disconnected');
            text.textContent = 'Desconectado';
        }
    }

    async loadServices() {
        try {
            const response = await fetch('/api/services');
            const data = await response.json();
            this.services = data;
            this.renderServices();
        } catch (error) {
            console.error('Error loading services:', error);
        }
    }

    renderServices() {
        const grid = document.getElementById('services-grid');
        grid.innerHTML = '';

        this.services.forEach(serviceData => {
            const card = this.createServiceCard(serviceData);
            grid.appendChild(card);
        });
    }

    createServiceCard(serviceData) {
        const { config, status } = serviceData;

        const card = document.createElement('div');
        card.className = `service-card status-${status.status}`;
        card.id = `service-${config.name}`;

        const statusClass = status.status;
        const statusText = this.getStatusText(status.status);

        card.innerHTML = `
            <div class="service-header">
                <div class="service-title">
                    <h3>${config.name}</h3>
                    <p>${config.description}</p>
                </div>
                <span class="service-status-badge ${statusClass}">${statusText}</span>
            </div>

            <div class="service-stats">
                <div class="stat-item">
                    <div class="stat-label">Puerto</div>
                    <div class="stat-value">${config.port}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">PID</div>
                    <div class="stat-value">${status.pid || 'N/A'}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Tiempo Activo</div>
                    <div class="stat-value">${status.uptime_str || '0s'}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">CPU / RAM</div>
                    <div class="stat-value">${status.cpu_percent.toFixed(1)}% / ${status.memory_mb.toFixed(0)}MB</div>
                </div>
            </div>

            ${status.error_message ? `
                <div class="error-message">
                    ⚠️ ${status.error_message}
                </div>
            ` : ''}

            <div class="service-actions">
                <button class="service-btn start" onclick="controller.startService('${config.name}')"
                    ${status.status === 'running' || status.status === 'starting' ? 'disabled' : ''}>
                    ▶️ Iniciar
                </button>
                <button class="service-btn stop" onclick="controller.stopService('${config.name}')"
                    ${status.status === 'stopped' || status.status === 'stopping' ? 'disabled' : ''}>
                    ⏹️ Detener
                </button>
                <button class="service-btn restart" onclick="controller.restartService('${config.name}')"
                    ${status.status === 'stopped' ? 'disabled' : ''}>
                    🔄 Reiniciar
                </button>
                <button class="service-btn logs" onclick="controller.showLogs('${config.name}')">
                    📋 Logs
                </button>
            </div>
        `;

        return card;
    }

    getStatusText(status) {
        const statusMap = {
            'stopped': 'Detenido',
            'starting': 'Iniciando...',
            'running': 'Ejecutando',
            'stopping': 'Deteniendo...',
            'error': 'Error'
        };
        return statusMap[status] || status;
    }

    handleStatusUpdate(statuses) {
        statuses.forEach(status => {
            const serviceData = this.services.find(s => s.config.name === status.name);
            if (serviceData) {
                serviceData.status = status;
                this.updateServiceCard(serviceData);
            }
        });

        // Update logs if modal is open
        if (this.currentLogService) {
            this.refreshLogs();
        }
    }

    updateServiceCard(serviceData) {
        const card = document.getElementById(`service-${serviceData.config.name}`);
        if (card) {
            const newCard = this.createServiceCard(serviceData);
            card.replaceWith(newCard);
        }
    }

    async startService(serviceName) {
        try {
            const response = await fetch(`/api/service/${serviceName}/start`, {
                method: 'POST'
            });
            const data = await response.json();
            if (!data.success) {
                alert('Error al iniciar el servicio');
            }
        } catch (error) {
            console.error('Error starting service:', error);
            alert('Error al iniciar el servicio');
        }
    }

    async stopService(serviceName) {
        try {
            const response = await fetch(`/api/service/${serviceName}/stop`, {
                method: 'POST'
            });
            const data = await response.json();
            if (!data.success) {
                alert('Error al detener el servicio');
            }
        } catch (error) {
            console.error('Error stopping service:', error);
            alert('Error al detener el servicio');
        }
    }

    async restartService(serviceName) {
        try {
            const response = await fetch(`/api/service/${serviceName}/restart`, {
                method: 'POST'
            });
            const data = await response.json();
            if (!data.success) {
                alert('Error al reiniciar el servicio');
            }
        } catch (error) {
            console.error('Error restarting service:', error);
            alert('Error al reiniciar el servicio');
        }
    }

    async showLogs(serviceName) {
        this.currentLogService = serviceName;
        const modal = document.getElementById('log-modal');
        const title = document.getElementById('log-modal-title');

        title.textContent = `Logs de ${serviceName}`;
        modal.classList.add('active');

        await this.refreshLogs();
    }

    async refreshLogs() {
        if (!this.currentLogService) return;

        try {
            const response = await fetch(`/api/service/${this.currentLogService}/logs`);
            const data = await response.json();

            const container = document.getElementById('log-container');
            if (data.logs && data.logs.length > 0) {
                container.innerHTML = data.logs.map(log =>
                    `<div class="log-line">${this.escapeHtml(log)}</div>`
                ).join('');

                // Scroll to bottom
                container.scrollTop = container.scrollHeight;
            } else {
                container.innerHTML = '<div class="log-line">No hay logs disponibles</div>';
            }
        } catch (error) {
            console.error('Error loading logs:', error);
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async startAll() {
        if (!confirm('¿Iniciar todos los servicios habilitados?')) return;

        try {
            const response = await fetch('/api/start-all', {
                method: 'POST'
            });
            const data = await response.json();
            if (data.success) {
                console.log('Starting all services...');
            }
        } catch (error) {
            console.error('Error starting all services:', error);
            alert('Error al iniciar todos los servicios');
        }
    }

    async stopAll() {
        if (!confirm('¿Detener todos los servicios?')) return;

        try {
            const response = await fetch('/api/stop-all', {
                method: 'POST'
            });
            const data = await response.json();
            if (data.success) {
                console.log('Stopping all services...');
            }
        } catch (error) {
            console.error('Error stopping all services:', error);
            alert('Error al detener todos los servicios');
        }
    }

    setupEventListeners() {
        document.getElementById('start-all-btn').addEventListener('click', () => {
            this.startAll();
        });

        document.getElementById('stop-all-btn').addEventListener('click', () => {
            this.stopAll();
        });

        // Close modal on outside click
        document.getElementById('log-modal').addEventListener('click', (e) => {
            if (e.target.id === 'log-modal') {
                closeLogModal();
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeLogModal();
            }
        });
    }
}

// Global functions for onclick handlers
let controller;

function closeLogModal() {
    const modal = document.getElementById('log-modal');
    modal.classList.remove('active');
    controller.currentLogService = null;
}

function refreshLogs() {
    controller.refreshLogs();
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    controller = new ServiceController();
});
