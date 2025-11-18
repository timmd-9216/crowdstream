// Dashboard WebSocket client and visualization

class DashboardClient {
    constructor() {
        this.socket = null;
        this.movementChart = null;
        this.bodyPartsChart = null;
        this.init();
    }

    init() {
        this.connectWebSocket();
        this.initCharts();
        this.setupEventListeners();
    }

    connectWebSocket() {
        this.socket = io();

        this.socket.on('connect', () => {
            console.log('Connected to server');
            this.updateConnectionStatus(true);
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.updateConnectionStatus(false);
        });

        this.socket.on('update', (data) => {
            this.handleUpdate(data);
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

    handleUpdate(data) {
        // Update current stats
        if (data.current) {
            this.updateCurrentStats(data.current);
        }

        // Update cumulative stats
        if (data.cumulative) {
            this.updateCumulativeStats(data.cumulative);
        }

        // Update charts
        if (data.history) {
            this.updateCharts(data.history);
        }
    }

    updateCurrentStats(current) {
        document.getElementById('current-people').textContent = current.person_count;
        document.getElementById('current-total').textContent = current.total_movement.toFixed(1);
        document.getElementById('current-arms').textContent = current.arm_movement.toFixed(1);
        document.getElementById('current-legs').textContent = current.leg_movement.toFixed(1);
        document.getElementById('current-head').textContent = current.head_movement.toFixed(1);
        document.getElementById('last-update').textContent = current.datetime;
    }

    updateCumulativeStats(cumulative) {
        document.getElementById('cum-messages').textContent = cumulative.total_messages;
        document.getElementById('cum-avg-people').textContent = cumulative.avg_people.toFixed(1);
        document.getElementById('cum-max-people').textContent = cumulative.max_people;
        document.getElementById('cum-avg-total').textContent = cumulative.avg_total_movement.toFixed(1);
        document.getElementById('cum-max-total').textContent = cumulative.max_total_movement.toFixed(1);

        document.getElementById('cum-avg-arms').textContent = cumulative.avg_arm_movement.toFixed(1);
        document.getElementById('cum-max-arms').textContent = cumulative.max_arm_movement.toFixed(1);

        document.getElementById('cum-avg-legs').textContent = cumulative.avg_leg_movement.toFixed(1);
        document.getElementById('cum-max-legs').textContent = cumulative.max_leg_movement.toFixed(1);

        document.getElementById('cum-avg-head').textContent = cumulative.avg_head_movement.toFixed(1);
        document.getElementById('cum-max-head').textContent = cumulative.max_head_movement.toFixed(1);
    }

    initCharts() {
        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#f9fafb',
                        font: {
                            size: 12
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: '#d1d5db',
                        maxRotation: 45,
                        minRotation: 45
                    },
                    grid: {
                        color: '#4b5563'
                    }
                },
                y: {
                    ticks: {
                        color: '#d1d5db'
                    },
                    grid: {
                        color: '#4b5563'
                    }
                }
            }
        };

        // Movement Chart
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
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Personas',
                        data: [],
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
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
                        display: true,
                        position: 'right',
                        ticks: {
                            color: '#d1d5db'
                        },
                        grid: {
                            drawOnChartArea: false,
                        }
                    }
                },
                plugins: {
                    ...commonOptions.plugins,
                    title: {
                        display: true,
                        text: 'Movimiento Total y Personas',
                        color: '#f9fafb',
                        font: {
                            size: 16
                        }
                    }
                }
            }
        });

        // Body Parts Chart
        const bodyPartsCtx = document.getElementById('bodyPartsChart').getContext('2d');
        this.bodyPartsChart = new Chart(bodyPartsCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Brazos',
                        data: [],
                        borderColor: '#f59e0b',
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Piernas',
                        data: [],
                        borderColor: '#8b5cf6',
                        backgroundColor: 'rgba(139, 92, 246, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Cabeza',
                        data: [],
                        borderColor: '#ec4899',
                        backgroundColor: 'rgba(236, 72, 153, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: {
                ...commonOptions,
                plugins: {
                    ...commonOptions.plugins,
                    title: {
                        display: true,
                        text: 'Movimiento por Parte del Cuerpo',
                        color: '#f9fafb',
                        font: {
                            size: 16
                        }
                    }
                }
            }
        });
    }

    updateCharts(history) {
        // Limit to last 50 data points for readability
        const maxPoints = 50;
        const data = history.slice(-maxPoints);

        // Extract labels and data
        const labels = data.map(d => d.datetime);
        const totalMovement = data.map(d => d.total_movement);
        const personCount = data.map(d => d.person_count);
        const armMovement = data.map(d => d.arm_movement);
        const legMovement = data.map(d => d.leg_movement);
        const headMovement = data.map(d => d.head_movement);

        // Update movement chart
        this.movementChart.data.labels = labels;
        this.movementChart.data.datasets[0].data = totalMovement;
        this.movementChart.data.datasets[1].data = personCount;
        this.movementChart.update('none'); // No animation for real-time updates

        // Update body parts chart
        this.bodyPartsChart.data.labels = labels;
        this.bodyPartsChart.data.datasets[0].data = armMovement;
        this.bodyPartsChart.data.datasets[1].data = legMovement;
        this.bodyPartsChart.data.datasets[2].data = headMovement;
        this.bodyPartsChart.update('none');
    }

    setupEventListeners() {
        // Reset button
        document.getElementById('reset-btn').addEventListener('click', () => {
            if (confirm('¿Estás seguro de que quieres reiniciar las estadísticas?')) {
                this.socket.emit('reset_stats');
                console.log('Stats reset requested');
            }
        });
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new DashboardClient();
});
