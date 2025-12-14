# 🎛️ OSC Mixer Client v2 - Quick Start

Script que envía **mensajes OSC reales** directamente al `audio_server.py` para crear mezclas automáticas.

## ⚡ Inicio Rápido

### 1. Iniciar Audio Server

```bash
cd src/audio-engine
python audio_server.py
```

Espera a ver: `🎛️💾 PYTHON AUDIO SERVER READY 💾🎛️`

### 2. Ejecutar Mezclas

En otra terminal:

```bash
cd src/audio-engine

# Listar canciones
./run_mixer.sh list

# Demo completo
./run_mixer.sh demo

# Mix básico (canciones 0 y 1 a 135 BPM)
./run_mixer.sh mix 0 1 135

# Mashup de 4 canciones a 140 BPM
./run_mixer.sh mashup 4 140

# Build progresivo de canción 2 a 120 BPM
./run_mixer.sh build 2 120
```

## 🎵 Mensajes OSC Enviados

El script envía estos mensajes OSC reales al audio_server.py (puerto 57120):

| Acción | Mensaje OSC | Parámetros |
|--------|-------------|------------|
| Cargar stem | `/load_buffer` | `[buffer_id, file_path, label]` |
| Reproducir | `/play_stem` | `[buffer_id, rate, volume, loop, start_pos]` |
| Crossfade | `/crossfade_levels` | `[deck_a_vol, deck_b_vol]` |
| Volumen | `/stem_volume` | `[buffer_id, volume]` |
| Parar | `/stop_stem` | `[buffer_id]` |
| Limpiar | `/mixer_cleanup` | `[]` |

## 🎛️ Patrones de Mezcla

### 1. Basic Mix
Mezcla completa entre 2 canciones con crossfade gradual:
- Carga canción 1 en Deck A (bass, drums, vocals)
- Carga canción 2 en Deck B (bass, drums, vocals)
- Crossfade progresivo de A a B

### 2. Mashup
Combina stems aleatorios de múltiples canciones:
- Selecciona N canciones al azar
- Escoge un stem diferente de cada una
- Los carga todos en Deck A

### 3. Progressive Build
Construcción progresiva añadiendo stems gradualmente:
- Empieza solo con bass (4 seg)
- Añade drums (4 seg)
- Añade vocals (4 seg)
- Añade piano y otros elementos

## 🔧 Configuración

Edita `osc_client_config.json`:

```json
{
  "paths": {
    "stems_dir": "stems",
    "structures_dir": "song-structures"
  },
  "osc": {
    "host": "localhost",
    "port": 57120
  },
  "mixing": {
    "default_bpm": 128.0
  }
}
```

## 📁 Estructura de Archivos

```
src/audio-engine/
├── audio_server.py           # Servidor OSC (iniciar primero)
├── osc_mixer_client_v2.py    # Cliente OSC con mensajes reales
├── run_mixer.sh              # Script helper
├── osc_client_config.json    # Configuración
├── stems/                    # Canciones
│   └── song_name/
│       ├── bass.wav
│       ├── drums.wav
│       ├── vocals.wav
│       ├── piano.wav
│       └── other.wav
└── song-structures/          # Estructuras JSON
    └── song_name.json
```

## 🎯 Ejemplo Completo

```bash
# Terminal 1: Iniciar audio server
cd src/audio-engine
python audio_server.py

# Terminal 2: Ejecutar mezclas
cd src/audio-engine

# Ver canciones disponibles
./run_mixer.sh list

# Crear mezcla entre Albania (0) y Armenia (1) a 130 BPM
./run_mixer.sh mix 0 1 130

# Escuchar el resultado por ~20 segundos...

# Crear mashup de 3 canciones a 135 BPM
./run_mixer.sh mashup 3 135
```

## 🔍 Verificar que Funciona

Cuando ejecutas un comando, deberías ver:

**En el cliente (run_mixer.sh):**
```
📥 Deck A [buf:1000]: bass from 01-01 Zjerm...
▶️  Play: rate=1.024, vol=0.80, start=0.000
📥 Deck A [buf:1001]: drums from 01-01 Zjerm...
▶️  Play: rate=1.024, vol=0.80, start=0.000
```

**En el servidor (audio_server.py):**
```
📡 OSC RECEIVED: /load_buffer (1000, '/path/to/bass.wav', 'label')
✅ Loaded label (8.5 MB)
📡 OSC RECEIVED: /play_stem (1000, 1.024, 0.8, 1, 0.0)
▶️  Playing buffer 1000, rate: 1.024
```

## 🆚 Diferencias con Versión Anterior

| Característica | v1 (osc_mixer_client.py) | v2 (osc_mixer_client_v2.py) |
|----------------|--------------------------|------------------------------|
| Mensajes OSC | Solo documentados | **Enviados realmente** |
| Puerto | 5005 (stem_mixer_smart) | 57120 (audio_server.py) |
| Control | Via CLI commands | **Via OSC directo** |
| Buffer IDs | N/A | Gestionados (1000-1099 A, 1100-1199 B) |
| BPM matching | N/A | **Calculado automáticamente** |

## ⚠️ Troubleshooting

### "Connection refused"
→ Asegúrate de que `audio_server.py` está corriendo

### No se escucha sonido
→ Verifica que `audio_server.py` muestra "Playing buffer..."
→ Revisa volumen del sistema

### "Invalid song ID"
→ Ejecuta `./run_mixer.sh list` para ver IDs válidos

### Puerto ocupado
→ Verifica que no hay otro proceso en puerto 57120:
```bash
lsof -i :57120
```

¡Listo para mezclar! 🎵✨
