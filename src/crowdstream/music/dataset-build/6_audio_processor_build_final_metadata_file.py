import os
import pandas as pd
import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
import random

keys_affinity = {
    "Abm": {
        "affinity_1": ["Abm", "Ebm"],
        "affinity_2": ["Dbm", "B", "Bbm"]
    },
    "B": {
        "affinity_1": ["B", "F#"],
        "affinity_2": ["E", "Abm", "Db"]
    },
    "Ebm": {
        "affinity_1": ["Ebm", "Bbm"],
        "affinity_2": ["Abm", "F#", "Fm"]
    },
    "F#": {
        "affinity_1": ["F#", "Db"],
        "affinity_2": ["B", "Ebm", "Ab"]
    },
    "Bbm": {
        "affinity_1": ["Bbm", "Fm"],
        "affinity_2": ["Ebm", "Db", "Cm"]
    },
    "Db": {
        "affinity_1": ["Db", "Ab"],
        "affinity_2": ["F#", "Bbm", "Eb"]
    },
    "Fm": {
        "affinity_1": ["Fm", "Cm"],
        "affinity_2": ["Bbm", "Ab", "Gm"]
    },
    "Ab": {
        "affinity_1": ["Ab", "Eb"],
        "affinity_2": ["Db", "Fm", "Bb"]
    },
    "Cm": {
        "affinity_1": ["Cm", "Gm"],
        "affinity_2": ["Fm", "Eb", "Dm"]
    },
    "Eb": {
        "affinity_1": ["Eb", "Bb"],
        "affinity_2": ["Ab", "Cm", "F"]
    },
    "Gm": {
        "affinity_1": ["Gm", "Dm"],
        "affinity_2": ["Cm", "Bb", "Am"]
    },
    "Bb": {
        "affinity_1": ["Bb", "F"],
        "affinity_2": ["Eb", "Gm", "C"]
    },
    "Dm": {
        "affinity_1": ["Dm", "Am"],
        "affinity_2": ["Gm", "F", "Em"]
    },
    "F": {
        "affinity_1": ["F", "C"],
        "affinity_2": ["Bb", "Dm", "G"]
    },
    "Am": {
        "affinity_1": ["Am", "Em"],
        "affinity_2": ["Dm", "C", "Bm"]
    },
    "C": {
        "affinity_1": ["C", "G"],
        "affinity_2": ["F", "Am", "D"]
    },
    "Em": {
        "affinity_1": ["Em", "Bm"],
        "affinity_2": ["Am", "G", "F#m"]
    },
    "G": {
        "affinity_1": ["G", "D"],
        "affinity_2": ["C", "Em", "A"]
    },
    "Bm": {
        "affinity_1": ["Bm", "F#m"],
        "affinity_2": ["Em", "D", "C#m"]
    },
    "D": {
        "affinity_1": ["D", "A"],
        "affinity_2": ["G", "Bm", "E"]
    },
    "F#m": {
        "affinity_1": ["F#m", "C#m"],
        "affinity_2": ["Bm", "A", "G#m"]
    },
    "A": {
        "affinity_1": ["A", "E"],
        "affinity_2": ["D", "F#m", "B"]
    },
    "Dbm": {
        "affinity_1": ["Dbm", "Abm"],
        "affinity_2": ["F#m", "E", "Ebm"]
    },
    "E": {
        "affinity_1": ["E", "B"],
        "affinity_2": ["A", "Dbm", "F#"]
    }
}

