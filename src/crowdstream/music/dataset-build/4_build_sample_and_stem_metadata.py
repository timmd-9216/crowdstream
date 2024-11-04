import os
import json
import pandas as pd
import xml.etree.ElementTree as ET

# Base directory containing artist folders
base_dir = "/Users/xaviergonzalez/Library/Mobile Documents/com~apple~CloudDocs/Desktop/9216 TIMMD/music/track_data"
# Base directory for checking sample audio files
sample_audio_dir = "/Users/xaviergonzalez/Library/Mobile Documents/com~apple~CloudDocs/Desktop/9216 TIMMD/music/sample_audio"
# Base directory for checking stems files
stems_dir = "/Users/xaviergonzalez/Library/Mobile Documents/com~apple~CloudDocs/Desktop/9216 TIMMD/music/sample_audio/stems"
# Path to the Rekordbox XML file
rekordbox_xml_path = "/Users/xaviergonzalez/Library/Mobile Documents/com~apple~CloudDocs/Desktop/9216 TIMMD/music/rekordbox/coll_piojos_AVICII.xml"

# Function to parse the Rekordbox XML file
def parse_rekordbox_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    track_data = {}
    for track in root.findall('.//TRACK'):
        # Extract relevant attributes from the XML
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

# Parse the Rekordbox XML and load it into a dictionary for fast lookups
rekordbox_tracks = parse_rekordbox_xml(rekordbox_xml_path)

# List to store the data
data = []

# Loop through each artist folder in track_data
for artist in os.listdir(base_dir):
    artist_path = os.path.join(base_dir, artist)
    if os.path.isdir(artist_path):
        # Loop through each JSON file in the artist's folder
        for file_name in os.listdir(artist_path):
            if file_name.endswith(".json"):
                json_file_path = os.path.join(artist_path, file_name)
                # Read the JSON file (always a list)
                with open(json_file_path, 'r') as file:
                    track_data = json.load(file)
                    # Process each track in the list
                    for track in track_data:
                        track_id = track.get("id")
                        # Build the path to the sample audio file
                        sample_file_path = os.path.join(sample_audio_dir, artist, f"spotify-track-{track_id}.mp3")
                        # Determine if the sample file exists
                        sample_exists = os.path.isfile(sample_file_path)
                        # Build the path for the stems directory
                        stems_path = os.path.join(stems_dir, f"spotify-track-{track_id}")
                        # Count the number of .wav files in the stems directory
                        wav_count = 0
                        if os.path.isdir(stems_path):
                            wav_count = len([f for f in os.listdir(stems_path) if f.endswith(".wav")])
                        # Check if the track is in the Rekordbox data
                        track_name = f"spotify-track-{track_id}"
                        rekordbox_match = track_name in rekordbox_tracks
                        # Get the Rekordbox metadata if available
                        rekordbox_metadata = rekordbox_tracks.get(track_name, {})
                        tempo_data = rekordbox_metadata.get("TEMPO", [])
                        # Add the entry to the list
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

# Create a DataFrame from the collected data
df = pd.DataFrame(data)

# Save the DataFrame to a CSV file (optional)
df.to_csv("track_data_summary.csv", index=False)

# Display the DataFrame
print(df)