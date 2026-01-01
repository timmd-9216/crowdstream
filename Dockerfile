FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy all service directories
COPY dance_movement_detector/ /app/dance_movement_detector/
COPY movement_dashboard/ /app/movement_dashboard/
COPY cosmic_journey/ /app/cosmic_journey/
COPY kill-all-services.sh /app/
COPY start-all-services.sh /app/

# Install Python dependencies for all services
RUN pip install --no-cache-dir \
    ultralytics>=8.0.0 \
    opencv-python-headless>=4.8.0 \
    numpy>=1.24.0 \
    python-osc>=1.8.0 \
    fastapi>=0.110 \
    uvicorn[standard]>=0.23 \
    jinja2>=3.1 \
    flask==3.0.0 \
    flask-socketio==5.3.5 \
    python-socketio==5.10.0

# Create logs directory
RUN mkdir -p /app/logs

# Make scripts executable
RUN chmod +x /app/start-all-services.sh /app/kill-all-services.sh

# Expose ports for web services
# 8082 - Dashboard
# 8091 - Cosmic Journey Visualizer
EXPOSE 8082 8091

# Start all services
CMD ["/bin/bash", "/app/start-all-services.sh"]
