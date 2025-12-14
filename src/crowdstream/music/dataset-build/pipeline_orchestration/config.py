"""
Configuration for CrowdStream Music Dataset Pipeline

This module provides configuration management for the Dagster pipeline,
including default settings, environment variable handling, and validation.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import os
from dataclasses import dataclass, field
import json

@dataclass
class PipelineConfig:
    """Main configuration class for the music dataset pipeline."""
    
    # Data paths
    base_data_dir: str = "data/music"
    artist_catalogue_file: str = "artist_catalogue.json"
    
    # Spotify configuration
    spotify_client_id: Optional[str] = None
    spotify_client_secret: Optional[str] = None
    spotify_request_timeout: int = 30
    spotify_max_retries: int = 3
    
    # Audio processing
    default_sample_rate: int = 44100
    crossfade_duration: float = 2.0
    segment_beats: int = 48
    supported_audio_formats: List[str] = field(default_factory=lambda: ["mp3", "wav", "flac"])
    
    # Spleeter configuration
    spleeter_model: str = "spleeter:5stems-16kHz"
    spleeter_output_format: str = "wav"
    spleeter_use_docker: bool = False
    spleeter_docker_image: str = "researchdeezer/spleeter:3.8-5stems"
    spleeter_timeout: int = 300  # seconds per file
    
    # BPM filtering
    min_bpm: float = 80.0
    max_bpm: float = 145.0
    bpm_tolerance: float = 5.0  # For playlist compatibility
    
    # Processing limits
    max_segments_per_stem: int = 3
    max_concurrent_processes: int = 4
    
    # Quality thresholds
    min_stems_for_mixing: int = 4
    min_track_duration_ms: int = 15000  # 15 seconds
    
    # Output settings
    generate_spectrograms: bool = False
    spectrogram_format: str = "png"
    export_metadata_formats: List[str] = field(default_factory=lambda: ["csv", "json"])
    
    def __post_init__(self):
        """Post-initialization to load from environment variables."""
        # Load Spotify credentials from environment
        if not self.spotify_client_id:
            self.spotify_client_id = os.getenv('SPOTIPY_CLIENT_ID')
        if not self.spotify_client_secret:
            self.spotify_client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
    
    @classmethod
    def from_file(cls, config_path: Path) -> 'PipelineConfig':
        """Load configuration from JSON file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        return cls(**config_data)
    
    def save_to_file(self, config_path: Path):
        """Save configuration to JSON file."""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict, excluding None values and non-serializable types
        config_dict = {}
        for key, value in self.__dict__.items():
            if value is not None:
                if isinstance(value, (str, int, float, bool, list)):
                    config_dict[key] = value
                elif isinstance(value, Path):
                    config_dict[key] = str(value)
        
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def get_data_paths(self) -> Dict[str, Path]:
        """Get all data paths as Path objects."""
        base_path = Path(self.base_data_dir)
        
        return {
            'base': base_path,
            'artist_catalogue': base_path / self.artist_catalogue_file,
            'track_data': base_path / 'track_data',
            'sample_audio': base_path / 'sample_audio',
            'stems': base_path / 'sample_audio' / 'stems',
            'loops': base_path / 'sample_audio' / 'loops',
            'rekordbox': base_path / 'rekordbox' / 'collection.xml',
            'metadata': base_path / 'metadata',
            'spectrograms': base_path / 'spectrograms'
        }
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Validate Spotify credentials
        if not self.spotify_client_id or not self.spotify_client_secret:
            errors.append("Spotify client ID and secret are required")
        
        # Validate BPM range
        if self.min_bpm >= self.max_bpm:
            errors.append("min_bpm must be less than max_bpm")
        
        # Validate file paths
        data_paths = self.get_data_paths()
        if not data_paths['artist_catalogue'].exists():
            errors.append(f"Artist catalogue file not found: {data_paths['artist_catalogue']}")
        
        # Validate processing limits
        if self.max_concurrent_processes < 1:
            errors.append("max_concurrent_processes must be at least 1")
        
        if self.min_stems_for_mixing < 2:
            errors.append("min_stems_for_mixing must be at least 2")
        
        return errors
    
    def ensure_directories(self):
        """Ensure all required directories exist."""
        data_paths = self.get_data_paths()
        
        directories_to_create = [
            data_paths['base'],
            data_paths['track_data'],
            data_paths['sample_audio'],
            data_paths['stems'],
            data_paths['loops'],
            data_paths['rekordbox'].parent,
            data_paths['metadata']
        ]
        
        if self.generate_spectrograms:
            directories_to_create.append(data_paths.get('spectrograms', data_paths['base'] / 'spectrograms'))
        
        for directory in directories_to_create:
            directory.mkdir(parents=True, exist_ok=True)

