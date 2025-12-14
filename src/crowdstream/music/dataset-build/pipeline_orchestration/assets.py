"""
Dagster Assets for CrowdStream Music Dataset Pipeline

This module implements the six-stage pipeline as Dagster assets:
1. Spotify sample download
2. Rekordbox XML processing  
3. Spleeter audio separation
4. Sample and stem metadata building
5. Audio segmentation
6. Final metadata file generation
"""

from dagster import (
    asset, 
    AssetMaterialization, 
    Output,
    RetryPolicy,
    get_dagster_logger,
    MetadataValue,
    MaterializeResult
)
from dagster_pandas import DataFrame
import pandas as pd
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests
from urllib.parse import unquote
from pydub import AudioSegment
import librosa
import ast
from collections import Counter
import time

try:
    from .resources import (
        SpotifyResource, 
        AudioProcessingResource, 
        DataPathsResource,
        SpleeterResource
    )
except ImportError:
    from resources import (
        SpotifyResource, 
        AudioProcessingResource, 
        DataPathsResource,
        SpleeterResource
    )

logger = get_dagster_logger()

# Stage 1: Spotify Sample Download
@asset(
    name="stage_1_spotify_download",
    description="Download 30-second samples from Spotify for artists in catalogue",
    retry_policy=RetryPolicy(max_retries=3),
    compute_kind="spotify_api"
)
def stage_1_spotify_download(
    spotify: SpotifyResource,
    data_paths: DataPathsResource
) -> MaterializeResult:
    """
    Download Spotify samples and track metadata for all artists in catalogue.
    
    This asset implements the functionality from 1_spotify_30sec_samples_download.py
    """
    logger.info("Starting Stage 1: Spotify sample download")
    
    # Ensure directories exist
    data_paths.ensure_directories()
    
    # Load artist catalogue
    catalogue_path = data_paths.get_artist_catalogue_path()
    if not catalogue_path.exists():
        raise FileNotFoundError(f"Artist catalogue not found: {catalogue_path}")
    
    artist_catalogue = spotify.load_artist_catalogue(catalogue_path)
    sp = spotify.get_spotify_client()
    
    # Statistics tracking
    total_artists = len(artist_catalogue)
    processed_artists = 0
    total_tracks_downloaded = 0
    failed_downloads = 0
    
    track_data_dir = data_paths.get_track_data_dir()
    sample_audio_dir = data_paths.get_sample_audio_dir()
    
    for artist_name, artist_uri in artist_catalogue.items():
        try:
            logger.info(f"Processing artist: {artist_name}")
            
            # Create artist directories
            artist_track_dir = track_data_dir / artist_name
            artist_audio_dir = sample_audio_dir / artist_name
            artist_track_dir.mkdir(parents=True, exist_ok=True)
            artist_audio_dir.mkdir(parents=True, exist_ok=True)
            
            # Get artist albums and singles
            albums = []
            results = sp.artist_albums(artist_uri, album_type='album')
            albums.extend(results['items'])
            while results['next']:
                results = sp.next(results)
                albums.extend(results['items'])
            
            singles = []
            results = sp.artist_albums(artist_uri, album_type='single')
            singles.extend(results['items'])
            while results['next']:
                results = sp.next(results)
                singles.extend(results['items'])
            
            all_releases = albums + singles
            
            # Get all tracks from releases
            artist_tracks = []
            for release in all_releases:
                try:
                    results = sp.album_tracks(release['id'])
                    artist_tracks.extend(results['items'])
                    while results['next']:
                        results = sp.next(results)
                        artist_tracks.extend(results['items'])
                except Exception as e:
                    logger.warning(f"Failed to get tracks for release {release['id']}: {e}")
                    continue
            
            # Download samples and save metadata
            for track in artist_tracks:
                try:
                    track_id = track['id']
                    preview_url = track.get('preview_url')
                    
                    if preview_url:
                        # Download audio sample
                        audio_file_path = artist_audio_dir / f"{track_id}.mp3"
                        if not audio_file_path.exists():
                            response = requests.get(preview_url, timeout=30)
                            response.raise_for_status()
                            
                            with open(audio_file_path, 'wb') as f:
                                f.write(response.content)
                            
                            logger.debug(f"Downloaded sample: {track_id}")
                        
                        # Save track metadata
                        metadata_file_path = artist_track_dir / f"{track_id}.json"
                        if not metadata_file_path.exists():
                            with open(metadata_file_path, 'w', encoding='utf-8') as f:
                                json.dump(track, f, indent=2, ensure_ascii=False)
                        
                        total_tracks_downloaded += 1
                    else:
                        logger.debug(f"No preview available for track: {track_id}")
                        
                except Exception as e:
                    logger.warning(f"Failed to download track {track.get('id', 'unknown')}: {e}")
                    failed_downloads += 1
                    continue
            
            processed_artists += 1
            logger.info(f"Completed artist {artist_name} ({processed_artists}/{total_artists})")
            
        except Exception as e:
            logger.error(f"Failed to process artist {artist_name}: {e}")
            continue
    
    # Return materialization result with metadata
    return MaterializeResult(
        metadata={
            "total_artists": total_artists,
            "processed_artists": processed_artists,
            "total_tracks_downloaded": total_tracks_downloaded,
            "failed_downloads": failed_downloads,
            "success_rate": f"{(total_tracks_downloaded/(total_tracks_downloaded + failed_downloads))*100:.2f}%" if (total_tracks_downloaded + failed_downloads) > 0 else "N/A"
        }
    )

