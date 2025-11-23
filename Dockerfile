FROM ubuntu:16.04

# Avoid interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install Python 3.8 from deadsnakes PPA (3.8 is max stable for Ubuntu 16.04)
RUN apt-get update && apt-get install -y \
    software-properties-common \
    curl \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update

# Install Python 3.8 and system dependencies
RUN apt-get install -y \
    python3.8 \
    python3.8-dev \
    python3.8-distutils \
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

# Install pip for Python 3.8
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py \
    && python3.8 get-pip.py \
    && rm get-pip.py

# Create symbolic link for python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1

# Set working directory
WORKDIR /app

# Copy all service directories
COPY dance_movement_detector/ /app/dance_movement_detector/
COPY dance_dashboard_alt/ /app/dance_dashboard_alt/
COPY cosmic_journey/ /app/cosmic_journey/
COPY kill-all-services.sh /app/
COPY start-all-services.sh /app/

# Upgrade pip and install wheel
RUN python3.8 -m pip install --no-cache-dir --upgrade pip setuptools wheel

# Install compatible Python dependencies for Ubuntu 16.04
# Using versions compatible with Python 3.8 and older glibc (2.23)
RUN python3.8 -m pip install --no-cache-dir \
    ultralytics==8.0.196 \
    opencv-python-headless==4.5.5.64 \
    numpy==1.21.6 \
    python-osc==1.8.3 \
    fastapi==0.95.2 \
    uvicorn==0.22.0 \
    jinja2==3.1.2 \
    flask==2.3.3 \
    flask-socketio==5.3.0 \
    python-socketio==5.9.0 \
    torch==1.13.1+cpu \
    torchvision==0.14.1+cpu \
    --extra-index-url https://download.pytorch.org/whl/cpu

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
