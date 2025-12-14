"""
CrowdStream Music Dataset Build Pipeline - Dagster Definitions

This module defines the complete Dagster pipeline for building music datasets
following the sequential processing stages:
1. Spotify sample download
2. Rekordbox XML processing  
3. Spleeter audio separation
4. Sample and stem metadata building
5. Audio segmentation
6. Final metadata file generation
"""

from dagster import (
    Definitions, 
    asset, 
    AssetMaterialization,
    Output,
    RetryPolicy,
    DefaultSensorStatus,
    sensor,
    DefaultScheduleStatus,
    schedule,
    RunRequest,
    SkipReason,
    ConfigurableResource,
    EnvVar
)
from dagster_pandas import DataFrame
import pandas as pd
import os
import json
from pathlib import Path
from typing import Dict, List, Optional
import logging

try:
    from .resources import (
        SpotifyResource,
        AudioProcessingResource, 
        DataPathsResource
    )

    from .assets import (
        stage_1_spotify_download,
        stage_2_rekordbox_processing,
        stage_3_spleeter_processing,
        stage_4_metadata_building,
        stage_5_audio_segmentation,
        stage_6_final_metadata
    )
except ImportError:
    # Fallback for direct execution
    from resources import (
        SpotifyResource,
        AudioProcessingResource, 
        DataPathsResource
    )

    from assets import (
        stage_1_spotify_download,
        stage_2_rekordbox_processing,
        stage_3_spleeter_processing,
        stage_4_metadata_building,
        stage_5_audio_segmentation,
        stage_6_final_metadata
    )

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load all assets
all_assets = [
    stage_1_spotify_download,
    stage_2_rekordbox_processing, 
    stage_3_spleeter_processing,
    stage_4_metadata_building,
    stage_5_audio_segmentation,
    stage_6_final_metadata
]

# Resource configuration
resources = {
    "spotify": SpotifyResource(
        client_id=EnvVar("SPOTIPY_CLIENT_ID"),
        client_secret=EnvVar("SPOTIPY_CLIENT_SECRET")
    ),
    "audio_processor": AudioProcessingResource(),
    "data_paths": DataPathsResource()
}

# Define schedules for automated execution
@schedule(
    cron_schedule="0 2 * * 0",  # Run every Sunday at 2 AM
    job_name="full_dataset_build",
    default_status=DefaultScheduleStatus.STOPPED
)
def weekly_dataset_build():
    """Schedule full dataset build weekly."""
    return RunRequest(
        run_key="weekly_dataset_build",
        tags={"scheduled": "true", "type": "full_build"}
    )

# Define sensors for reactive execution
@sensor(
    asset_selection=all_assets,
    default_status=DefaultSensorStatus.STOPPED
)
def dataset_build_sensor(context):
    """Sensor to trigger pipeline based on file changes."""
    data_paths = DataPathsResource()
    
    # Check if artist catalogue has been updated
    artist_catalogue_path = data_paths.get_artist_catalogue_path()
    
    if artist_catalogue_path.exists():
        last_modified = artist_catalogue_path.stat().st_mtime
        
        # Check if file was modified in the last hour
        import time
        if time.time() - last_modified < 3600:
            return RunRequest(
                run_key=f"sensor_triggered_{int(last_modified)}",
                tags={"triggered_by": "file_change", "file": str(artist_catalogue_path)}
            )
    
    return SkipReason("No file changes detected")

# Main definitions
defs = Definitions(
    assets=all_assets,
    resources=resources,
    schedules=[weekly_dataset_build],
    sensors=[dataset_build_sensor]
)

if __name__ == "__main__":
    # For local development and testing
    from dagster import materialize
    
    logger.info("Starting local pipeline execution...")
    
    try:
        # Materialize all assets in dependency order
        result = materialize(
            assets=all_assets,
            resources=resources
        )
        
        if result.success:
            logger.info("Pipeline completed successfully!")
        else:
            logger.error("Pipeline failed!")
            
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise