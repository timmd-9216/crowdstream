class DashboardClient {
    constructor() {
        this.socket = null;
        this.movementChart = null;
        this.bodyPartsChart = null;
        this.reconnectDelay = 1500;
        this.init();
    }

    init() {
        this.initCharts();
        this.setupEventListeners();
        this.connectWebSocket();
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const url = `${protocol}://${window.location.host}/ws`;
        console.log('Connecting to websocket', url);
        this.socket = new WebSocket(url);

        this.socket.onopen = () => {
            console.log('✅ WebSocket connected');
            this.updateConnectionStatus(true);
        };

        this.socket.onclose = () => {
            console.log('❌ WebSocket disconnected');
            this.updateConnectionStatus(false);
            setTimeout(() => this.connectWebSocket(), this.reconnectDelay);
        };

        this.socket.onerror = (err) => {
            console.error('WebSocket error', err);
        };

        this.socket.onmessage = (event) => {
            try {
                const payload = JSON.parse(event.data);
                if (payload.type === 'update') {
                    this.handleUpdate(payload.data);
                }
            } catch (error) {
                console.error('Invalid message from server', error);
            }
        };
    }

    updateConnectionStatus(connected) {
        const indicator = document.getElementById('status-indicator');
        const text = document.getElementById('status-text');
        if (!indicator || !text) return;

        indicator.classList.toggle('connected', connected);
        indicator.classList.toggle('disconnected', !connected);
        text.textContent = connected ? 'Conectado' : 'Desconectado';
    }

    handleUpdate(data) {
        if (!data) return;
        if (data.current) {
            this.updateCurrentStats(data.current);
        }
        if (data.cumulative) {
            this.updateCumulativeStats(data.cumulative);
        }
        if (data.history) {
            this.updateCharts(data.history);
        }
    }

    updateCurrentStats(current) {
        const setText = (id, value) => {
            const el = document.getElementById(id);
            if (el != null) {
                el.textContent = value;
            }
        };
        setText('current-people', current.person_count ?? 0);
        setText('current-total', this.formatNumber(current.total_movement));
        setText('current-arms', this.formatNumber(current.arm_movement));
        setText('current-legs', this.formatNumber(current.leg_movement));
        setText('current-head', this.formatNumber(current.head_movement));
        setText('last-update', current.datetime ?? '--:--:--');
    }

    updateCumulativeStats(cumulative) {
        const format = (value) => this.formatNumber(value, 1);
        const setText = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.textContent = value;
        };

        setText('cum-messages', cumulative.total_messages ?? 0);
        setText('cum-avg-people', format(cumulative.avg_people));
        setText('cum-max-people', cumulative.max_people ?? 0);
        setText('cum-avg-total', format(cumulative.avg_total_movement));
        setText('cum-max-total', format(cumulative.max_total_movement));
        setText('cum-avg-arms', format(cumulative.avg_arm_movement));
        setText('cum-max-arms', format(cumulative.max_arm_movement));
        setText('cum-avg-legs', format(cumulative.avg_leg_movement));
        setText('cum-max-legs', format(cumulative.max_leg_movement));
        setText('cum-avg-head', format(cumulative.avg_head_movement));
        setText('cum-max-head', format(cumulative.max_head_movement));
    }

    initCharts() {
        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#f9fafb',
                    }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#d1d5db', maxRotation: 45, minRotation: 45 },
                    grid: { color: '#4b5563' }
                },
                y: {
                    ticks: { color: '#d1d5db' },
                    grid: { color: '#4b5563' }
                }
            }
        };

        const movementCtx = document.getElementById('movementChart').getContext('2d');
        this.movementChart = new Chart(movementCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Movimiento Total',
                        data: [],
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 2,
                    },
                    {
                        label: 'Personas',
                        data: [],
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 2,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                ...commonOptions,
                scales: {
                    ...commonOptions.scales,
                    y1: {
                        type: 'linear',
                        position: 'right',
                        ticks: { color: '#d1d5db' },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });

        const bodyCtx = document.getElementById('bodyPartsChart').getContext('2d');
        this.bodyPartsChart = new Chart(bodyCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Brazos',
                        data: [],
                        borderColor: '#f59e0b',
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 2,
                    },
                    {
                        label: 'Piernas',
                        data: [],
                        borderColor: '#8b5cf6',
                        backgroundColor: 'rgba(139, 92, 246, 0.1)',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 2,
                    },
                    {
                        label: 'Cabeza',
                        data: [],
                        borderColor: '#ec4899',
                        backgroundColor: 'rgba(236, 72, 153, 0.1)',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 2,
                    }
                ]
            },
            options: commonOptions,
        });
    }

    updateCharts(history) {
        if (!history || !Array.isArray(history)) {
            return;
        }
        const maxPoints = 50;
        const recent = history.slice(-maxPoints);
        const labels = recent.map((d) => d.datetime || 'N/A');
        const totals = recent.map((d) => d.total_movement || 0);
        const people = recent.map((d) => d.person_count || 0);
        const arms = recent.map((d) => d.arm_movement || 0);
        const legs = recent.map((d) => d.leg_movement || 0);
        const heads = recent.map((d) => d.head_movement || 0);

        this.movementChart.data.labels = labels;
        this.movementChart.data.datasets[0].data = totals;
        this.movementChart.data.datasets[1].data = people;
        this.movementChart.update('none');

        this.bodyPartsChart.data.labels = labels;
        this.bodyPartsChart.data.datasets[0].data = arms;
        this.bodyPartsChart.data.datasets[1].data = legs;
        this.bodyPartsChart.data.datasets[2].data = heads;
        this.bodyPartsChart.update('none');
    }

    setupEventListeners() {
        const resetBtn = document.getElementById('reset-btn');
        if (!resetBtn) return;
        resetBtn.addEventListener('click', () => {
            if (!confirm('¿Estás seguro de reiniciar las estadísticas?')) {
                return;
            }
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                this.socket.send(JSON.stringify({ action: 'reset' }));
            } else {
                alert('Sin conexión al servidor. Intenta recargar.');
            }
        });
    }

    formatNumber(value, digits = 1) {
        const num = Number(value);
        return Number.isFinite(num) ? num.toFixed(digits) : '0.0';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new DashboardClient();
});
