ARG BASE=python:3.6

FROM ${BASE}

ARG SPLEETER_VERSION=1.5.3
ENV MODEL_PATH /model

RUN mkdir -p /model
RUN apt-get update && apt-get install -y ffmpeg libsndfile1
RUN pip install musdb museval
RUN pip install spleeter==${SPLEETER_VERSION}
RUN pip install google-cloud-storage

# drumsep
RUN git clone https://github.com/inagoy/drumsep.git
RUN cd drumsep && mkdir model
RUN cd /drumsep/model && gdown 1-Dm666ScPkg8Gt2-lK3Ua0xOudWHZBGC
RUN chmod 755 /drumsep/drumsep

# Copy the Python script into the container (you need to have a script in the same directory)
COPY process_audio.py /app/process_audio.py

# Set the working directory
WORKDIR /app

# Use the Python script as the entry point
CMD ["python", "process_audio.py"]
