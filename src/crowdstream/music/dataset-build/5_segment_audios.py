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
import ast
import csv
from collections import Counter

import csv
import ast
import pandas as pd

class AudioProcessor:

    def __init__(self, track_df_path):
        self.track_df_path = track_df_path
        self.track_df = pd.read_csv(self.track_df_path)
        
        # Ensure 'tempo' column is parsed as a list of tuples
        self.track_df['tempo'] = self.track_df['tempo'].apply(ast.literal_eval)
        
        # Remove duplicates based on 'id', keeping the first occurrence
        self.track_df = self.track_df.drop_duplicates(subset='id', keep='first')
        
        # Convert DataFrame to dictionary with 'id' as the key
        #self.track_dict = self.track_df.set_index('id').T.to_dict()

    def filter_id_list(self, lower_bpm=80, upper_bpm=145, artist_list=['Los Piojos', 'AVICII'], stems=[4, 5], tempo_dim_1=True):
        # Filter rows where 'tempo' has only one tuple
        self.filtered_df = self.track_df[
            (self.track_df['artist'].isin(artist_list)) &
            (self.track_df['stems.wav'].isin(stems)) &
            (self.track_df['tempo'].apply(lambda t: len(t) == 1))
        ]

        # Further filter based on the BPM of the single tempo tuple
        self.filtered_df = self.filtered_df[
            self.filtered_df['tempo'].apply(lambda t: lower_bpm <= t[0][1] <= upper_bpm)
        ]

        # Remove duplicates based on 'id' and keep the first occurrence
        self.filtered_df = self.filtered_df.drop_duplicates(subset='id', keep='first')

        self.filtered_track_dict = self.filtered_df.set_index('id').T.to_dict()

        # Return list of filtered ids
        return self.filtered_df['id'].tolist()

    def stems_occurrence_table(self):
        stems_counts = Counter(row['stems.wav'] for row in self.track_dict.values())
        return pd.DataFrame(list(stems_counts.items()), columns=['stems.wav', 'occurrences'])

    @staticmethod
    def calculate_duration(beats, bpm):
        return (60 / bpm) * beats

    def get_loop_from_stems(self, track_name, output_path, adjustment=0.0, 
                            looped=True, stems_location='sample_audio/stems'):
        track_info = self.filtered_track_dict[track_name]
        metadata_list = []

        # Get only the first tempo tuple
        inicio_, bpm, batitto, bar = track_info['tempo'][0]
        if inicio_ < -adjustment:
            beat_interval = 60 / bpm
            inicio = inicio_ + beat_interval
        else:
            inicio = inicio_      

        start_time = inicio + adjustment

        # Calculate durations for 16, 32, and 48 beats
        duration_16_beats = self.calculate_duration(16, bpm)
        duration_32_beats = self.calculate_duration(32, bpm)
        duration_48_beats = self.calculate_duration(48, bpm)

        end_time = start_time + duration_48_beats

        if end_time * 1000 > track_info['duration']:
            raise ValueError('Not enough tempo points to extract the segment.')

        start_time_ms = start_time * 1000
        end_time_ms = end_time * 1000
        end_time_16_ms = (start_time + duration_16_beats) * 1000
        end_time_32_ms = (start_time + duration_32_beats) * 1000

        if track_info['stems.wav'] == 4:
            stems = ['bass', 'drums', 'other', 'vocals']
        elif track_info['stems.wav'] == 5:
            stems = ['bass', 'drums', 'other', 'piano', 'vocals']
        else:
            stems = []

        for stem in stems:
            track_location = os.path.join(stems_location, 'spotify-track-' + track_name, f"{stem}.wav")
            if os.path.isfile(track_location):
                audio = AudioSegment.from_file(track_location)

                if looped:
                    # Extract segments
                    segment_0_16 = audio[start_time_ms:end_time_16_ms]
                    segment_16_32 = audio[end_time_16_ms:end_time_32_ms]
                    segment_32_48 = audio[end_time_32_ms:end_time_ms]

                    # Crossfade between segment_0_16 and segment_32_48
                    fade_in = segment_0_16.fade(from_gain=-60, to_gain=0, start=0, duration=int(duration_16_beats * 1000))
                    fade_out = segment_32_48.fade(from_gain=0, to_gain=-60, start=0, duration=int(duration_16_beats * 1000))
                    transition = fade_out.overlay(fade_in, position=0)

                    # Create the looped segment
                    audio_loop = transition + segment_16_32

                    # Export the looped segment
                    output_file = os.path.join(output_path, f'{track_name}_{stem}_looped_segment.wav')
                    audio_loop.export(output_file, format="wav")
                else:
                    segment = audio[start_time_ms:end_time_ms]
                    output_file = os.path.join(output_path, f'{track_name}_{stem}_segment.wav')
                    segment.export(output_file, format="wav")

                # Append metadata for each generated file
                metadata = {
                    'filename': output_file,
                    'track_id': track_name,
                    'name': track_info['name'],
                    'artist': track_info['artist'],
                    'stem': stem,
                    'bpm': bpm,
                    'key': track_info['Tonality'],
                    'duration': duration_48_beats,
                    'start_time': start_time_ms,
                    'end_time': end_time_ms
                }
                metadata_list.append(metadata)
            else:
                print(f"WARNING: file {track_location} doesn't exist.")

        # Save metadata to CSV
        metadata_df = pd.DataFrame(metadata_list)
        file_path = os.path.join(output_path, 'generated_files_metadata.csv')
        metadata_df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)

    def extract_segment(self, track_name, output_path, adjustment=0.0, 
        looped=True, include_stems=True, audio_location ='',stems_location='sample_audio/stems'):      
        
        track_info = self.track_dict[track_name]

        #get only the first element as it may be more than one        
        inicio_, bpm, batitto, bar = track_info['tempo']


        if inicio_ < -adjustment:
            beat_interval = 60 / bpm
            inicio = inicio_ + beat_interval
        else:
            inicio = inicio_


        start_time = inicio + adjustment

        duration_16_beats = self.calculate_duration(16, bpm)
        duration_32_beats = self.calculate_duration(32, bpm)
        duration_48_beats = self.calculate_duration(48, bpm)

        duration = self.calculate_duration(48, bpm)

        end_time = start_time + duration

        if end_time*1000 > track_info['duration']:
            raise ValueError('Not enough tempo points to extract the segment.')

        start_time_ms = start_time * 1000
        end_time_ms = end_time * 1000

        end_time_16_ms = (start_time + duration_16_beats) * 1000
        end_time_32_ms = (start_time + duration_32_beats) * 1000
        end_time_48_ms = (start_time + duration_48_beats) * 1000

        track_location = os.path.join(output_path, f'{track_name}_{stem}_looped_segment.wav')

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
            
            #fade_in_file = os.path.join(output_path, f'{track_name}_fade_in.mp3')
            #fade_out_file = os.path.join(output_path, f'{track_name}_fade_out.mp3')
            #fade_in.export(fade_in_file, format="mp3")
            #fade_out.export(fade_out_file, format="mp3")
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
                    output_file = os.path.join(output_path, f'{track_name}_{stem}_loop.wav')
                    audio_loop.export(output_file, format="wav")
                else:
                    print(f"WARNING: file %s doesn't exists",track_location)
            print(f'Looped segment saved to {output_file}')

    @staticmethod
    def read_csv(csv_path):
        return pd.read_csv(csv_path)

# if __name__ == "__main__":

# Example usage
if __name__ == "__main__":

    base_path = 'track_data_summary.csv'

    # Create an AudioProcessor instance
    audio_processor = AudioProcessor(base_path)
    # Example extraction
    #track_name = 'spotify-track-0tvaWhHlhewQ6ovIwn6wnX'  # Replace with the track name you want to process
    # Find all tracks that meet the criteria
    id_list = audio_processor.filter_id_list()
    #print(audio_processor.stems_occurrence_table())
    print( '2TkOLbkuGh8bFdBnFzPIP1' in id_list)

    print("WARNING: lower/upper bpm hardcodeados")

    #track_name = 'spotify-track-7GNBiHP71dMz18dCIksjSB'
    output_path = 'sample_audio/loops_piojos_avicii'  # Replace with your desired output directory
    adjustment = -0.05  # Adjust this value as needed

    for f in id_list:
        #print(f)
        audio_processor.get_loop_from_stems(f, output_path, adjustment, stems_location='/Users/xaviergonzalez/Library/Mobile Documents/com~apple~CloudDocs/Desktop/9216 TIMMD/music/sample_audio/stems')

    