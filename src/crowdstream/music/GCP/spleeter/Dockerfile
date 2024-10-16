ARG BASE=python:3.6

FROM ${BASE}

ARG SPLEETER_VERSION=1.5.3
ENV MODEL_PATH /model

RUN mkdir -p /model
RUN apt-get update && apt-get install -y ffmpeg libsndfile1
RUN pip install musdb museval
RUN pip install spleeter==${SPLEETER_VERSION}
RUN pip install google-cloud-storage

# Copy the Python script into the container (you need to have a script in the same directory)
COPY process_audio.py /app/process_audio.py

# Set the working directory
WORKDIR /app

# Use the Python script as the entry point
CMD ["python", "process_audio.py"]
