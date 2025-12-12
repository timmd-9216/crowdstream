#!/usr/bin/env python3
"""
Python Audio Server - Pure Python replacement for SuperCollider
Implements the same OSC API as supercollider_audio_server_minimal.scd
Uses PyAudio for real-time audio playback with crossfading and mixing
"""

import numpy as np
import soundfile as sf
import pyaudio
import threading
import time
from pathlib import Path
from pythonosc import dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from typing import Dict, Optional, Tuple
import argparse

class AudioBuffer:
    """Represents an audio buffer with playback capabilities"""
    
    def __init__(self, file_path: str, buffer_id: int, name: str = ""):
        self.buffer_id = buffer_id
        self.name = name
        self.file_path = file_path
        self.audio_data = None
        self.sample_rate = 44100
        self.channels = 2
        self.frames = 0
        self.loaded = False
        
        self.load_audio()
    
    def load_audio(self):
        """Load audio file into memory"""
        try:
            self.audio_data, self.sample_rate = sf.read(self.file_path, dtype=np.float32)
            
            # Ensure stereo
            if len(self.audio_data.shape) == 1:
                self.audio_data = np.column_stack((self.audio_data, self.audio_data))
            elif self.audio_data.shape[1] == 1:
                self.audio_data = np.tile(self.audio_data, (1, 2))
            
            self.frames = len(self.audio_data)
            self.channels = self.audio_data.shape[1]
            self.loaded = True
            
            # Calculate memory usage
            memory_mb = (self.frames * self.channels * 4) / (1024 * 1024)
            print(f"✅ Loaded {self.name} ({memory_mb:.1f} MB)")
            
        except Exception as e:
            print(f"❌ Load failed: {self.name} - {e}")
            self.loaded = False

class StemPlayer:
    """Individual stem player with rate, volume, and position control"""
    
    def __init__(self, buffer: AudioBuffer, rate: float = 1.0, volume: float = 0.8, 
                 start_pos: float = 0.0, loop: bool = True):
        self.buffer = buffer
        self.rate = rate
        self.volume = volume
        self.loop = loop
        self.playing = False
        self.position = int(start_pos * buffer.frames) if buffer.loaded else 0
        self.original_position = self.position
        
    def get_audio_chunk(self, chunk_size: int) -> np.ndarray:
        """Get next audio chunk for playback"""
        if not self.buffer.loaded or not self.playing:
            return np.zeros((chunk_size, 2), dtype=np.float32)
        
        output = np.zeros((chunk_size, 2), dtype=np.float32)
        samples_needed = chunk_size
        output_pos = 0
        
        while samples_needed > 0 and self.playing:
            # Calculate how many samples we can read from current position
            available = self.buffer.frames - self.position
            if available <= 0:
                if self.loop:
                    self.position = 0
                    available = self.buffer.frames
                else:
                    break
            
            # Determine how many samples to read
            to_read = min(samples_needed, available)
            if to_read <= 0:
                break
            
            # Read audio data
            end_pos = self.position + to_read
            audio_chunk = self.buffer.audio_data[self.position:end_pos]
            
            # Apply volume
            audio_chunk = audio_chunk * self.volume
            
            # Copy to output buffer
            output[output_pos:output_pos + to_read] = audio_chunk
            
            # Update positions
            self.position = end_pos
            output_pos += to_read
            samples_needed -= to_read
        
        return output

