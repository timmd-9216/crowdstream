from pythonosc import udp_client

client = udp_client.SimpleUDPClient("127.0.0.1", 57120)

# Stems posibles: ["vocals", "drums", "bass", "piano", "other"]

#  Reproducir un stem
client.send_message("/play_sound", ["vocals", "/path/to/vocals.wav", 0.8])
client.send_message("/play_sound", ["drums", "/path/to/drums.wav", 0.6])
client.send_message("/play_sound", ["bass", "/path/to/bass.wav", 0.5])

# Cambiar volumen de un stem
client.send_message("/set_volume", ["vocals", 0.2])
client.send_message("/set_volume", ["drums", 0.9])

# Detener un stem
client.send_message("/stop_sound", ["bass"])

# Detener todos
client.send_message("/stop_all", [])
