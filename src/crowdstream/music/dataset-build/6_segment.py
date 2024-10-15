import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import requests
import json
from pathlib import Path
from pydub import AudioSegment
from urllib.parse import unquote
import pandas as pd
import xml.etree.ElementTree as ET
import librosa

def process_audio_files(directory='sample_audio/loops', track_metadata_csv='track_metadata.csv', 
        output_csv='loops_metadata.csv'):
    # Step 1: List all files in the directory
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

    # Step 2: Create a DataFrame with a column named 'file_name'
    df = pd.DataFrame(files, columns=['file_name'])

    # Step 3: Create a new column 'trackName' with the first 36 characters of 'file_name'
    df['trackName'] = df['file_name'].str[:36]

    # Step 4: Load track metadata
    track_metadata = pd.read_csv(track_metadata_csv)

    # Step 5: Create 'Key' column by matching 'trackName' with 'Name' in track metadata
    df = df.merge(track_metadata[['Name', 'Key']], left_on='trackName', right_on='Name', how='left')
    df.drop(columns=['Name'], inplace=True)  # Drop the 'Name' column after merging

    # Step 6: Create 'Bpm' column by matching 'trackName' with 'AverageBpm' in track metadata
    df = df.merge(track_metadata[['Name', 'AverageBpm']], left_on='trackName', right_on='Name', how='left')
    df.drop(columns=['Name'], inplace=True)  # Drop the 'Name' column after merging

    # Rename the 'AverageBpm' column to 'Bpm'
    df.rename(columns={'AverageBpm': 'Bpm'}, inplace=True)

    df.to_csv(output_csv, index=False)
    print(df)
    return df

def generate_tempo_metadata(directory='sample_audio/loops', output_csv='tempo_metadata.csv'):
    data = []
    for file in os.listdir(directory):
        if file.endswith('.mp3') or file.endswith('.wav'):
            file_path = os.path.join(directory, file)
            y, sr = librosa.load(file_path)
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            #data.append({'TrackID': len(data)+1, 'FileName': file, 'Bpm': tempo})
            data.append({'TrackID': len(data)+1, 'Name': file, 'Bpm': tempo[0]})
    df = pd.DataFrame(data)
    df.to_csv(output_csv, index=False)
    print(f'Tempo metadata saved to {output_csv}')

def generate_track_metadata(directory='sample_audio/loops', output_csv='track_metadata.csv'):
    data = []
    for file in os.listdir(directory):
        if file.endswith('.mp3') or file.endswith('.wav'):
            file_path = os.path.join(directory, file)
            track_id = len(data) + 1
            data.append({
                'TrackID': track_id,
                'Name': os.path.splitext(file)[0],
                'Location': 'file://' + os.path.abspath(file_path)
            })
    df = pd.DataFrame(data)
    df.to_csv(output_csv, index=False)
    print(f'Track metadata saved to {output_csv}')

class SpotifyHandler:
    def __init__(self, client_id, client_secret):
        self.client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        self.sp = spotipy.Spotify(client_credentials_manager=self.client_credentials_manager)
        self.artist_catalogue = {
                    'Angeles Azules': '0ZCO8oVkMj897cKgFH7fRW',
                    'Los Mirlos':'1ga48mxYYI9RuUrWLa3voh',
                    'Antonio Rios':'7s652lD4v77szrPEfgMTBi'
        }

    def save_artist_track_data(self, artist):
        artist_uri = self.artist_catalogue[artist]
        artist_folder = Path('track_data') / artist
        artist_folder.mkdir(parents=True, exist_ok=True)

        results = self.sp.artist_albums(artist_uri, album_type='album')
        albums = results['items']
        while results['next']:
            results = self.sp.next(results)
            albums.extend(results['items'])

        results_singles = self.sp.artist_albums(artist_uri, album_type='single')
        singles = results_singles['items']
        while results_singles['next']:
            results_singles = self.sp.next(results_singles)
            singles.extend(results_singles['items'])

        all_releases = albums + singles

        for release in all_releases:
            album_id = release['id']
            album_name = release['name']
            album_folder = artist_folder / album_name
            album_folder.mkdir(parents=True, exist_ok=True)

            tracks = self.sp.album_tracks(album_id)
            track_data = []
            for track in tracks['items']:
                track_info = {
                    'track_name': track['name'],
                    'track_id': track['id'],
                    'track_uri': track['uri']
                }
                track_data.append(track_info)

            with open(album_folder / 'track_data.json', 'w') as f:
                json.dump(track_data, f, indent=4)

    def save_artist_sample_audio(self, artist, output_folder, duration=30):
        artist_uri = self.artist_catalogue[artist]
        artist_folder = Path(output_folder) / artist
        artist_folder.mkdir(parents=True, exist_ok=True)

        results = self.sp.artist_top_tracks(artist_uri)
        top_track = results['tracks'][0]

        track_id = top_track['id']
        track_name = top_track['name']
        track_preview_url = top_track['preview_url']

        if track_preview_url:
            audio_data = requests.get(track_preview_url).content
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")

            sample_segment = audio_segment[:duration * 1000]
            output_file = artist_folder / f"{track_name}_sample.mp3"
            sample_segment.export(output_file, format="mp3")
            print(f'Sample audio saved to {output_file}')
        else:
            print(f'No preview available for track: {track_name}')