# Stage 2: Rekordbox XML Processing  
@asset(
    name="stage_2_rekordbox_processing",
    description="Process Rekordbox XML file to extract BPM and key information",
    deps=[stage_1_spotify_download],
    compute_kind="xml_processing"
)
def stage_2_rekordbox_processing(
    data_paths: DataPathsResource
) -> MaterializeResult:
    """
    Process Rekordbox XML file to extract track analysis data.
    
    This asset implements the functionality from 2_build_rekordbox_xml.py
    """
    logger.info("Starting Stage 2: Rekordbox XML processing")
    
    rekordbox_xml_path = data_paths.get_rekordbox_xml_path()
    
    if not rekordbox_xml_path.exists():
        logger.warning(f"Rekordbox XML file not found: {rekordbox_xml_path}")
        logger.info("Please export your Rekordbox collection as XML and place it at the expected path")
        
        # Create a placeholder file with instructions
        rekordbox_xml_path.parent.mkdir(parents=True, exist_ok=True)
        instructions = """
<!-- Rekordbox XML Export Instructions -->
<!-- 1. Drag and drop audio files from Stage 1 into Rekordbox playlist/gallery -->
<!-- 2. Ensure all tracks are analyzed (BPM, key detection) -->  
<!-- 3. Go to File > Export Collection in XML format -->
<!-- 4. Save the exported XML file at this location -->
        """
        with open(rekordbox_xml_path, 'w') as f:
            f.write(instructions)
            
        return MaterializeResult(
            metadata={
                "status": "pending_manual_export",
                "instructions_file_created": str(rekordbox_xml_path),
                "tracks_processed": 0
            }
        )
    
    try:
        # Parse XML file
        tree = ET.parse(rekordbox_xml_path)
        root = tree.getroot()
        
        tracks_processed = 0
        rekordbox_data = {}
        
        for track in root.findall('.//TRACK'):
            track_info = {
                'TrackID': track.get('TrackID'),
                'Name': track.get('Name'),
                'Location': track.get('Location'),
                'AverageBpm': float(track.get('AverageBpm', 0)) if track.get('AverageBpm') else None,
                'Tonality': track.get('Tonality'),
                'BitRate': int(track.get('BitRate', 0)) if track.get('BitRate') else None,
                'SampleRate': int(track.get('SampleRate', 0)) if track.get('SampleRate') else None,
                'TotalTime': int(track.get('TotalTime', 0)) if track.get('TotalTime') else None,
                'PlayCount': int(track.get('PlayCount', 0)) if track.get('PlayCount') else None,
                'DateAdded': track.get('DateAdded'),
                'TEMPO': []
            }
            
            # Extract tempo markers
            for tempo in track.findall('TEMPO'):
                tempo_info = (
                    float(tempo.get('Inizio', 0)),
                    float(tempo.get('Bpm', 0)), 
                    tempo.get('Metro'),
                    int(tempo.get('Battito', 0))
                )
                track_info['TEMPO'].append(tempo_info)
            
            rekordbox_data[track_info['Name']] = track_info
            tracks_processed += 1
        
        # Save processed Rekordbox data
        metadata_dir = data_paths.get_metadata_dir()
        rekordbox_processed_path = metadata_dir / "rekordbox_processed.json"
        
        with open(rekordbox_processed_path, 'w', encoding='utf-8') as f:
            json.dump(rekordbox_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Processed {tracks_processed} tracks from Rekordbox XML")
        
        return MaterializeResult(
            metadata={
                "status": "completed",
                "tracks_processed": tracks_processed,
                "output_file": str(rekordbox_processed_path),
                "xml_source": str(rekordbox_xml_path)
            }
        )
        
    except ET.ParseError as e:
        logger.error(f"Failed to parse Rekordbox XML: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing Rekordbox XML: {e}")
        raise

# Stage 3: Spleeter Processing
@asset(
    name="stage_3_spleeter_processing", 
    description="Separate audio samples into stems using Spleeter",
    deps=[stage_1_spotify_download],
    retry_policy=RetryPolicy(max_retries=2),
    compute_kind="audio_separation"
)
def stage_3_spleeter_processing(
    data_paths: DataPathsResource,
    audio_processor: AudioProcessingResource
) -> MaterializeResult:
    """
    Separate audio samples into stems using Spleeter.
    
    This asset implements the functionality from 3_spleeter_processing.py
    """
    logger.info("Starting Stage 3: Spleeter audio separation")
    
    sample_audio_dir = data_paths.get_sample_audio_dir()
    stems_dir = data_paths.get_stems_dir()
    
    if not sample_audio_dir.exists():
        raise FileNotFoundError(f"Sample audio directory not found: {sample_audio_dir}")
    
    # Find all audio files to process
    audio_files = []
    for artist_dir in sample_audio_dir.iterdir():
        if artist_dir.is_dir() and artist_dir.name != "stems":
            for audio_file in artist_dir.glob("*.mp3"):
                audio_files.append(audio_file)
    
    if not audio_files:
        logger.warning("No audio files found for Spleeter processing")
        return MaterializeResult(
            metadata={
                "status": "no_files_found",
                "files_processed": 0,
                "stems_created": 0
            }
        )
    
    logger.info(f"Found {len(audio_files)} audio files for processing")
    
    files_processed = 0
    stems_created = 0
    failed_separations = 0
    
    # Process each audio file
    for audio_file in audio_files:
        try:
            logger.info(f"Processing: {audio_file.name}")
            
            # Create output directory for this track's stems
            track_stems_dir = stems_dir / audio_file.stem
            track_stems_dir.mkdir(parents=True, exist_ok=True)
            
            # Check if stems already exist
            expected_stems = ["vocals.wav", "drums.wav", "bass.wav", "piano.wav", "other.wav"]
            existing_stems = [stem for stem in expected_stems if (track_stems_dir / stem).exists()]
            
            if len(existing_stems) == len(expected_stems):
                logger.debug(f"Stems already exist for {audio_file.name}, skipping")
                stems_created += len(existing_stems)
                files_processed += 1
                continue
            
            # Run Spleeter separation
            try:
                # Using command line Spleeter (more reliable than Python API)
                cmd = [
                    "spleeter", "separate",
                    "-p", "spleeter:5stems-16kHz",
                    "-o", str(stems_dir),
                    str(audio_file)
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout per file
                )
                
                if result.returncode == 0:
                    # Count created stems
                    created_stems = list(track_stems_dir.glob("*.wav"))
                    stems_created += len(created_stems)
                    files_processed += 1
                    logger.info(f"Successfully separated {audio_file.name} into {len(created_stems)} stems")
                else:
                    logger.error(f"Spleeter failed for {audio_file.name}: {result.stderr}")
                    failed_separations += 1
                    
            except subprocess.TimeoutExpired:
                logger.error(f"Spleeter timeout for {audio_file.name}")
                failed_separations += 1
            except FileNotFoundError:
                logger.error("Spleeter not found. Please install Spleeter: pip install spleeter")
                raise
                
        except Exception as e:
            logger.error(f"Failed to process {audio_file.name}: {e}")
            failed_separations += 1
            continue
    
    success_rate = (files_processed / len(audio_files)) * 100 if audio_files else 0
    
    return MaterializeResult(
        metadata={
            "status": "completed",
            "total_files": len(audio_files),
            "files_processed": files_processed,
            "stems_created": stems_created,
            "failed_separations": failed_separations,
            "success_rate": f"{success_rate:.2f}%"
        }
    )

# Stage 4: Sample and Stem Metadata Building
@asset(
    name="stage_4_metadata_building",
    description="Build comprehensive metadata combining Spotify and Rekordbox data",
    deps=[stage_1_spotify_download, stage_2_rekordbox_processing, stage_3_spleeter_processing],
    compute_kind="metadata_processing"
)
def stage_4_metadata_building(
    data_paths: DataPathsResource
) -> MaterializeResult:
    """
    Build sample and stem metadata by combining Spotify, Rekordbox, and file system data.
    
    This asset implements the functionality from 4_build_sample_and_stem_metadata.py
    """
    logger.info("Starting Stage 4: Sample and stem metadata building")
    
    track_data_dir = data_paths.get_track_data_dir()
    sample_audio_dir = data_paths.get_sample_audio_dir()
    stems_dir = data_paths.get_stems_dir()
    metadata_dir = data_paths.get_metadata_dir()
    
    # Load Rekordbox data if available
    rekordbox_data = {}
    rekordbox_processed_path = metadata_dir / "rekordbox_processed.json"
    if rekordbox_processed_path.exists():
        with open(rekordbox_processed_path, 'r', encoding='utf-8') as f:
            rekordbox_data = json.load(f)
        logger.info(f"Loaded Rekordbox data for {len(rekordbox_data)} tracks")
    else:
        logger.warning("No Rekordbox data found, continuing without BPM/key information")
    
    # Build comprehensive metadata
    metadata_entries = []
    processed_tracks = 0
    
    # Iterate through each artist directory
    for artist_dir in track_data_dir.iterdir():
        if not artist_dir.is_dir():
            continue
            
        artist_name = artist_dir.name
        logger.info(f"Processing metadata for artist: {artist_name}")
        
        # Process each track
        for track_metadata_file in artist_dir.glob("*.json"):
            try:
                track_id = track_metadata_file.stem
                
                # Load Spotify track metadata
                with open(track_metadata_file, 'r', encoding='utf-8') as f:
                    spotify_track = json.load(f)
                
                # Check for sample audio file
                sample_audio_path = sample_audio_dir / artist_name / f"{track_id}.mp3"
                has_sample = sample_audio_path.exists()
                
                # Check for stems
                track_stems_dir = stems_dir / track_id
                stem_files = list(track_stems_dir.glob("*.wav")) if track_stems_dir.exists() else []
                has_stems = len(stem_files) > 0
                stem_count = len(stem_files)
                
                # Find matching Rekordbox data
                track_name = f"spotify-track-{track_id}"
                rekordbox_match = rekordbox_data.get(track_name, {})
                
                # Build metadata entry
                entry = {
                    "id": track_id,
                    "artist": artist_name,
                    "name": spotify_track.get("name", ""),
                    "duration_ms": spotify_track.get("duration_ms"),
                    "explicit": spotify_track.get("explicit", False),
                    "external_urls": spotify_track.get("external_urls", {}),
                    "popularity": spotify_track.get("popularity"),
                    "preview_url": spotify_track.get("preview_url"),
                    "track_number": spotify_track.get("track_number"),
                    "uri": spotify_track.get("uri"),
                    
                    # File system info
                    "has_sample": has_sample,
                    "has_stems": has_stems,
                    "stem_count": stem_count,
                    "stem_files": [stem.name for stem in stem_files],
                    
                    # Rekordbox data (if available)
                    "rekordbox_match": bool(rekordbox_match),
                    "average_bpm": rekordbox_match.get("AverageBpm"),
                    "tonality": rekordbox_match.get("Tonality"),
                    "tempo_markers": rekordbox_match.get("TEMPO", []),
                    
                    # Processing timestamps
                    "processed_at": time.time(),
                    "sample_file_path": str(sample_audio_path) if has_sample else None,
                    "stems_directory": str(track_stems_dir) if has_stems else None
                }
                
                metadata_entries.append(entry)
                processed_tracks += 1
                
            except Exception as e:
                logger.error(f"Failed to process metadata for {track_metadata_file}: {e}")
                continue
    
    # Create DataFrame and save as CSV
    if metadata_entries:
        df = pd.DataFrame(metadata_entries)
        
        # Save comprehensive metadata
        metadata_csv_path = metadata_dir / "track_metadata_complete.csv"
        df.to_csv(metadata_csv_path, index=False)
        
        # Generate summary statistics
        total_tracks = len(df)
        tracks_with_samples = df['has_sample'].sum()
        tracks_with_stems = df['has_stems'].sum()
        tracks_with_rekordbox = df['rekordbox_match'].sum()
        
        avg_stem_count = df[df['has_stems']]['stem_count'].mean() if tracks_with_stems > 0 else 0
        
        logger.info(f"Metadata processing completed: {total_tracks} tracks processed")
        
        return MaterializeResult(
            metadata={
                "total_tracks": total_tracks,
                "tracks_with_samples": int(tracks_with_samples),
                "tracks_with_stems": int(tracks_with_stems),
                "tracks_with_rekordbox": int(tracks_with_rekordbox),
                "average_stem_count": f"{avg_stem_count:.2f}",
                "output_file": str(metadata_csv_path),
                "sample_completion_rate": f"{(tracks_with_samples/total_tracks)*100:.2f}%",
                "stems_completion_rate": f"{(tracks_with_stems/total_tracks)*100:.2f}%"
            }
        )
    else:
        logger.warning("No metadata entries created")
        return MaterializeResult(
            metadata={
                "total_tracks": 0,
                "status": "no_data_processed"
            }
        )

# Stage 5: Audio Segmentation
@asset(
    name="stage_5_audio_segmentation",
    description="Create BPM-synchronized audio segments and loops",
    deps=[stage_4_metadata_building],
    compute_kind="audio_processing"
)
def stage_5_audio_segmentation(
    data_paths: DataPathsResource,
    audio_processor: AudioProcessingResource
) -> MaterializeResult:
    """
    Create audio segments and loops from stems based on BPM analysis.
    
    This asset implements the functionality from 5_segment_audios.py
    """
    logger.info("Starting Stage 5: Audio segmentation")
    
    metadata_dir = data_paths.get_metadata_dir()
    stems_dir = data_paths.get_stems_dir()
    loops_dir = data_paths.get_loops_dir()
    
    # Load track metadata
    metadata_csv_path = metadata_dir / "track_metadata_complete.csv"
    if not metadata_csv_path.exists():
        raise FileNotFoundError(f"Track metadata not found: {metadata_csv_path}")
    
    df = pd.read_csv(metadata_csv_path)
    
    # Filter tracks suitable for segmentation
    suitable_tracks = df[
        (df['has_stems'] == True) &
        (df['average_bpm'].notna()) &
        (df['average_bpm'] >= 80) &
        (df['average_bpm'] <= 145) &
        (df['stem_count'] >= 4)
    ].copy()
    
    if suitable_tracks.empty:
        logger.warning("No tracks suitable for segmentation found")
        return MaterializeResult(
            metadata={
                "suitable_tracks": 0,
                "segments_created": 0,
                "status": "no_suitable_tracks"
            }
        )
    
    logger.info(f"Processing {len(suitable_tracks)} tracks for segmentation")
    
    segments_created = 0
    tracks_processed = 0
    failed_processing = 0
    
    for _, track in suitable_tracks.iterrows():
        try:
            track_id = track['id']
            bpm = track['average_bpm']
            artist = track['artist']
            
            logger.info(f"Segmenting track {track_id} (BPM: {bpm})")
            
            # Create loops directory for this track
            track_loops_dir = loops_dir / artist / track_id
            track_loops_dir.mkdir(parents=True, exist_ok=True)
            
            # Find stem files
            track_stems_dir = stems_dir / track_id
            stem_files = list(track_stems_dir.glob("*.wav"))
            
            if not stem_files:
                logger.warning(f"No stem files found for track {track_id}")
                failed_processing += 1
                continue
            
            # Calculate segment parameters
            beat_duration_ms = (60 / bpm) * 1000
            segment_duration_ms = beat_duration_ms * audio_processor.segment_beats
            
            # Process each stem
            track_segments = 0
            for stem_file in stem_files:
                try:
                    # Load audio
                    audio = AudioSegment.from_wav(str(stem_file))
                    stem_name = stem_file.stem
                    
                    # Calculate how many complete segments we can extract
                    max_segments = int(len(audio) / segment_duration_ms)
                    
                    if max_segments == 0:
                        logger.warning(f"Audio too short for segmentation: {stem_file.name}")
                        continue
                    
                    # Extract segments with crossfading
                    for segment_idx in range(min(max_segments, 3)):  # Limit to 3 segments per stem
                        start_ms = segment_idx * segment_duration_ms
                        end_ms = start_ms + segment_duration_ms
                        
                        # Extract segment
                        segment = audio[start_ms:end_ms]
                        
                        # Apply crossfade for seamless looping
                        crossfade_ms = int(audio_processor.crossfade_duration * 1000)
                        if len(segment) > crossfade_ms * 2:
                            # Crossfade end to beginning for seamless looping
                            fade_out_part = segment[-crossfade_ms:]
                            fade_in_part = segment[:crossfade_ms]
                            
                            # Apply crossfade
                            crossfaded = fade_out_part.fade_out(crossfade_ms).overlay(
                                fade_in_part.fade_in(crossfade_ms)
                            )
                            
                            # Replace the beginning with crossfaded part
                            segment = crossfaded + segment[crossfade_ms:-crossfade_ms]
                        
                        # Save segment
                        segment_filename = f"{track_id}_{stem_name}_seg{segment_idx:02d}_bpm{int(bpm)}.wav"
                        segment_path = track_loops_dir / segment_filename
                        
                        segment.export(str(segment_path), format="wav")
                        track_segments += 1
                        segments_created += 1
                        
                        logger.debug(f"Created segment: {segment_filename}")
                
                except Exception as e:
                    logger.error(f"Failed to process stem {stem_file.name}: {e}")
                    continue
            
            if track_segments > 0:
                tracks_processed += 1
                logger.info(f"Created {track_segments} segments for track {track_id}")
            else:
                failed_processing += 1
                
        except Exception as e:
            logger.error(f"Failed to process track {track['id']}: {e}")
            failed_processing += 1
            continue
    
    # Generate loops metadata
    loops_metadata = []
    for loops_file in loops_dir.rglob("*.wav"):
        try:
            # Parse filename to extract metadata
            filename_parts = loops_file.stem.split('_')
            if len(filename_parts) >= 4:
                track_id = filename_parts[0]
                stem_type = filename_parts[1]
                segment_info = filename_parts[2]
                bpm_info = filename_parts[3]
                
                # Get audio info
                audio_info = audio_processor.get_audio_info(loops_file)
                
                loops_metadata.append({
                    "file_name": loops_file.name,
                    "track_id": track_id,
                    "stem_type": stem_type,
                    "segment_info": segment_info,
                    "bpm": int(bpm_info.replace("bpm", "")),
                    "duration_ms": audio_info.get("duration_ms"),
                    "file_path": str(loops_file),
                    "file_size_bytes": audio_info.get("file_size_bytes")
                })
        except Exception as e:
            logger.warning(f"Failed to extract metadata from {loops_file.name}: {e}")
            continue
    
    # Save loops metadata
    if loops_metadata:
        loops_df = pd.DataFrame(loops_metadata)
        loops_metadata_path = metadata_dir / "loops_metadata.csv"
        loops_df.to_csv(loops_metadata_path, index=False)
        
        logger.info(f"Saved metadata for {len(loops_metadata)} loops")
    
    return MaterializeResult(
        metadata={
            "suitable_tracks": len(suitable_tracks),
            "tracks_processed": tracks_processed,
            "failed_processing": failed_processing,
            "segments_created": segments_created,
            "loops_metadata_entries": len(loops_metadata),
            "success_rate": f"{(tracks_processed/len(suitable_tracks))*100:.2f}%" if len(suitable_tracks) > 0 else "N/A"
        }
    )

# Stage 6: Final Metadata File Generation
@asset(
    name="stage_6_final_metadata",
    description="Generate final dataset with harmonic key relationships and playlist algorithms",
    deps=[stage_5_audio_segmentation],
    compute_kind="data_finalization"
)
def stage_6_final_metadata(
    data_paths: DataPathsResource
) -> MaterializeResult:
    """
    Generate final metadata file with harmonic key relationships and intelligent playlist features.
    
    This asset implements the functionality from 6_audio_processor_build_final_metadata_file.py
    """
    logger.info("Starting Stage 6: Final metadata file generation")
    
    metadata_dir = data_paths.get_metadata_dir()
    
    # Load existing metadata
    track_metadata_path = metadata_dir / "track_metadata_complete.csv"
    loops_metadata_path = metadata_dir / "loops_metadata.csv"
    
    if not track_metadata_path.exists():
        raise FileNotFoundError(f"Track metadata not found: {track_metadata_path}")
    
    track_df = pd.read_csv(track_metadata_path)
    
    loops_df = pd.DataFrame()
    if loops_metadata_path.exists():
        loops_df = pd.read_csv(loops_metadata_path)
        logger.info(f"Loaded {len(loops_df)} loops metadata entries")
    else:
        logger.warning("No loops metadata found")
    
    # Define harmonic key relationships (Circle of Fifths)
    keys_affinity = {
        "Abm": {"affinity_1": ["Abm", "Ebm"], "affinity_2": ["Dbm", "B", "Bbm"]},
        "B": {"affinity_1": ["B", "F#"], "affinity_2": ["E", "Abm", "Db"]},
        "Ebm": {"affinity_1": ["Ebm", "Bbm"], "affinity_2": ["Abm", "F#", "Fm"]},
        "F#": {"affinity_1": ["F#", "Db"], "affinity_2": ["B", "Ebm", "Ab"]},
        "Bbm": {"affinity_1": ["Bbm", "Fm"], "affinity_2": ["Ebm", "Db", "Cm"]},
        "Db": {"affinity_1": ["Db", "Ab"], "affinity_2": ["F#", "Bbm", "Eb"]},
        "Fm": {"affinity_1": ["Fm", "Cm"], "affinity_2": ["Bbm", "Ab", "Gm"]},
        "Ab": {"affinity_1": ["Ab", "Eb"], "affinity_2": ["Db", "Fm", "Bb"]},
        "Cm": {"affinity_1": ["Cm", "Gm"], "affinity_2": ["Fm", "Eb", "Dm"]},
        "Eb": {"affinity_1": ["Eb", "Bb"], "affinity_2": ["Ab", "Cm", "F"]},
        "Gm": {"affinity_1": ["Gm", "Dm"], "affinity_2": ["Cm", "Bb", "Am"]},
        "Bb": {"affinity_1": ["Bb", "F"], "affinity_2": ["Eb", "Gm", "C"]},
        "Dm": {"affinity_1": ["Dm", "Am"], "affinity_2": ["Gm", "C", "Em"]},
        "F": {"affinity_1": ["F", "C"], "affinity_2": ["Bb", "Dm", "G"]},
        "Am": {"affinity_1": ["Am", "Em"], "affinity_2": ["Dm", "G", "F#m"]},
        "C": {"affinity_1": ["C", "G"], "affinity_2": ["F", "Am", "D"]},
        "Em": {"affinity_1": ["Em", "Bm"], "affinity_2": ["Am", "D", "Abm"]},
        "G": {"affinity_1": ["G", "D"], "affinity_2": ["C", "Em", "A"]},
        "Bm": {"affinity_1": ["Bm", "F#m"], "affinity_2": ["Em", "A", "Bbm"]},
        "D": {"affinity_1": ["D", "A"], "affinity_2": ["G", "Bm", "E"]},
        "F#m": {"affinity_1": ["F#m", "Dbm"], "affinity_2": ["Bm", "E", "Fm"]},
        "A": {"affinity_1": ["A", "E"], "affinity_2": ["D", "F#m", "B"]},
        "Dbm": {"affinity_1": ["Dbm", "Abm"], "affinity_2": ["F#m", "B", "Cm"]},
        "E": {"affinity_1": ["E", "B"], "affinity_2": ["A", "Dbm", "F#"]}
    }
    
    # Add harmonic compatibility to tracks with key information
    enhanced_tracks = []
    tracks_with_keys = 0
    
    for _, track in track_df.iterrows():
        track_dict = track.to_dict()
        
        # Add harmonic compatibility if tonality is available
        if pd.notna(track['tonality']) and track['tonality'] in keys_affinity:
            key = track['tonality']
            track_dict['harmonic_affinity_1'] = keys_affinity[key]['affinity_1']
            track_dict['harmonic_affinity_2'] = keys_affinity[key]['affinity_2']
            track_dict['has_harmonic_data'] = True
            tracks_with_keys += 1
        else:
            track_dict['harmonic_affinity_1'] = []
            track_dict['harmonic_affinity_2'] = []
            track_dict['has_harmonic_data'] = False
        
        # Add BPM category
        if pd.notna(track['average_bpm']):
            bpm = track['average_bpm']
            if bpm < 90:
                track_dict['bpm_category'] = 'slow'
            elif bpm < 120:
                track_dict['bpm_category'] = 'medium'
            elif bpm < 140:
                track_dict['bpm_category'] = 'fast'
            else:  
                track_dict['bpm_category'] = 'very_fast'
        else:
            track_dict['bpm_category'] = 'unknown'
        
        # Add suitability flags
        track_dict['suitable_for_mixing'] = (
            track['has_stems'] and 
            pd.notna(track['average_bpm']) and 
            80 <= track['average_bpm'] <= 145 and
            track['stem_count'] >= 4
        )
        
        track_dict['suitable_for_harmonic_mixing'] = (
            track_dict['suitable_for_mixing'] and 
            track_dict['has_harmonic_data']
        )
        
        enhanced_tracks.append(track_dict)
    
    # Create enhanced DataFrame
    enhanced_df = pd.DataFrame(enhanced_tracks)
    
    # Generate playlist recommendations
    playlist_recommendations = []
    
    # Find tracks suitable for harmonic mixing
    mixable_tracks = enhanced_df[enhanced_df['suitable_for_harmonic_mixing'] == True]
    
    if not mixable_tracks.empty:
        logger.info(f"Generating playlist recommendations for {len(mixable_tracks)} mixable tracks")
        
        for _, track in mixable_tracks.iterrows():
            # Find compatible tracks
            compatible_tracks = mixable_tracks[
                (mixable_tracks['tonality'].isin(track['harmonic_affinity_1'] + track['harmonic_affinity_2'])) &
                (abs(mixable_tracks['average_bpm'] - track['average_bpm']) <= 5) &  # BPM within 5
                (mixable_tracks['id'] != track['id'])  # Exclude self
            ]
            
            if not compatible_tracks.empty:
                playlist_recommendations.append({
                    'source_track_id': track['id'],
                    'source_artist': track['artist'],
                    'source_key': track['tonality'],
                    'source_bpm': track['average_bpm'],
                    'compatible_track_ids': compatible_tracks['id'].tolist(),
                    'compatibility_count': len(compatible_tracks)
                })
    
    # Save final dataset files
    final_dataset_path = metadata_dir / "final_dataset.csv"
    enhanced_df.to_csv(final_dataset_path, index=False)
    
    # Save playlist recommendations
    if playlist_recommendations:
        playlist_df = pd.DataFrame(playlist_recommendations)
        playlist_path = metadata_dir / "playlist_recommendations.csv"
        playlist_df.to_csv(playlist_path, index=False)
        logger.info(f"Generated {len(playlist_recommendations)} playlist recommendations")
    
    # Generate summary statistics
    total_tracks = len(enhanced_df)
    tracks_with_samples = enhanced_df['has_sample'].sum()
    tracks_with_stems = enhanced_df['has_stems'].sum()
    mixable_tracks_count = enhanced_df['suitable_for_mixing'].sum()
    harmonic_mixable_count = enhanced_df['suitable_for_harmonic_mixing'].sum()
    
    # BPM distribution
    bpm_distribution = enhanced_df['bpm_category'].value_counts().to_dict()
    
    # Generate summary report
    summary_report = {
        "dataset_summary": {
            "total_tracks": int(total_tracks),
            "tracks_with_samples": int(tracks_with_samples),
            "tracks_with_stems": int(tracks_with_stems),
            "tracks_with_keys": int(tracks_with_keys),
            "mixable_tracks": int(mixable_tracks_count),
            "harmonic_mixable_tracks": int(harmonic_mixable_count),
            "playlist_recommendations": len(playlist_recommendations)
        },
        "completion_rates": {
            "sample_rate": f"{(tracks_with_samples/total_tracks)*100:.2f}%",
            "stems_rate": f"{(tracks_with_stems/total_tracks)*100:.2f}%",
            "keys_rate": f"{(tracks_with_keys/total_tracks)*100:.2f}%",
            "mixing_suitability": f"{(mixable_tracks_count/total_tracks)*100:.2f}%"
        },
        "bpm_distribution": bpm_distribution,
        "output_files": {
            "final_dataset": str(final_dataset_path),
            "playlist_recommendations": str(playlist_path) if playlist_recommendations else None,
            "loops_metadata": str(loops_metadata_path) if loops_metadata_path.exists() else None
        },
        "generation_timestamp": time.time()
    }
    
    # Save summary report
    summary_path = metadata_dir / "dataset_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary_report, f, indent=2, ensure_ascii=False)
    
    logger.info("Final dataset generation completed successfully")
    
    return MaterializeResult(
        metadata={
            "total_tracks": int(total_tracks),
            "mixable_tracks": int(mixable_tracks_count),
            "harmonic_mixable_tracks": int(harmonic_mixable_count),
            "playlist_recommendations": len(playlist_recommendations),
            "final_dataset_path": str(final_dataset_path),
            "dataset_summary_path": str(summary_path),
            "processing_complete": True
        }
    )