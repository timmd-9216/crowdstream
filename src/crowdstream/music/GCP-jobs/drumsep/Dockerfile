ARG BASE=python:3.8

FROM ${BASE}

RUN pip install google-cloud-storage

# dependencies
RUN apt-get update && apt-get install -y ffmpeg libsndfile1
RUN pip install demucs gdown

# drumsep
RUN git clone https://github.com/inagoy/drumsep.git
RUN cd drumsep && mkdir model
RUN cd /drumsep/model && gdown 1-Dm666ScPkg8Gt2-lK3Ua0xOudWHZBGC
RUN chmod 755 /drumsep/drumsep
RUN mkdir /data

# Copy the Python script into the container (you need to have a script in the same directory)
COPY process_audio.py /app/process_audio.py

# Set the working directory
WORKDIR /app

# Use the Python script as the entry point
CMD ["python", "process_audio.py"]
