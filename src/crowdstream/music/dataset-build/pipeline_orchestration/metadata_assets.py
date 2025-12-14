import os
import json
import pandas as pd
import xml.etree.ElementTree as ET
from dagster import asset
from pathlib import Path

from .spotify_assets import spotify_data

# Define paths relative to this file
SCRIPT_DIR = Path(__file__).parent
DATASET_BUILD_DIR = SCRIPT_DIR.parent
TRACK_DATA_DIR = DATASET_BUILD_DIR / 'track_data'
SAMPLE_AUDIO_DIR = DATASET_BUILD_DIR / 'sample_audio'
REKORDBOX_XML_PATH = DATASET_BUILD_DIR / "rekordbox.xml"

# Function to parse the Rekordbox XML file
def parse_rekordbox_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    track_data = {}
    for track in root.findall('.//TRACK'):
        track_info = {
            'TrackID': track.get('TrackID'),
            'Name': track.get('Name'),
            'Location': track.get('Location'),
            'AverageBpm': track.get('AverageBpm'),
            'Tonality': track.get('Tonality'),
            'BitRate': track.get('BitRate'),
            'SampleRate': track.get('SampleRate'),
            'TotalTime': track.get('TotalTime'),
            'PlayCount': track.get('PlayCount'),
            'DateAdded': track.get('DateAdded'),
            'TEMPO': [
                (float(tempo.get('Inizio')), float(tempo.get('Bpm')), tempo.get('Metro'), int(tempo.get('Battito')))
                for tempo in track.findall('TEMPO')
            ]
        }
        track_data[track_info['Name']] = track_info

    return track_data

@asset(deps=[spotify_data])
def track_data_summary():
    rekordbox_tracks = {}
    if REKORDBOX_XML_PATH.exists():
        rekordbox_tracks = parse_rekordbox_xml(REKORDBOX_XML_PATH)

    data = []
    for artist in os.listdir(TRACK_DATA_DIR):
        artist_path = os.path.join(TRACK_DATA_DIR, artist)
        if os.path.isdir(artist_path):
            for file_name in os.listdir(artist_path):
                if file_name.endswith(".json"):
                    json_file_path = os.path.join(artist_path, file_name)
                    with open(json_file_path, 'r') as file:
                        track_data = json.load(file)
                        for track in track_data:
                            track_id = track.get("id")
                            sample_file_path = os.path.join(SAMPLE_AUDIO_DIR, artist, f"spotify-track-{track_id}.mp3")
                            sample_exists = os.path.isfile(sample_file_path)
                            stems_path = os.path.join(SAMPLE_AUDIO_DIR, 'stems', f"spotify-track-{track_id}")
                            wav_count = 0
                            if os.path.isdir(stems_path):
                                wav_count = len([f for f in os.listdir(stems_path) if f.endswith(".wav")])
                            track_name = f"spotify-track-{track_id}"
                            rekordbox_match = track_name in rekordbox_tracks
                            rekordbox_metadata = rekordbox_tracks.get(track_name, {})
                            tempo_data = rekordbox_metadata.get("TEMPO", [])
                            entry = {
                                "artist": artist,
                                "duration": track.get("duration_ms"),
                                "id": track_id,
                                "name": track.get("name"),
                                "sample.mp3": sample_exists,
                                "stems.wav": wav_count,
                                "rekorbox": rekordbox_match,
                                "tempo": tempo_data,
                                "TrackID": rekordbox_metadata.get("TrackID"),
                                "Location": rekordbox_metadata.get("Location"),
                                "AverageBpm": rekordbox_metadata.get("AverageBpm"),
                                "Tonality": rekordbox_metadata.get("Tonality"),
                                "BitRate": rekordbox_metadata.get("BitRate"),
                                "SampleRate": rekordbox_metadata.get("SampleRate"),
                                "TotalTime": rekordbox_metadata.get("TotalTime"),
                                "PlayCount": rekordbox_metadata.get("PlayCount"),
                                "DateAdded": rekordbox_metadata.get("DateAdded"),
                            }
                            data.append(entry)

    df = pd.DataFrame(data)
    df.to_csv(DATASET_BUILD_DIR / "track_data_summary.csv", index=False)

    return df