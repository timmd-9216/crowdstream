# OSC Mixer Client

Script automatizado para crear mezclas enviando mensajes OSC al audio-engine.

## 📋 Descripción

`osc_mixer_client.py` es un cliente que lee las canciones disponibles en las carpetas `stems/` y `song-structures/` y envía comandos OSC al audio-engine para crear mezclas automáticas.

## 🚀 Inicio Rápido

### 1. Preparar Directorios

Crear la estructura de carpetas necesaria:

```bash
# Desde la raíz del proyecto
mkdir -p stems song-structures
```

### 2. Organizar Stems

Colocar los stems de cada canción en subdirectorios:

```
stems/
├── song_1/
│   ├── bass.wav
│   ├── drums.wav
│   ├── vocals.wav
│   ├── piano.wav
│   └── other.wav
├── song_2/
│   ├── bass.wav
│   ├── drums.wav
│   └── vocals.wav
└── song_3/
    └── ...
```

### 3. Estructuras de Canciones (Opcional)

Si tienes información de la estructura de las canciones (secciones como intro, verse, chorus), créalas en formato JSON:

```json
{
  "segments": [
    {
      "label": "intro",
      "start": 0.0,
      "duration": 8.0
    },
    {
      "label": "verse",
      "start": 8.0,
      "duration": 16.0
    },
    {
      "label": "chorus",
      "start": 24.0,
      "duration": 12.0
    }
  ]
}
```

Guardar como `song-structures/song_1.json` (mismo nombre que la carpeta del stem).

### 4. Iniciar Audio Server

Primero, iniciar el servidor de audio:

```bash
cd src/audio-engine
python audio_server.py
```

Esperar el mensaje: `🎛️💾 PYTHON AUDIO SERVER READY 💾🎛️`

### 5. Iniciar Mixer Inteligente

En otra terminal:

```bash
cd src/audio-engine
python stem_mixer_smart.py
```

### 6. Ejecutar Cliente OSC

En una tercera terminal:

```bash
cd src/audio-engine
python osc_mixer_client.py --list  # Listar canciones disponibles
```

## 📖 Uso

### Listar Canciones Disponibles

```bash
python osc_mixer_client.py --list
```

### Ejecutar Demo Completo

Ejecuta una secuencia de mezclas demostrativas:

```bash
python osc_mixer_client.py --demo
```

### Crear Mezcla Básica

Mezcla dos canciones completas:

```bash
python osc_mixer_client.py --basic-mix 0 1 --bpm 130
```

- `0` y `1` son los IDs de las canciones (ver con `--list`)
- `--bpm 130` establece el tempo de la mezcla

### Crear Mashup

Combina stems aleatorios de múltiples canciones:

```bash
python osc_mixer_client.py --mashup 3 --bpm 128
```

- `3` es el número de canciones a combinar
- Selecciona stems aleatorios de cada canción

### Crear Build Progresivo

Construcción progresiva añadiendo stems gradualmente:

```bash
python osc_mixer_client.py --build 0 --bpm 125
```

- Empieza con bass
- Añade drums después de 4 segundos
- Añade vocals después de 4 segundos más
- Etc.

## 🎛️ Opciones Avanzadas

### Cambiar Host/Puerto OSC

```bash
python osc_mixer_client.py --host 192.168.1.100 --port 5005 --demo
```

### Personalizar BPM

Todos los comandos aceptan `--bpm`:

```bash
python osc_mixer_client.py --mashup 4 --bpm 140
```

## 📡 Mensajes OSC Soportados

El script envía los siguientes mensajes OSC al audio-engine:

| Mensaje | Descripción | Ejemplo |
|---------|-------------|---------|
| `/bpm` | Establecer BPM global | `/bpm 128.0` |
| `/crossfade` | Crossfade entre decks | `/crossfade 0.5` |
| `/stem/bass` | Volumen de bass | `/stem/bass 0.8` |
| `/stem/drums` | Volumen de drums | `/stem/drums 0.7` |
| `/stem/vocals` | Volumen de vocals | `/stem/vocals 0.9` |
| `/stem/piano` | Volumen de piano | `/stem/piano 0.6` |
| `/stem/other` | Volumen de otros | `/stem/other 0.5` |

## 🎨 Patrones de Mezcla

### 1. Basic Mix
- Carga canción completa en Deck A
- Carga canción completa en Deck B
- Crossfade progresivo de A a B

### 2. Mashup
- Selecciona canciones al azar
- Combina diferentes stems de diferentes canciones
- Mix equilibrado en ambos decks

### 3. Progressive Build
- Empieza con un stem (bass)
- Añade stems progresivamente cada 4 segundos
- Crea tensión y energía creciente

## 🔧 Personalización

### Crear Tus Propios Patrones

Edita `osc_mixer_client.py` y añade métodos personalizados:

```python
def my_custom_pattern(self, song_id: int):
    """Mi patrón personalizado"""
    self.set_bpm(140.0)

    # Tu lógica aquí
    self.load_stem_to_deck_a(song_id, 'drums')
    time.sleep(2)
    self.load_stem_to_deck_a(song_id, 'bass')

    # etc.
```

### Ajustar Tiempos

Modifica los `time.sleep()` en los métodos de mezcla para cambiar los tiempos entre acciones.

## 📚 Documentación Relacionada

- [SMART_STEM_MIXER_GUIDE.md](SMART_STEM_MIXER_GUIDE.md) - Guía completa del mixer
- [OSC_MESSAGES_REFERENCE.md](OSC_MESSAGES_REFERENCE.md) - Referencia de mensajes OSC
- [README.md](README.md) - Documentación general del audio-engine

## ⚠️ Notas

1. **Requiere audio-engine activo**: El audio_server.py y stem_mixer_smart.py deben estar corriendo
2. **Estructura de carpetas**: Las carpetas `stems/` y `song-structures/` deben estar en el directorio de trabajo
3. **Formato de audio**: Los stems deben ser archivos WAV
4. **Sincronización**: El mixer usa cuantización de beats para sincronización temporal

## 🐛 Solución de Problemas

### "No songs available"
- Verificar que la carpeta `stems/` existe y tiene subdirectorios con archivos .wav
- Verificar permisos de lectura

### "Connection refused"
- Asegurarse de que audio_server.py está corriendo
- Verificar que el puerto OSC (5005) está disponible

### Sin sonido
- Verificar que audio_server.py está reproduciendo (ver logs)
- Verificar volumen del sistema
- Revisar configuración de audio en mixer_config.json

## 💡 Ejemplos Completos

### Sesión de Mezcla Completa

```bash
# Terminal 1: Audio server
cd src/audio-engine
python audio_server.py

# Terminal 2: Mixer inteligente
cd src/audio-engine
python stem_mixer_smart.py

# Terminal 3: Cliente OSC
cd src/audio-engine

# Listar canciones
python osc_mixer_client.py --list

# Crear mashup de 3 canciones a 135 BPM
python osc_mixer_client.py --mashup 3 --bpm 135

# Esperar a que termine...

# Crear build progresivo de la canción 2 a 120 BPM
python osc_mixer_client.py --build 2 --bpm 120
```

¡Disfruta creando mezclas automáticas! 🎵
