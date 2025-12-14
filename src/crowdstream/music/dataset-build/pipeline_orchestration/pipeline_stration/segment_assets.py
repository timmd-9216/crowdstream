
import os
import pandas as pd
import ast
from pydub import AudioSegment
from dagster import asset
from collections import Counter
from pathlib import Path

from .metadata_assets import track_data_summary

# Define paths relative to this file
SCRIPT_DIR = Path(__file__).parent
DATASET_BUILD_DIR = SCRIPT_DIR.parent
SAMPLE_AUDIO_DIR = DATASET_BUILD_DIR / 'sample_audio'

class AudioProcessor:
    def __init__(self, track_df):
        self.track_df = track_df
        self.track_df['tempo'] = self.track_df['tempo'].apply(ast.literal_eval)
        self.track_df = self.track_df.drop_duplicates(subset='id', keep='first')

    def filter_id_list(self, lower_bpm=80, upper_bpm=145, artist_list=['Los Piojos', 'AVICII'], stems=[4, 5], tempo_dim_1=True):
        self.filtered_df = self.track_df[
            (self.track_df['artist'].isin(artist_list)) &
            (self.track_df['stems.wav'].isin(stems)) &
            (self.track_df['tempo'].apply(lambda t: len(t) == 1))
        ]
        self.filtered_df = self.filtered_df[
            self.filtered_df['tempo'].apply(lambda t: lower_bpm <= t[0][1] <= upper_bpm)
        ]
        self.filtered_df = self.filtered_df.drop_duplicates(subset='id', keep='first')
        self.filtered_track_dict = self.filtered_df.set_index('id').T.to_dict()
        return self.filtered_df['id'].tolist()

    @staticmethod
    def calculate_duration(beats, bpm):
        return (60 / bpm) * beats

    def get_loop_from_stems(self, track_name, output_path, adjustment=0.0, 
                            looped=True, stems_location=SAMPLE_AUDIO_DIR / 'stems'):
        track_info = self.filtered_track_dict[track_name]
        metadata_list = []
        inicio_, bpm, batitto, bar = track_info['tempo'][0]
        if inicio_ < -adjustment:
            beat_interval = 60 / bpm
            inicio = inicio_ + beat_interval
        else:
            inicio = inicio_
        start_time = inicio + adjustment
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
                    segment_0_16 = audio[start_time_ms:end_time_16_ms]
                    segment_16_32 = audio[end_time_16_ms:end_time_32_ms]
                    segment_32_48 = audio[end_time_32_ms:end_time_ms]
                    fade_in = segment_0_16.fade(from_gain=-60, to_gain=0, start=0, duration=int(duration_16_beats * 1000))
                    fade_out = segment_32_48.fade(from_gain=0, to_gain=-60, start=0, duration=int(duration_16_beats * 1000))
                    transition = fade_out.overlay(fade_in, position=0)
                    audio_loop = transition + segment_16_32
                    output_file = os.path.join(output_path, f'{track_name}_{stem}_looped_segment.wav')
                    audio_loop.export(output_file, format="wav")
                else:
                    segment = audio[start_time_ms:end_time_ms]
                    output_file = os.path.join(output_path, f'{track_name}_{stem}_segment.wav')
                    segment.export(output_file, format="wav")
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
        metadata_df = pd.DataFrame(metadata_list)
        file_path = os.path.join(output_path, 'generated_files_metadata.csv')
        metadata_df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)

@asset(deps=[track_data_summary])
def segmented_audio(track_data_summary):
    audio_processor = AudioProcessor(track_data_summary)
    id_list = audio_processor.filter_id_list()
    output_path = SAMPLE_AUDIO_DIR / 'loops'
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    adjustment = -0.05
    for f in id_list:
        audio_processor.get_loop_from_stems(f, output_path, adjustment)
