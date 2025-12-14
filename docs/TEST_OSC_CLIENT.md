# 🧪 Test del OSC Mixer Client v2

## ✅ Script Completado

Se ha creado `osc_mixer_client_v2.py` que **envía mensajes OSC REALES** al `audio_server.py`.

## 📁 Archivos Creados

1. **[osc_mixer_client_v2.py](osc_mixer_client_v2.py)** - Cliente OSC principal con mensajes reales
2. **[run_mixer.sh](run_mixer.sh)** - Script helper para ejecución rápida
3. **[osc_client_config.json](osc_client_config.json)** - Configuración (puerto 57120)
4. **[QUICK_START.md](QUICK_START.md)** - Guía de inicio rápido

## 🎵 Canciones Detectadas

El script detectó **11 canciones de Eurovisión 2025**:
- 0: Albania - Zjerm
- 1: Armenia - SURVIVOR
- 2: Australia - Milkshake Man
- 3: Austria - Wasted Love
- 4: Azerbaijan - Run With U
- 5: Belgium - Strobe Lights
- 6: Croatia - Poison Cake
- 7: Cyprus - Shh
- 8: Czechia - Kiss Kiss Goodbye
- 9: Denmark - Hallucination
- 10: Estonia - Espresso Macchiato

Cada una con 5 stems: bass, drums, vocals, piano, other

## 🧪 Cómo Probar

### Opción 1: Prueba Simple (Solo Listar)

```bash
cd src/audio-engine
./run_mixer.sh list
```

✅ Esto funciona sin necesitar audio_server corriendo

### Opción 2: Prueba Completa con Audio

**Terminal 1: Iniciar Audio Server**
```bash
cd src/audio-engine
python audio_server.py
```

Espera a ver:
```
🎛️💾 PYTHON AUDIO SERVER READY 💾🎛️
🔊 Audio: 44100Hz, 256 samples
🔌 OSC: localhost:57120
```

**Terminal 2: Ejecutar Mezcla**
```bash
cd src/audio-engine

# Opción A: Mix básico (20 seg aprox)
./run_mixer.sh mix 0 1 130

# Opción B: Mashup rápido
./run_mixer.sh mashup 3 135

# Opción C: Build progresivo
./run_mixer.sh build 0 125
```

## 📡 Mensajes OSC Que Envía

Ejemplo de secuencia real para `./run_mixer.sh mix 0 1 130`:

```
# Cleanup inicial
→ /mixer_cleanup []

# Cargar Deck A (Albania)
→ /load_buffer [1000, "/path/to/stems/.../bass.wav", "Albania_bass"]
→ /play_stem [1000, 1.024, 0.8, 1, 0.0]

→ /load_buffer [1001, "/path/to/stems/.../drums.wav", "Albania_drums"]
→ /play_stem [1001, 1.024, 0.8, 1, 0.0]

→ /load_buffer [1002, "/path/to/stems/.../vocals.wav", "Albania_vocals"]
→ /play_stem [1002, 1.024, 0.8, 1, 0.0]

# Crossfade inicial (solo A)
→ /crossfade_levels [1.0, 0.0]

# Cargar Deck B (Armenia)
→ /load_buffer [1100, "/path/to/stems/.../bass.wav", "Armenia_bass"]
→ /play_stem [1100, 1.030, 0.8, 1, 0.0]

→ /load_buffer [1101, "/path/to/stems/.../drums.wav", "Armenia_drums"]
→ /play_stem [1101, 1.030, 0.8, 1, 0.0]

→ /load_buffer [1102, "/path/to/stems/.../vocals.wav", "Armenia_vocals"]
→ /play_stem [1102, 1.030, 0.8, 1, 0.0]

# Crossfade progresivo A → B (11 pasos cada 1.5 seg)
→ /crossfade_levels [1.0, 0.0]    # 100% A
→ /crossfade_levels [0.99, 0.16]  # 90% A, 10% B
→ /crossfade_levels [0.95, 0.31]  # 80% A, 20% B
...
→ /crossfade_levels [0.0, 1.0]    # 100% B
```

## 🎛️ Características Implementadas

