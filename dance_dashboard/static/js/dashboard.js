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
        console.log('Initializing WebSocket connection...');
        this.socket = io({
            transports: ['websocket'],
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionAttempts: 10
        });

        this.socket.on('connect', () => {
            console.log('✅ Connected to dashboard server');
            this.updateConnectionStatus(true);
        });

        this.socket.on('disconnect', () => {
            console.log('❌ Disconnected from dashboard server');
            this.updateConnectionStatus(false);
        });

        this.socket.on('connect_error', (error) => {
            console.error('Connection error:', error);
        });

        this.socket.on('update', (data) => {
            console.log('📊 Received update:', data);
            this.handleUpdate(data);
        });

        this.socket.on('stats_reset', () => {
            console.log('🔄 Stats reset confirmed by server');
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
        console.log('📈 Updating current stats:', current);
        const peopleEl = document.getElementById('current-people');
        const totalEl = document.getElementById('current-total');
        const armsEl = document.getElementById('current-arms');
        const legsEl = document.getElementById('current-legs');
        const headEl = document.getElementById('current-head');
        const updateEl = document.getElementById('last-update');

        if (peopleEl) peopleEl.textContent = current.person_count;
        if (totalEl) totalEl.textContent = current.total_movement.toFixed(1);
        if (armsEl) armsEl.textContent = current.arm_movement.toFixed(1);
        if (legsEl) legsEl.textContent = current.leg_movement.toFixed(1);
        if (headEl) headEl.textContent = current.head_movement.toFixed(1);
        if (updateEl) updateEl.textContent = current.datetime;

        console.log('✅ Current stats updated');
    }

    updateCumulativeStats(cumulative) {
        console.log('📊 Updating cumulative stats:', cumulative);

        const msgEl = document.getElementById('cum-messages');
        const avgPeopleEl = document.getElementById('cum-avg-people');
        const maxPeopleEl = document.getElementById('cum-max-people');
        const avgTotalEl = document.getElementById('cum-avg-total');
        const maxTotalEl = document.getElementById('cum-max-total');
        const avgArmsEl = document.getElementById('cum-avg-arms');
        const maxArmsEl = document.getElementById('cum-max-arms');
        const avgLegsEl = document.getElementById('cum-avg-legs');
        const maxLegsEl = document.getElementById('cum-max-legs');
        const avgHeadEl = document.getElementById('cum-avg-head');
        const maxHeadEl = document.getElementById('cum-max-head');

        if (msgEl) msgEl.textContent = cumulative.total_messages;
        if (avgPeopleEl) avgPeopleEl.textContent = cumulative.avg_people.toFixed(1);
        if (maxPeopleEl) maxPeopleEl.textContent = cumulative.max_people;
        if (avgTotalEl) avgTotalEl.textContent = cumulative.avg_total_movement.toFixed(1);
        if (maxTotalEl) maxTotalEl.textContent = cumulative.max_total_movement.toFixed(1);
        if (avgArmsEl) avgArmsEl.textContent = cumulative.avg_arm_movement.toFixed(1);
        if (maxArmsEl) maxArmsEl.textContent = cumulative.max_arm_movement.toFixed(1);
        if (avgLegsEl) avgLegsEl.textContent = cumulative.avg_leg_movement.toFixed(1);
        if (maxLegsEl) maxLegsEl.textContent = cumulative.max_leg_movement.toFixed(1);
        if (avgHeadEl) avgHeadEl.textContent = cumulative.avg_head_movement.toFixed(1);
        if (maxHeadEl) maxHeadEl.textContent = cumulative.max_head_movement.toFixed(1);

        console.log('✅ Cumulative stats updated');
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
        if (!history || history.length === 0) {
            console.log('No history data to display');
            // Clear charts if no data
            this.movementChart.data.labels = [];
            this.movementChart.data.datasets[0].data = [];
            this.movementChart.data.datasets[1].data = [];
            this.movementChart.update('none');

            this.bodyPartsChart.data.labels = [];
            this.bodyPartsChart.data.datasets[0].data = [];
            this.bodyPartsChart.data.datasets[1].data = [];
            this.bodyPartsChart.data.datasets[2].data = [];
            this.bodyPartsChart.update('none');
            return;
        }

        // Limit to last 50 data points for readability
        const maxPoints = 50;
        const data = history.slice(-maxPoints);

        console.log(`Updating charts with ${data.length} data points`);

        // Extract labels and data
        const labels = data.map(d => d.datetime || 'N/A');
        const totalMovement = data.map(d => d.total_movement || 0);
        const personCount = data.map(d => d.person_count || 0);
        const armMovement = data.map(d => d.arm_movement || 0);
        const legMovement = data.map(d => d.leg_movement || 0);
        const headMovement = data.map(d => d.head_movement || 0);

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
                console.log('🔄 Resetting statistics...');
                console.log('Socket connected:', this.socket.connected);
                if (this.socket.connected) {
                    // Send reset with callback to receive immediate response
                    this.socket.emit('reset_stats', (data) => {
                        console.log('🔄 Stats reset confirmed by server, updating UI');
                        this.handleUpdate(data);
                    });
                    console.log('✅ Reset event sent to server');
                } else {
                    console.error('❌ Socket not connected! Cannot send reset event');
                    alert('Error: No hay conexión con el servidor. Recarga la página.');
                }
            }
        });
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new DashboardClient();
});
