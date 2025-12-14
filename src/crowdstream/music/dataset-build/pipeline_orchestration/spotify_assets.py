import os
import json
from pathlib import Path
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import requests
from dagster import asset

# Define paths relative to this file to make them robust
SCRIPT_DIR = Path(__file__).parent
DATASET_BUILD_DIR = SCRIPT_DIR.parent
ARTIST_CATALOGUE = DATASET_BUILD_DIR / 'artist_catalogue.json'
TRACK_DATA_DIR = DATASET_BUILD_DIR / 'track_data'
SAMPLE_AUDIO_DIR = DATASET_BUILD_DIR / 'sample_audio'

class SpotifyHandler:
    def __init__(self, client_id, client_secret):
        self.client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        self.sp = spotipy.Spotify(client_credentials_manager=self.client_credentials_manager)
        self.artist_catalogue = self._load_artist_catalogue()

    def _load_artist_catalogue(self):
        with open(ARTIST_CATALOGUE, 'r', encoding='utf-8') as file:
            return json.load(file)

    def save_artist_track_data(self, artist):
        birdy_uri = self.artist_catalogue[artist]
        artist_folder = TRACK_DATA_DIR / artist
        artist_folder.mkdir(parents=True, exist_ok=True)
        
        try:
            results = self.sp.artist_albums(birdy_uri, album_type='album')
            albums = results['items']
            while results['next']:
                results = self.sp.next(results)
                albums.extend(results['items'])
            
            results_singles = self.sp.artist_albums(birdy_uri, album_type='single')
            singles = results_singles['items']
            while results_singles['next']:
                results_singles = self.sp.next(results_singles)
                singles.extend(results_singles['items'])
            
            all_releases = albums + singles
            
            track_list_singles = []
            for release in all_releases:
                results = self.sp.album_tracks(release['id'])
                track_list_singles.extend(results['items'])
                while results['next']:
                    results = self.sp.next(results)
                    track_list_singles.extend(results['items'])
            
            with open(artist_folder / f'{birdy_uri}.json', 'w') as handle:
                json.dump(track_list_singles, handle, indent=4)
        
        except Exception as e:
            print(f"An error occurred: {e}")

    def save_artist_sample_audio(self, artist):
        birdy_uri = self.artist_catalogue[artist]
        artist_folder = SAMPLE_AUDIO_DIR / artist
        artist_folder.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(TRACK_DATA_DIR / artist / f'{birdy_uri}.json', 'r') as handle:
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

@asset
def spotify_data():
    client_id = os.getenv('SPOTIPY_CLIENT_ID')
    client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')

    if not client_id or not client_secret:
        raise ValueError("Please set the SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET environment variables.")

    spotify_handler = SpotifyHandler(client_id, client_secret)

    for k in spotify_handler.artist_catalogue:
        spotify_handler.save_artist_track_data(k)
        spotify_handler.save_artist_sample_audio(k)