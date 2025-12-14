"""
Resources for CrowdStream Music Dataset Pipeline

This module defines Dagster resources for managing external dependencies
and configurations used throughout the pipeline.
"""

from dagster import ConfigurableResource, get_dagster_logger
from pydantic import Field
from pathlib import Path
from typing import Dict, Optional, List
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import json
import os
from pydub import AudioSegment
import pandas as pd

logger = get_dagster_logger()

class DataPathsResource(ConfigurableResource):
    """Resource for managing data paths throughout the pipeline."""
    
    base_data_dir: str = Field(
        default="data/music",
        description="Base directory for all music data"
    )
    
    def get_base_path(self) -> Path:
        """Get the base data path."""
        return Path(self.base_data_dir)
    
    def get_artist_catalogue_path(self) -> Path:
        """Get path to artist catalogue JSON file."""
        return self.get_base_path() / "artist_catalogue.json"
    
    def get_track_data_dir(self) -> Path:
        """Get directory for track data."""
        return self.get_base_path() / "track_data"
    
    def get_sample_audio_dir(self) -> Path:
        """Get directory for sample audio files."""
        return self.get_base_path() / "sample_audio"
    
    def get_stems_dir(self) -> Path:
        """Get directory for audio stems."""
        return self.get_sample_audio_dir() / "stems"
    
    def get_loops_dir(self) -> Path:
        """Get directory for audio loops."""
        return self.get_sample_audio_dir() / "loops"
    
    def get_rekordbox_xml_path(self) -> Path:
        """Get path to Rekordbox XML file."""
        return self.get_base_path() / "rekordbox" / "collection.xml"
    
    def get_metadata_dir(self) -> Path:
        """Get directory for metadata files."""
        return self.get_base_path() / "metadata"
    
    def ensure_directories(self):
        """Ensure all required directories exist."""
        directories = [
            self.get_base_path(),
            self.get_track_data_dir(),
            self.get_sample_audio_dir(),
            self.get_stems_dir(),
            self.get_loops_dir(),
            self.get_rekordbox_xml_path().parent,
            self.get_metadata_dir()
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory exists: {directory}")

class SpotifyResource(ConfigurableResource):
    """Resource for managing Spotify API interactions."""
    
    client_id: str = Field(description="Spotify Client ID")
    client_secret: str = Field(description="Spotify Client Secret")
    
    def get_spotify_client(self) -> spotipy.Spotify:
        """Get authenticated Spotify client."""
        try:
            client_credentials_manager = SpotifyClientCredentials(
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            sp = spotipy.Spotify(
                client_credentials_manager=client_credentials_manager,
                requests_timeout=10,
                retries=3
            )
            
            logger.info("Spotify client initialized successfully")
            return sp
            
        except Exception as e:
            logger.error(f"Failed to initialize Spotify client: {e}")
            raise

    def load_artist_catalogue(self, catalogue_path: Path) -> Dict:
        """Load artist catalogue from JSON file."""
        try:
            with open(catalogue_path, 'r', encoding='utf-8') as file:
                catalogue = json.load(file)
                logger.info(f"Loaded {len(catalogue)} artists from catalogue")
                return catalogue
        except FileNotFoundError:
            logger.error(f"Artist catalogue not found at {catalogue_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in artist catalogue: {e}")
            raise

    def validate_credentials(self) -> bool:
        """Validate Spotify credentials by making a test request."""
        try:
            sp = self.get_spotify_client()
            # Test with a simple search
            results = sp.search(q="test", type="artist", limit=1)
            logger.info("Spotify credentials validated successfully")
            return True
        except Exception as e:
            logger.error(f"Spotify credential validation failed: {e}")
            return False

class AudioProcessingResource(ConfigurableResource):
    """Resource for audio processing operations."""
    
    default_sample_rate: int = Field(
        default=44100,
        description="Default sample rate for audio processing"
    )
    
    crossfade_duration: float = Field(
        default=2.0,
        description="Default crossfade duration in seconds"
    )
    
    segment_beats: int = Field(
        default=48,
        description="Number of beats per audio segment"
    )
    
    supported_formats: List[str] = Field(
        default=["mp3", "wav", "flac"],
        description="Supported audio formats"
    )
    
    def validate_audio_file(self, file_path: Path) -> bool:
        """Validate audio file format and accessibility."""
        try:
            if not file_path.exists():
                logger.error(f"Audio file does not exist: {file_path}")
                return False
            
            if file_path.suffix.lower().strip('.') not in self.supported_formats:
                logger.error(f"Unsupported audio format: {file_path.suffix}")
                return False
            
            # Try to load the audio file
            audio = AudioSegment.from_file(str(file_path))
            logger.debug(f"Audio file validated: {file_path} ({len(audio)}ms)")
            return True
            
        except Exception as e:
            logger.error(f"Audio file validation failed for {file_path}: {e}")
            return False
    
    def get_audio_info(self, file_path: Path) -> Dict:
        """Get audio file information."""
        try:
            audio = AudioSegment.from_file(str(file_path))
            
            info = {
                "duration_ms": len(audio),
                "frame_rate": audio.frame_rate,
                "channels": audio.channels,
                "sample_width": audio.sample_width,
                "file_size_bytes": file_path.stat().st_size,
                "format": file_path.suffix.lower().strip('.')
            }
            
            logger.debug(f"Audio info extracted for {file_path}: {info}")
            return info
            
        except Exception as e:
            logger.error(f"Failed to get audio info for {file_path}: {e}")
            return {}

    def calculate_bpm_segments(self, bpm: float, total_duration_ms: int) -> Dict:
        """Calculate segment timings based on BPM."""
        try:
            # Calculate beat duration in milliseconds
            beat_duration_ms = (60 / bpm) * 1000
            
            # Calculate segment duration
            segment_duration_ms = beat_duration_ms * self.segment_beats
            
            # Calculate how many complete segments fit
            max_segments = int(total_duration_ms / segment_duration_ms)
            
            segments = []
            for i in range(max_segments):
                start_ms = i * segment_duration_ms
                end_ms = start_ms + segment_duration_ms
                
                segments.append({
                    "segment_id": i,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "duration_ms": segment_duration_ms
                })
            
            result = {
                "bpm": bpm,
                "beat_duration_ms": beat_duration_ms,
                "segment_duration_ms": segment_duration_ms,
                "total_segments": max_segments,
                "segments": segments
            }
            
            logger.debug(f"BPM segments calculated: {max_segments} segments at {bpm} BPM")
            return result
            
        except Exception as e:
            logger.error(f"Failed to calculate BPM segments: {e}")
            return {"segments": []}

class SpleeterResource(ConfigurableResource):
    """Resource for managing Spleeter audio separation."""
    
    model_name: str = Field(
        default="spleeter:5stems-16kHz",
        description="Spleeter model to use for separation"
    )
    
    output_format: str = Field(
        default="wav",
        description="Output format for separated stems"
    )
    
    use_docker: bool = Field(
        default=False,
        description="Whether to use Docker for Spleeter processing"
    )
    
    docker_image: str = Field(
        default="researchdeezer/spleeter:3.8-5stems",
        description="Docker image for Spleeter"
    )
    
    def validate_spleeter_installation(self) -> bool:
        """Validate Spleeter installation."""
        try:
            if self.use_docker:
                # Check if Docker is available
                import subprocess
                result = subprocess.run(
                    ["docker", "--version"], 
                    capture_output=True, 
                    text=True
                )
                if result.returncode != 0:
                    logger.error("Docker not available but use_docker=True")
                    return False
                
                # Check if Spleeter Docker image is available
                result = subprocess.run(
                    ["docker", "images", self.docker_image, "--format", "table {{.Repository}}:{{.Tag}}"],
                    capture_output=True,
                    text=True
                )
                
                if self.docker_image not in result.stdout:
                    logger.warning(f"Spleeter Docker image not found locally: {self.docker_image}")
                    # Image will be pulled when needed
                
                logger.info("Docker-based Spleeter validation completed")
                return True
            else:
                # Check if Spleeter Python package is available
                try:
                    import spleeter
                    logger.info("Spleeter Python package found")
                    return True
                except ImportError:
                    logger.error("Spleeter Python package not installed")
                    return False
                    
        except Exception as e:
            logger.error(f"Spleeter validation failed: {e}")
            return False
    
    def get_expected_stems(self) -> List[str]:
        """Get list of expected stem names based on model."""
        if "5stems" in self.model_name:
            return ["vocals", "drums", "bass", "piano", "other"]
        elif "4stems" in self.model_name:
            return ["vocals", "drums", "bass", "other"]  
        elif "2stems" in self.model_name:
            return ["vocals", "accompaniment"]
        else:
            logger.warning(f"Unknown model stem configuration: {self.model_name}")
            return ["vocals", "accompaniment"]  # Default fallback