class AudioProcessor:
    def __init__(self, base_path, track_df, tempo_df):
        self.base_path = base_path
        self.track_df = track_df.dropna(subset=['Location'])  # Drop rows with NA values in 'Location'
        self.track_df = self.track_df[self.track_df['Location'].notna()]  # Ensure no NA values in 'Location'
        self.track_df = self.track_df[self.track_df['Location'].str.contains(base_path, na=False)]  # Filter rows where 'Location' contains base_path
        self.tempo_df = tempo_df

        #len(track_df[base_path in track_df['Location']])
        self.filtered_track_df = self.track_df

    @staticmethod
    def calculate_duration(beats, bpm):
        return (60 / bpm) * beats

    def extract_segment(self, track_name, output_path, adjustment=0.0, 
        looped=False, include_stems=True, stems_location='sample_audio/stems', lower_bpm= 120, upper_bpm=124):
        
        print(self.filtered_track_df['Name'])
        track_info = self.filtered_track_df[self.filtered_track_df['Name'] == track_name]
        print(track_info)
        if track_info.empty:
            raise ValueError(f'Track with name {track_name} not found or not in the specified folder.')

        track_id = track_info.iloc[0]['TrackID']
        track_location = unquote(track_info.iloc[0]['Location'].replace('file://localhost', ''))
        tempo_info = self.tempo_df[self.tempo_df['TrackID'] == int(track_id)]
        print(tempo_info)

        bpm_in_range = (tempo_info.iloc[0]['Bpm'] >= lower_bpm ) and (tempo_info.iloc[0]['Bpm'] <= upper_bpm )

        print(tempo_info.iloc[0]['Inizio'])
        if tempo_info.iloc[0]['Inizio'] < -adjustment:
            beat_interval = 60 / tempo_info.iloc[0]['Bpm']
            inicio = tempo_info.iloc[0]['Inizio'] +beat_interval
            print(inicio)
        else:
            inicio = tempo_info.iloc[0]['Inizio']

        if len(tempo_info) != 1  or not bpm_in_range:
            raise ValueError('Not enough tempo points to extract the segment.')

        start_time = inicio + adjustment
        bpm = tempo_info.iloc[0]['Bpm']

        duration_16_beats = self.calculate_duration(16, bpm)
        duration_32_beats = self.calculate_duration(32, bpm)
        duration_48_beats = self.calculate_duration(48, bpm)

        duration = self.calculate_duration(48, bpm)
        end_time = start_time + duration

        start_time_ms = start_time * 1000
        end_time_ms = end_time * 1000

        end_time_16_ms = (start_time + duration_16_beats) * 1000
        end_time_32_ms = (start_time + duration_32_beats) * 1000
        end_time_48_ms = (start_time + duration_48_beats) * 1000

        audio = AudioSegment.from_file(track_location)
        segment = audio[start_time_ms:end_time_ms]

        segment_0_16 = audio[start_time_ms:end_time_16_ms]
        segment_32_48 = audio[end_time_32_ms:end_time_48_ms]
        
        if looped:
            # Calculate durations
            duration_16_beats = int(self.calculate_duration(16, bpm) * 1000)
            duration_32_beats = int(self.calculate_duration(32, bpm) * 1000)
            
            # Extract segments
            segment_0_16 = audio[start_time_ms:(start_time_ms + duration_16_beats)]
            segment_16_32 = audio[(start_time_ms + duration_16_beats):(start_time_ms + duration_32_beats)]
            segment_32_48 = audio[(start_time_ms + duration_32_beats):end_time_48_ms]

            # Crossfade between segment_0_16 and segment_32_48
            fade_in = segment_0_16.fade(from_gain=-60, to_gain=0, start=0, duration=duration_16_beats)
            fade_out = segment_32_48.fade(from_gain=0, to_gain=-60, start=0, duration=duration_16_beats)
            transition = fade_out.overlay(fade_in, position=0)
            
            fade_in_file = os.path.join(output_path, f'{track_name}_fade_in.mp3')
            fade_out_file = os.path.join(output_path, f'{track_name}_fade_out.mp3')
            fade_in.export(fade_in_file, format="mp3")
            fade_out.export(fade_out_file, format="mp3")
            # Create the looped segment
            audio_loop = transition + segment_16_32
            
            # Export the looped segment
            output_file = os.path.join(output_path, f'{track_name}_looped_segment.wav')
            audio_loop.export(output_file, format="wav")
            print(f'Looped segment saved to {output_file}')
        else:
            segment = audio[start_time_ms:end_time_48_ms]
            output_file = os.path.join(output_path, f'{track_name}_segment.wav')
            segment.export(output_file, format="wav")
            print(f'Segment saved to {output_file}')

        if include_stems:
            # Calculate durations
            #duration_16_beats = int(self.calculate_duration(16, bpm) * 1000)
            #duration_32_beats = int(self.calculate_duration(32, bpm) * 1000)
            stems = ['bass','drums','other','vocals']

            for stem in stems:
                track_location = stems_location + "/" + track_name +  "/" + stem + '.wav'
                if os.path.isfile(track_location):
                    audio = AudioSegment.from_file(track_location)
                    segment = audio[start_time_ms:end_time_ms]

                    segment_0_16 = audio[start_time_ms:end_time_16_ms]
                    segment_32_48 = audio[end_time_32_ms:end_time_48_ms]

                    # Extract segments
                    segment_0_16 = audio[start_time_ms:(start_time_ms + duration_16_beats)]
                    segment_16_32 = audio[(start_time_ms + duration_16_beats):(start_time_ms + duration_32_beats)]
                    segment_32_48 = audio[(start_time_ms + duration_32_beats):end_time_48_ms]

                    # Crossfade between segment_0_16 and segment_32_48
                    fade_in = segment_0_16.fade(from_gain=-60, to_gain=0, start=0, duration=duration_16_beats)
                    fade_out = segment_32_48.fade(from_gain=0, to_gain=-60, start=0, duration=duration_16_beats)
                    transition = fade_out.overlay(fade_in, position=0)
                    
                    audio_loop = transition + segment_16_32
                    
                    # Export the looped segment
                    output_file = os.path.join(output_path, f'{track_name}_{stem}_looped_segment.wav')
                    audio_loop.export(output_file, format="wav")
                else:
                    print(f"WARNING: file %s doesn't exists",track_location)
            print(f'Looped segment saved to {output_file}')


        #output_file = os.path.join(output_path, f'{track_name}_segment.mp3')
        audio_loop.export(output_file, format="mp3")
        print(f'Segment saved to {output_file}')

    @staticmethod
    def parse_rekordbox_xml(xml_path):
        tree = ET.parse(xml_path)
        root = tree.getroot()

        track_data = []
        for track in root.findall('.//TRACK'):
            track_info = {
                'TrackID': track.get('TrackID'),
                'Name': track.get('Name'),
                'Location': track.get('Location')
            }
            track_data.append(track_info)

        return pd.DataFrame(track_data)

    @staticmethod
    def read_csv(csv_path):
        return pd.read_csv(csv_path)