class AudioAnalyzer:
    def __init__(self, csv_path, spectrogram_dir, numpy_dir):
        self.loop_df = pd.read_csv(csv_path)
        self.spectrogram_dir = spectrogram_dir
        self.numpy_dir = numpy_dir
        os.makedirs(self.spectrogram_dir, exist_ok=True)
        os.makedirs(self.numpy_dir, exist_ok=True)

        # Create self.track_df with distinct artist, track_id, name, bpm, and key
        self.track_df = self.loop_df[['artist', 'track_id', 'name', 'bpm', 'key']].drop_duplicates()

    def generate_spectrograms(self):
        for index, row in self.loop_df.iterrows():
            audio_file = row['filename']
            if os.path.exists(audio_file):
                y, sr = librosa.load(audio_file, sr=None)
                S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)
                S_dB = librosa.power_to_db(S, ref=np.max)

                # Save the spectrogram as a NumPy array
                spectrogram_filename = os.path.splitext(os.path.basename(audio_file))[0]
                numpy_path = os.path.join(self.numpy_dir, f"{spectrogram_filename}.npy")
                np.save(numpy_path, S_dB)

                # Plot and save the spectrogram image without axes, frames, or titles
                plt.figure(figsize=(10, 4))
                plt.axis('off')
                librosa.display.specshow(S_dB, sr=sr, x_axis=None, y_axis=None)
                plt.subplots_adjust(left=0, right=1, top=1, bottom=0, wspace=0, hspace=0)
                spectrogram_image_path = os.path.join(self.spectrogram_dir, f"{spectrogram_filename}.png")
                plt.savefig(spectrogram_image_path, bbox_inches='tight', pad_inches=0)
                plt.close()
            else:
                print(f"File {audio_file} does not exist.")

    def generate_playlist_2_artist(self, starting_bpm=120):
        # Filter tracks with BPM less than starting_bpm
        filtered_df = self.track_df[self.track_df['bpm'] < starting_bpm]

        if not filtered_df.empty:
            # Randomly select one track
            first_track = filtered_df.sample(n=1, random_state=random.randint(0, 10000)).iloc[0]

            # Save the BPM, key, and artist of the selected track
            current_bpm = first_track['bpm']
            current_key = first_track['key']
            current_artist = first_track['artist']

            # Initialize playlist and used_artists
            self.playlist = [first_track['track_id']]
            used_artists = {current_artist}

            # Print the details of the selected track
            print(f"Selected Track ID: {first_track['track_id']}")
            print(f"Artist: {current_artist}")
            print(f"BPM: {current_bpm}")
            print(f"Key: {current_key}")
            print(f"Name: {first_track['name']}")

            # Find and add subsequent tracks
            while True:
                next_track = self.find_next_track(current_bpm, current_key, used_artists, self.playlist, affinity_level=1)
                if next_track is None:
                    print('next')
                    break
                self.playlist.append(next_track['track_id'])
                used_artists = {next_track['artist']}
                current_bpm = next_track['bpm']
                current_key = next_track['key']
                print(f"Added Track ID: {next_track['track_id']}")
                print(f"Artist: {next_track['artist']}")
                print(f"BPM: {next_track['bpm']}")
                print(f"Key: {next_track['key']}")
                print(f"Name: {next_track['name']}")

            # Save the playlist to a CSV file
            self.save_playlist_to_csv(self.playlist)
            #playlist_df = self.loop_df[self.loop_df['track_id'].isin(playlist)]
            #playlist_df = playlist_df.sort_values(by=['track_id', 'stem'])
            #playlist_df.to_csv('sonic_pi_list.csv', index=False)
        else:
            print("No tracks found with BPM less than the specified threshold.")
        
    def find_next_track(self, current_bpm, current_key, used_artists, playlist, affinity_level=1):
        if affinity_level == 1:
            key_affinity_list = keys_affinity[current_key]['affinity_1']
            bpm_range = (current_bpm - 2, current_bpm + 3)
        else:
            key_affinity_list = keys_affinity[current_key]['affinity_2']
            bpm_range = (current_bpm - 2, current_bpm + 5)

        candidates = self.track_df[
            (self.track_df['bpm'] > bpm_range[0]) &
            (self.track_df['bpm'] < bpm_range[1]) &
            (self.track_df['key'].isin(key_affinity_list)) &
            (~self.track_df['artist'].isin(used_artists)) &
            (~self.track_df['track_id'].isin(playlist))
        ]

        if not candidates.empty:
            return candidates.sample(n=1, random_state=random.randint(0, 10000)).iloc[0]
        elif affinity_level == 1:
            return self.find_next_track(current_bpm, current_key, used_artists, playlist, affinity_level=2)
        else:
            return None

    def save_playlist_to_csv(self, playlist):
        # Initialize an empty DataFrame to store the ordered playlist
        print(playlist)
        ordered_playlist_df = pd.DataFrame()

        # Iterate over each track_id in the playlist
        for track_id in playlist:
            # Filter loop_df to include only rows with the current track_id
            track_df = self.loop_df[self.loop_df['track_id'] == track_id]
            # Append the filtered DataFrame to the ordered_playlist_df
            ordered_playlist_df = pd.concat([ordered_playlist_df, track_df], ignore_index=True)

        # Sort by 'stem' within each track_id group
        #ordered_playlist_df = ordered_playlist_df.sort_values(by=['track_id', 'stem'])

        # Save to CSV
        ordered_playlist_df.to_csv('sonic_pi_list.csv', index=False)


if __name__ == "__main__":
    csv_path = 'sample_audio/loops_piojos_avicii/generated_files_metadata.csv'
    spectrogram_dir = 'sample_audio/loops_piojos_avicii/spectrograms/'
    numpy_dir = 'sample_audio/loops_piojos_avicii/numpy/'

    audio_analyzer = AudioAnalyzer(csv_path, spectrogram_dir, numpy_dir)
    audio_analyzer.generate_playlist_2_artist()

        # Filter loop_df to i