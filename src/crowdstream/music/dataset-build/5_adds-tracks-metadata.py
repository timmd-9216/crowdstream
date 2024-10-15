import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import requests
import json
from pathlib import Path
from pydub import AudioSegment
from urllib.parse import unquote    

# Read environment variables
client_id = os.getenv('SPOTIPY_CLIENT_ID')
client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')

# Ensure the variables are set
if not client_id or not client_secret:
    raise ValueError("Please set the SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET environment variables.")

client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)  # Spotify object to access API

# artist_catalogue = {'Tomas Heredia': '0MxxbjQyul7WXUFy0O6qiu',
#                     'Hernan Cattaneo':'4mpJaw5y17CIN08qqe8EfB',
#                     'Marsh':'1eucLGnPT27tdEh6MU29wp',
#                     'Tinlicker':'5EmEZjq8eHEC6qFnT63Lza',
#                     'Robin S':'2WvLeseDGPX1slhmxI59G3',
#                     'Janice Robinson':'6BXTl7YkINlCQkkzE9hvCd'}

artist_catalogue = {'Angeles Azules': '0ZCO8oVkMj897cKgFH7fRW',
                    'Los Mirlos':'1ga48mxYYI9RuUrWLa3voh',
                    'Antonio Rios':'7s652lD4v77szrPEfgMTBi'}


def save_artist_track_data(artist, sp=sp):
    birdy_uri = artist_catalogue[artist]
    artist_folder = Path('track_data') / artist
    artist_folder.mkdir(parents=True, exist_ok=True)
    
    try:
        # Get albums
        results = sp.artist_albums(birdy_uri, album_type='album')
        albums = results['items']
        while results['next']:
            results = sp.next(results)
            albums.extend(results['items'])
        
        # Get singles
        results_singles = sp.artist_albums(birdy_uri, album_type='single')
        singles = results_singles['items']
        while results_singles['next']:
            results_singles = sp.next(results_singles)
            singles.extend(results_singles['items'])
        
        all_releases = albums + singles
        
        # Get album tracks and save track data
        track_list_singles = []
        for release in all_releases:
            results = sp.album_tracks(release['id'])
            track_list_singles.extend(results['items'])
            while results['next']:
                results = sp.next(results)
                track_list_singles.extend(results['items'])
        
        # Save to JSON
        with open(artist_folder / f'{birdy_uri}.json', 'w') as handle:
            json.dump(track_list_singles, handle, indent=4)
    
    except Exception as e:
        print(f"An error occurred: {e}")

def save_artist_sample_audio(artist, sp=sp):
    birdy_uri = artist_catalogue[artist]
    artist_folder = Path('sample_audio') / artist
    artist_folder.mkdir(parents=True, exist_ok=True)
    
    try:
        # Load track data from JSON
        with open(Path('track_data') / artist / f'{birdy_uri}.json', 'r') as handle:
            track_list = json.load(handle)
        
        for track in track_list:
            url = track.get('preview_url')
            if url:
                try:
                    response = requests.get(url)
                    response.raise_for_status()
                    with open(artist_folder / f'{track["uri"].replace(":", "-")}.mp3', 'wb') as f:
                        f.write(response.content)
                    print(f"Downloaded {track['preview_url']}")
                except requests.RequestException as e:
                    print(f"Failed to download {url}: {e}")
    
    except FileNotFoundError:
        print(f"JSON file not found for artist {artist}")
    except Exception as e:
        print(f"An error occurred: {e}")

'''
# Example usage
artist = 'Robin S'
save_artist_track_data(artist)
save_artist_sample_audio(artist)
'''

import xml.etree.ElementTree as ET
import pandas as pd

# Parse the XML file
tree = ET.parse('rekordbox/collection_cumbia.xml')
root = tree.getroot()

# Initialize an empty list to store track metadata
track_data = []