# Default configuration instance
DEFAULT_CONFIG = PipelineConfig()

# Development configuration
DEVELOPMENT_CONFIG = PipelineConfig(
    base_data_dir="data/music_dev",
    max_concurrent_processes=2,
    spleeter_timeout=120,
    generate_spectrograms=True
)

# Production configuration
PRODUCTION_CONFIG = PipelineConfig(
    base_data_dir="/data/music_production",
    max_concurrent_processes=8,
    spleeter_use_docker=True,
    spleeter_timeout=600,
    generate_spectrograms=True,
    export_metadata_formats=["csv", "json", "parquet"]
)

def get_config(config_name: str = "default") -> PipelineConfig:
    """Get configuration by name."""
    configs = {
        "default": DEFAULT_CONFIG,
        "development": DEVELOPMENT_CONFIG,
        "production": PRODUCTION_CONFIG
    }
    
    config = configs.get(config_name)
    if not config:
        available_configs = list(configs.keys())
        raise ValueError(f"Unknown config '{config_name}'. Available: {available_configs}")
    
    return config

def load_config_from_env() -> PipelineConfig:
    """Load configuration from environment variables."""
    config = PipelineConfig()
    
    # Override with environment variables if present
    env_mappings = {
        'CROWDSTREAM_DATA_DIR': 'base_data_dir',
        'CROWDSTREAM_MIN_BPM': 'min_bpm',
        'CROWDSTREAM_MAX_BPM': 'max_bpm',
        'CROWDSTREAM_SEGMENT_BEATS': 'segment_beats',
        'CROWDSTREAM_MAX_PROCESSES': 'max_concurrent_processes',
        'CROWDSTREAM_SPLEETER_MODEL': 'spleeter_model',
        'CROWDSTREAM_USE_DOCKER': 'spleeter_use_docker',
        'CROWDSTREAM_GENERATE_SPECTROGRAMS': 'generate_spectrograms'
    }
    
    for env_var, config_attr in env_mappings.items():
        env_value = os.getenv(env_var)
        if env_value:
            # Type conversion based on attribute type
            current_value = getattr(config, config_attr)
            if isinstance(current_value, bool):
                setattr(config, config_attr, env_value.lower() in ('true', '1', 'yes'))
            elif isinstance(current_value, int):
                setattr(config, config_attr, int(env_value))
            elif isinstance(current_value, float):
                setattr(config, config_attr, float(env_value))
            else:
                setattr(config, config_attr, env_value)
    
    return config

if __name__ == "__main__":
    # Example usage and validation
    config = load_config_from_env()
    
    print("Current Configuration:")
    print(f"- Data directory: {config.base_data_dir}")
    print(f"- BPM range: {config.min_bpm} - {config.max_bpm}")
    print(f"- Max processes: {config.max_concurrent_processes}")
    print(f"- Spleeter model: {config.spleeter_model}")
    print(f"- Use Docker: {config.spleeter_use_docker}")
    
    # Validate configuration
    errors = config.validate()
    if errors:
        print("\nConfiguration Errors:")
        for error in errors:
            print(f"- {error}")
    else:
        print("\nConfiguration is valid!")
        
        # Ensure directories exist
        config.ensure_directories()
        print("Required directories created/verified.")
        
        # Save current config
        config_path = Path("pipeline_config.json")
        config.save_to_file(config_path)
        print(f"Configuration saved to: {config_path}")