FROM ubuntu:16.04

# Avoid interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Use system Python 3.5.2 (default on Ubuntu 16.04 / Jetson TX1)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-setuptools \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install system dependencies for OpenCV and ML
RUN apt-get update && apt-get install -y \
    libopencv-dev \
    python3-opencv \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgstreamer1.0-0 \
    libavcodec-ffmpeg56 \
    libavformat-ffmpeg56 \
    libswscale-ffmpeg3 \
    libgtk2.0-0 \
    libatlas-base-dev \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip to max version for Python 3.5
RUN python3 -m pip install --no-cache-dir --upgrade "pip<21.0" setuptools wheel

# Set working directory
WORKDIR /app

# Copy all service directories
COPY dance_movement_detector/ /app/dance_movement_detector/
COPY dance_dashboard_alt/ /app/dance_dashboard_alt/
COPY cosmic_journey/ /app/cosmic_journey/
COPY kill-all-services.sh /app/
COPY start-all-services.sh /app/

# Install Python dependencies from requirements files
# These are now compatible with Python 3.5.2
RUN cd /app/dance_movement_detector && \
    python3 -m pip install --no-cache-dir -r requirements.txt

RUN cd /app/dance_dashboard_alt && \
    python3 -m pip install --no-cache-dir -r requirements.txt

RUN cd /app/cosmic_journey && \
    python3 -m pip install --no-cache-dir -r requirements.txt

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