# Iterate through each track in the collection
for track in root.find('COLLECTION').findall('TRACK'):
    # Extract basic metadata
    track_info = {
        'TrackID': track.get('TrackID'),
        'Name': track.get('Name'),
        'Artist': track.get('Artist'),
        'Album': track.get('Album'),
        'Genre': track.get('Genre'),
        'Location': track.get('Location'),
        'AverageBpm': float(track.get('AverageBpm', 0)),
        'Key': track.get('Tonality')
    }

    # Extract tempo records
    tempo_records = []
    for tempo in track.findall('TEMPO'):
        tempo_info = {
            'Inizio': float(tempo.get('Inizio')),
            'Bpm': float(tempo.get('Bpm')),
            'Metro': tempo.get('Metro'),
            'Battito': int(tempo.get('Battito'))
        }
        tempo_records.append(tempo_info)

    # Add the tempo records to the track info
    track_info['TempoRecords'] = tempo_records
    
    # Add track info to the list
    track_data.append(track_info)

# Convert the list of dictionaries to a pandas DataFrame
df = pd.DataFrame(track_data)

# Display the DataFrame
#print(df.head())

# Save the DataFrame to a CSV file for basic metadata
track_df = df.drop(columns=['TempoRecords'])
track_df.to_csv('track_metadata.csv', index=False)

# Save the tempo records separately
tempo_data = []
for track in track_data:
    for tempo in track['TempoRecords']:
        tempo_data.append({
            'TrackID': track['TrackID'],
            'Name': track['Name'],
            'Inizio': tempo['Inizio'],
            'Bpm': tempo['Bpm'],
            'Metro': tempo['Metro'],
            'Battito': tempo['Battito']
        })

tempo_df = pd.DataFrame(tempo_data)
tempo_df.to_csv('tempo_metadata.csv', index=False)

# Query by key
key_query = 'Cm'
filtered_by_key = df[df['Key'] == key_query]
#print(filtered_by_key)

# Define the base path to filter locations
#base_path = 'file://localhost/Users/xaviergonzalez/Library/Mobile%20Documents/com~apple~CloudDocs/Desktop/9216%20TIMMD/music/sample_audio/'
base_path = './sample_audio/'

# Filter the track_df to include only those locations within the base_path and its subfolders
filtered_track_df = track_df #[base_path in track_df['Location']]

def calculate_duration(beats, bpm):
    return (60 / bpm) * beats

def extract_segment(track_name, output_path, adjustment=0.0):
    
    # Find the track ID from the track name in the filtered dataframe
    track_info = filtered_track_df[filtered_track_df['Name'] == track_name]
    if track_info.empty:
        raise ValueError(f'Track with name {track_name} not found or not in the specified folder.')

    track_id = track_info.iloc[0]['TrackID']
    track_location = unquote(track_info.iloc[0]['Location'].replace('file://localhost', ''))
    
    # Find the tempo information for the given track ID
    tempo_info = tempo_df[tempo_df['TrackID'] == track_id]

    if len(tempo_info) < 1:
        raise ValueError('Not enough tempo points to extract the segment.')

    # Get the start time of the first beat and calculate the end time for 48 beats
    start_time = tempo_info.iloc[0]['Inizio'] + adjustment
    bpm = tempo_info.iloc[0]['Bpm']
    duration = calculate_duration(48, bpm)
    end_time = start_time + duration

    # Convert times from seconds to milliseconds
    start_time_ms = start_time * 1000
    end_time_ms = end_time * 1000

    # Load the audio file
    audio = AudioSegment.from_file(track_location)

    # Extract the segment
    segment = audio[start_time_ms:end_time_ms]

    # Export the segment
    output_file = os.path.join(output_path, f'{track_name}_segment.wav')
    segment.export(output_file, format="wav")
    print(f'Segment saved to {output_file}')

# Example usage

#track_name = 'spotify-track-1oBrF9K3oXROnWhov5dDQk'  # Replace with the track name you want to process
#track_name = 'spotify-track-1cgKW6P31HXhlspXNWSFiP'
# track_name = 'spotify-track-1n1htKGh0CJOU4O59kzwfl'
# output_path = 'delete'  # Replace with your desired output directory
# adjustment = -0.05  # Adjust this value as needed
# extract_segment(track_name, output_path, adjustment)