### ✅ Funcionalidades Principales

- [x] Descubrimiento automático de canciones en `stems/`
- [x] Lectura de estructuras JSON en `song-structures/`
- [x] Gestión de buffer IDs (Deck A: 1000-1099, Deck B: 1100-1199)
- [x] Cálculo automático de playback rate para BPM matching
- [x] Crossfade con curva equal-power (suena mejor)
- [x] Envío de mensajes OSC reales al puerto 57120
- [x] Soporte para secciones de canciones (intro, verse, chorus, etc.)

### 🎨 Patrones de Mezcla

1. **Basic Mix** - Mezcla completa entre 2 canciones
2. **Mashup** - Combina stems aleatorios de N canciones
3. **Progressive Build** - Construcción gradual añadiendo stems
4. **Demo Sequence** - Secuencia completa de los 3 patrones

## 🔍 Verificación de Funcionamiento

### Lo que DEBES ver en el cliente:

```
🎛️ OSC Mixer Client v2 (Direct OSC)
📡 Audio Server: localhost:57120
...
📥 Deck A [buf:1000]: bass from 01-01 Zjerm...
▶️  Play: rate=1.024, vol=0.80, start=0.000
```

### Lo que DEBES ver en el servidor:

```
📡 OSC RECEIVED: /load_buffer (1000, '/Users/.../bass.wav', 'Albania_bass')
✅ Loaded Albania_bass (8.5 MB)
📡 OSC RECEIVED: /play_stem (1000, 1.024, 0.8, 1, 0.0)
▶️  Playing buffer 1000, rate: 1.024
```

### Y DEBES ESCUCHAR:
🔊 Audio mezclándose en tiempo real!

## 📊 Estado del Código

| Componente | Estado | Notas |
|------------|--------|-------|
| Descubrimiento de canciones | ✅ | 11 canciones detectadas |
| Lectura de estructuras JSON | ✅ | Tempo y secciones |
| Mensajes OSC | ✅ | Envío real al puerto 57120 |
| Buffer management | ✅ | Deck A/B separados |
| BPM matching | ✅ | Cálculo automático de rate |
| Crossfade | ✅ | Equal-power curve |
| Patrones de mezcla | ✅ | Basic, Mashup, Build |
| Configuración JSON | ✅ | Paths y defaults |
| Scripts helper | ✅ | run_mixer.sh |
| Documentación | ✅ | Este archivo + QUICK_START |

## 🚀 Próximos Pasos Sugeridos

1. **Probar con audio_server.py corriendo** (la prueba definitiva)
2. **Ajustar timings** si es necesario (actualmente 1.5s entre crossfades)
3. **Añadir más patrones** de mezcla personalizados
4. **Integrar con dance_energy_analyzer** para mezclas reactivas
5. **Crear interfaz web** para control visual

## 💡 Uso Avanzado

### Configurar Paths Personalizados

```bash
# Via variables de entorno
STEMS_DIR=/custom/path ./run_mixer.sh list

# Via argumentos
venv/bin/python3 osc_mixer_client_v2.py \
  --stems-dir /custom/stems \
  --structures-dir /custom/structures \
  --list
```

### Cambiar Puerto OSC

```bash
venv/bin/python3 osc_mixer_client_v2.py \
  --port 5005 \
  --mix 0 1
```

### Ajustar BPM

```bash
./run_mixer.sh mix 0 1 140    # Mix a 140 BPM
./run_mixer.sh build 3 115    # Build a 115 BPM
```

## ✅ Checklist de Prueba

- [ ] `./run_mixer.sh list` muestra las 11 canciones
- [ ] `python audio_server.py` inicia sin errores
- [ ] `./run_mixer.sh mix 0 1 130` envía mensajes OSC
- [ ] audio_server.py muestra "OSC RECEIVED" y "Playing buffer"
- [ ] Se escucha audio mezclándose
- [ ] El crossfade funciona suavemente
- [ ] `./run_mixer.sh mashup 3` crea una mezcla interesante
- [ ] `./run_mixer.sh build 0` construye progresivamente

¡Todo listo para mezclar Eurovisión 2025 con OSC! 🎵✨