# if __name__ == "__main__":

# Example usage
if __name__ == "__main__":
    client_id = os.getenv('SPOTIPY_CLIENT_ID')
    client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')

    if not client_id or not client_secret:
        raise ValueError("Please set the SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET environment variables.")

    spotify_handler = SpotifyHandler(client_id, client_secret)
    # spotify_handler.save_artist_track_data('Tomas Heredia')  # Example usage
    # spotify_handler.save_artist_sample_audio('Tomas Heredia', 'sample_output')  # Example usage

    
    # Existing functionality
    #generate_drums_spectrograms()
    # Parse XML and read CSV files

    base_path = "sample_audio/"
    xml_path = 'rekordbox/collection_cumbia.xml'
    track_df = AudioProcessor.parse_rekordbox_xml(xml_path)
    #track_df[track_df['Location'].str.startswith(base_path)]
    tempo_csv_path = 'tempo_metadata.csv'
    tempo_df = AudioProcessor.read_csv(tempo_csv_path)

    # Create an AudioProcessor instance
    audio_processor = AudioProcessor(base_path, track_df, tempo_df)
    # Example extraction
    #track_name = 'spotify-track-0tvaWhHlhewQ6ovIwn6wnX'  # Replace with the track name you want to process
    # Find all tracks that meet the criteria
    lower_bpm = 80 # cumbia
    upper_bpm = 100
    # lower_bpm = 120 #electro
    # upper_bpm = 124
    print("WARNING: lower/upper bpm hardcodeados")
    matching_tracks = tempo_df.groupby('TrackID').filter(lambda x: len(x) == 1)
    # print(matching_tracks['Bpm'])
    matching_tracks = matching_tracks[(matching_tracks['Bpm'] >= lower_bpm) & (matching_tracks['Bpm'] <= upper_bpm)]
    matching_tracks = matching_tracks[matching_tracks['Name'].str.startswith('spotify-track-')]
    # Get the file names
    file_names = matching_tracks['Name']
    #track_name = 'spotify-track-7GNBiHP71dMz18dCIksjSB'
    output_path = 'sample_audio/loops'  # Replace with your desired output directory
    adjustment = -0.05  # Adjust this value as needed
    
    # print("filenamsssss",file_names)
    print("Warning: checkear ubicación de stems output")
    print("Spleeter stems output is stems_location (downloaded files for example)")
    for f in file_names:
        print(f)
        audio_processor.extract_segment(f, output_path, adjustment, looped=True, lower_bpm=lower_bpm, upper_bpm=upper_bpm,stems_location='output/')