class PythonAudioServer:
    """Main audio server class - Python replacement for SuperCollider"""
    
    def __init__(self, osc_port: int = 57120, audio_device: Optional[int] = None):
        self.osc_port = osc_port
        self.audio_device = audio_device
        self.sample_rate = 44100
        self.chunk_size = 1024  # Increased from 256 to reduce ALSA issues on RPi
        self.channels = 2

        # Audio state
        self.buffers: Dict[int, AudioBuffer] = {}
        self.active_players: Dict[int, StemPlayer] = {}

        # Mixing parameters
        self.deck_a_volume = 0.8
        self.deck_b_volume = 0.0
        self.master_volume = 0.8

        # PyAudio setup
        self.pa = pyaudio.PyAudio()
        self.stream = None
        self.running = False

        # OSC server
        self.osc_server = None

        print("🎛️💾 PYTHON AUDIO SERVER INITIALIZING 💾🎛️")
        self.list_audio_devices()
        self.setup_audio()
        self.setup_osc()
    
    def list_audio_devices(self):
        """List available audio output devices"""
        print("\n📡 Available Audio Devices:")
        for i in range(self.pa.get_device_count()):
            info = self.pa.get_device_info_by_index(i)
            if info['maxOutputChannels'] > 0:
                host_api = self.pa.get_host_api_info_by_index(info['hostApi'])
                print(f"  [{i}] {info['name']} ({host_api['name']}) - {info['maxOutputChannels']} channels")
        print()

    def setup_audio(self):
        """Initialize PyAudio stream"""
        try:
            # Find best device: prefer 'pulse' or 'default' by name (better for Raspberry Pi)
            selected_device = None
            default_device = None
            if self.audio_device is None:
                print("🔍 Searching for best audio device...")
                for i in range(self.pa.get_device_count()):
                    try:
                        info = self.pa.get_device_info_by_index(i)
                        device_name = info['name'].lower()
                        # Prefer 'pulse' first
                        if 'pulse' in device_name and info['maxOutputChannels'] > 0:
                            selected_device = i
                            print(f"🔍 Found pulse device: [{i}] {info['name']}")
                            break
                        # Store 'default' as fallback
                        elif device_name == 'default' and info['maxOutputChannels'] > 0:
                            default_device = i
                            print(f"🔍 Found default device: [{i}] {info['name']}")
                    except Exception as e:
                        print(f"⚠️  Error checking device {i}: {e}")

                # Use default if pulse not found
                if selected_device is None and default_device is not None:
                    selected_device = default_device
                    print(f"🔍 Using default device as fallback")

            open_params = {
                'format': pyaudio.paFloat32,
                'channels': self.channels,
                'rate': self.sample_rate,
                'output': True,
                'frames_per_buffer': self.chunk_size
            }

            # Use specific device if provided, otherwise use selected device
            if self.audio_device is not None:
                open_params['output_device_index'] = self.audio_device
                device_info = self.pa.get_device_info_by_index(self.audio_device)
                print(f"🎯 Using specified device: [{self.audio_device}] {device_info['name']}")
            elif selected_device is not None:
                open_params['output_device_index'] = selected_device
                device_info = self.pa.get_device_info_by_index(selected_device)
                print(f"🎯 Using auto-selected device: [{selected_device}] {device_info['name']}")
            else:
                print(f"🎯 Using system default device")

            self.stream = self.pa.open(**open_params)

            print(f"🔊 Audio stream opened: {self.sample_rate}Hz, {self.chunk_size} samples")

            # DON'T start audio_loop yet - will start after test tone
            # self.running = True
            # self.audio_thread = threading.Thread(target=self.audio_loop)
            # self.audio_thread.daemon = True
            # self.audio_thread.start()
            
        except Exception as e:
            print(f"❌ Failed to open audio stream: {e}")
    
    def audio_loop(self):
        """Audio processing loop (instead of callback)"""
        while self.running:
            try:
                # Mix all active players
                deck_a_mix = np.zeros((self.chunk_size, 2), dtype=np.float32)
                deck_b_mix = np.zeros((self.chunk_size, 2), dtype=np.float32)
                
                for buffer_id, player in list(self.active_players.items()):
                    if player.playing:
                        try:
                            chunk = player.get_audio_chunk(self.chunk_size)
                            
                            # Route to appropriate deck
                            if buffer_id < 1100:
                                deck_a_mix += chunk
                            else:
                                deck_b_mix += chunk
                                
                        except Exception as e:
                            print(f"⚠️  Error in player {buffer_id}: {e}")
                            player.playing = False
                
                # Apply deck volumes and mix
                final_mix = (deck_a_mix * self.deck_a_volume +
                            deck_b_mix * self.deck_b_volume) * self.master_volume

                # Soft limiting to prevent clipping
                final_mix = np.tanh(final_mix * 0.9) * 0.9

                # Debug: log if we have actual audio
                max_amplitude = np.max(np.abs(final_mix))
                if max_amplitude > 0.01 and hasattr(self, '_last_log_time'):
                    if time.time() - self._last_log_time > 2.0:  # Log every 2 seconds
                        print(f"🔊 Audio level: {max_amplitude:.3f} | Players: {len(self.active_players)} | Playing: {sum(1 for p in self.active_players.values() if p.playing)}")
                        self._last_log_time = time.time()
                elif not hasattr(self, '_last_log_time'):
                    self._last_log_time = time.time()

                # Write to audio stream (blocking call)
                if self.stream and self.stream.is_active():
                    try:
                        self.stream.write(final_mix.astype(np.float32).tobytes(),
                                        exception_on_underflow=False)
                    except Exception as e:
                        # Silently continue on write errors (common on RPi)
                        pass

                # No sleep - write() is blocking and handles timing
                
            except Exception as e:
                print(f"❌ Audio loop error: {e}")
                time.sleep(0.1)
    
    def setup_osc(self):
        """Setup OSC server with same API as SuperCollider"""
        disp = dispatcher.Dispatcher()
        
        # Load buffer
        disp.map("/load_buffer", self.osc_load_buffer)
        
        # Play stem
        disp.map("/play_stem", self.osc_play_stem)
        
        # Stop stem
        disp.map("/stop_stem", self.osc_stop_stem)
        
        # Volume control
        disp.map("/stem_volume", self.osc_stem_volume)
        
        # Crossfade
        disp.map("/crossfade_levels", self.osc_crossfade_levels)
        
        # Status
        disp.map("/get_status", self.osc_get_status)
        
        # Test tone
        disp.map("/test_tone", self.osc_test_tone)
        
        # Cleanup
        disp.map("/mixer_cleanup", self.osc_mixer_cleanup)
        
        # Start OSC server
        self.osc_server = ThreadingOSCUDPServer(
            ("localhost", self.osc_port), disp)
        
        print(f"🔌 OSC server listening on port {self.osc_port}")
    
    def osc_load_buffer(self, address, *args):
        """Load audio buffer - /load_buffer [buffer_id, file_path, stem_name]"""
        try:
            buffer_id = int(args[0])
            file_path = str(args[1])
            stem_name = str(args[2])
            
            # Free existing buffer if it exists
            if buffer_id in self.buffers:
                print(f"Freed buffer {buffer_id}")
                del self.buffers[buffer_id]
            
            # Stop any active player for this buffer
            if buffer_id in self.active_players:
                self.active_players[buffer_id].playing = False
                del self.active_players[buffer_id]
            
            # Load new buffer
            self.buffers[buffer_id] = AudioBuffer(file_path, buffer_id, stem_name)
            
        except Exception as e:
            print(f"❌ Error loading buffer: {e}")
    
    def osc_play_stem(self, address, *args):
        """Play stem - /play_stem [buffer_id, rate, volume, loop, start_pos]"""
        try:
            buffer_id = int(args[0])
            rate = float(args[1])
            volume = float(args[2])
            loop = bool(int(args[3])) if len(args) > 3 else True
            start_pos = float(args[4]) if len(args) > 4 else 0.0
            
            if buffer_id not in self.buffers:
                print(f"❌ Buffer {buffer_id} not loaded")
                return
            
            buffer = self.buffers[buffer_id]
            if not buffer.loaded:
                print(f"❌ Buffer {buffer_id} not ready")
                return
            
            # Stop existing player
            if buffer_id in self.active_players:
                self.active_players[buffer_id].playing = False
            
            # Create new player
            player = StemPlayer(buffer, rate, volume, start_pos, loop)
            player.playing = True
            self.active_players[buffer_id] = player
            
            print(f"▶️  Playing buffer {buffer_id}, rate: {rate:.3f}")
            
        except Exception as e:
            print(f"❌ Error playing stem: {e}")
    
    def osc_stop_stem(self, address, *args):
        """Stop stem playback"""
        try:
            buffer_id = int(args[0])
            if buffer_id in self.active_players:
                self.active_players[buffer_id].playing = False
                del self.active_players[buffer_id]
                print(f"⏹️  Stopped {buffer_id}")
        except Exception as e:
            print(f"❌ Error stopping stem: {e}")
    
    def osc_stem_volume(self, address, *args):
        """Set stem volume"""
        try:
            buffer_id = int(args[0])
            volume = float(args[1])
            if buffer_id in self.active_players:
                self.active_players[buffer_id].volume = volume
        except Exception as e:
            print(f"❌ Error setting volume: {e}")
    
    def osc_crossfade_levels(self, address, *args):
        """Set crossfade levels - /crossfade_levels [deck_a_vol, deck_b_vol]"""
        try:
            self.deck_a_volume = float(args[0])
            self.deck_b_volume = float(args[1])
            print(f"🎚️  A:{self.deck_a_volume:.2f} B:{self.deck_b_volume:.2f}")
        except Exception as e:
            print(f"❌ Error setting crossfade: {e}")
    
    def osc_get_status(self, address, *args):
        """Get server status"""
        try:
            print("=== PYTHON AUDIO SERVER ===")
            print(f"Sample Rate: {self.sample_rate} Hz")
            print(f"Buffers loaded: {len(self.buffers)}")
            print(f"Active players: {len([p for p in self.active_players.values() if p.playing])}")
            print(f"Deck A: {self.deck_a_volume:.2f}, Deck B: {self.deck_b_volume:.2f}")
        except Exception as e:
            print(f"❌ Error getting status: {e}")
    
    def osc_test_tone(self, address, *args):
        """Test tone (simplified - just acknowledge)"""
        freq = args[0] if args else 440
        print(f"🎵 Test tone request: {freq} Hz")
    
    def osc_mixer_cleanup(self, address, *args):
        """Clean up all buffers and players"""
        try:
            # Stop all players
            for player in self.active_players.values():
                player.playing = False
            self.active_players.clear()
            
            # Clear buffers
            self.buffers.clear()
            
            print("🧹 Cleaned")
        except Exception as e:
            print(f"❌ Error cleaning up: {e}")
    
    def play_test_tone(self, duration=1.0, frequency=440.0):
        """Play a test tone to verify audio output"""
        print(f"\n🎵 Playing test tone ({frequency} Hz, {duration}s)...")
        print(f"📊 Stream info:")
        print(f"   - Active: {self.stream.is_active()}")
        print(f"   - Stopped: {self.stream.is_stopped()}")
        print(f"   - Sample rate: {self.sample_rate} Hz")
        print(f"   - Channels: {self.channels}")

        # Generate sine wave
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        samples = np.sin(2 * np.pi * frequency * t) * 0.3  # 30% volume

        # Convert to stereo
        stereo_samples = np.column_stack((samples, samples)).astype(np.float32)

        print(f"📊 Audio data: {stereo_samples.shape}, {stereo_samples.dtype}")
        print(f"📊 Bytes to write: {len(stereo_samples.tobytes())}")

        # Write directly to stream (blocking)
        try:
            bytes_written = self.stream.write(stereo_samples.tobytes())
            print(f"✅ Test tone completed (wrote {len(stereo_samples.tobytes())} bytes)")
        except Exception as e:
            print(f"❌ Test tone failed: {e}")
            import traceback
            traceback.print_exc()

    def start(self):
        """Start the audio server"""
        if self.stream and self.osc_server:
            self.stream.start_stream()

            print("🎛️💾 PYTHON AUDIO SERVER READY 💾🎛️")
            print(f"🔊 Audio: {self.sample_rate}Hz, {self.chunk_size} samples")
            print(f"🔌 OSC: localhost:{self.osc_port}")
            print("💡 Same OSC API as SuperCollider server")
            print()

            # Play test tone BEFORE starting audio loop (like test_audio.py)
            print("⏳ Waiting for audio stream to stabilize...")
            time.sleep(0.5)

            print("\n🎵 Playing test tone (440 Hz, 2s)...")
            # Generate test tone - same as test_audio.py
            duration = 2.0
            frequency = 440.0
            t = np.linspace(0, duration, int(self.sample_rate * duration))
            samples = np.sin(2 * np.pi * frequency * t) * 0.3  # 30% volume
            stereo_samples = np.column_stack((samples, samples)).astype(np.float32)

            try:
                self.stream.write(stereo_samples.tobytes())
                print("✅ Test tone completed - audio is working!")
            except Exception as e:
                print(f"❌ Test tone failed: {e}")

            # TEST: Play a real stem file directly (like test tone)
            print("\n🎵 Testing stem playback (bass from first song)...")
            try:
                import soundfile as sf
                # Find first available bass stem
                stems_dir = Path("stems")
                if stems_dir.exists():
                    for song_dir in sorted(stems_dir.iterdir()):
                        if song_dir.is_dir():
                            bass_file = song_dir / "bass.wav"
                            if bass_file.exists():
                                print(f"📂 Loading: {bass_file}")
                                audio_data, sr = sf.read(str(bass_file), dtype=np.float32)

                                # Ensure stereo
                                if audio_data.ndim == 1:
                                    audio_data = np.column_stack((audio_data, audio_data))

                                # Play first 5 seconds only
                                samples_to_play = min(len(audio_data), sr * 5)
                                audio_chunk = audio_data[:samples_to_play]

                                print(f"▶️  Playing {samples_to_play/sr:.1f}s of bass at 50% volume...")
                                audio_chunk = audio_chunk * 0.5  # 50% volume
                                self.stream.write(audio_chunk.astype(np.float32).tobytes())
                                print("✅ Stem playback test completed!")
                                break
            except Exception as e:
                print(f"⚠️  Stem test failed: {e}")
                import traceback
                traceback.print_exc()

            # Start the audio loop
            print("\n🎵 Starting audio processing loop...")
            self.running = True
            self.audio_thread = threading.Thread(target=self.audio_loop)
            self.audio_thread.daemon = True
            self.audio_thread.start()

            # Wait for loop to stabilize
            time.sleep(0.2)

            # Start OSC server
            server_thread = threading.Thread(target=self.osc_server.serve_forever)
            server_thread.daemon = True
            server_thread.start()

            return server_thread
        else:
            print("❌ Failed to initialize audio server")
            return None
    
    def stop(self):
        """Stop the audio server"""
        self.running = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        if self.osc_server:
            self.osc_server.shutdown()
        
        if self.pa:
            self.pa.terminate()
        
        print("👋 Python Audio Server stopped")

def main():
    parser = argparse.ArgumentParser(description='Python Audio Server - SuperCollider replacement')
    parser.add_argument('--port', type=int, default=57120, help='OSC port (default: 57120)')
    parser.add_argument('--device', type=int, help='Audio device ID (use --list-devices to see options)')
    parser.add_argument('--list-devices', action='store_true', help='List available audio devices and exit')

    args = parser.parse_args()

    # List devices mode
    if args.list_devices:
        pa = pyaudio.PyAudio()
        print("\n📡 Available Audio Output Devices:")
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if info['maxOutputChannels'] > 0:
                host_api = pa.get_host_api_info_by_index(info['hostApi'])
                is_default = " (DEFAULT)" if i == pa.get_default_output_device_info()['index'] else ""
                print(f"  [{i}] {info['name']} ({host_api['name']}) - {info['maxOutputChannels']} channels{is_default}")
        pa.terminate()
        print("\nUse: python audio_server.py --device <ID>\n")
        return

    # Create and start server
    server = PythonAudioServer(osc_port=args.port, audio_device=args.device)
    server_thread = server.start()
    
    if server_thread:
        try:
            # Keep running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            server.stop()

if __name__ == "__main__":
    main()