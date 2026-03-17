# Dance Movement Detector

Sistema de detección de movimiento de bailarines usando YOLO v8 Pose Detection. Analiza grupos de personas bailando y envía mensajes OSC periódicos al DJ con información sobre el movimiento.

## 🚀 Quick Start

### Raspberry Pi (Optimizado)
```bash
./start_detector_rpi.sh
```

### MacOS / Desktop
```bash
./start.sh
```

## Características

- **Detección de poses** con YOLO v8
- **Análisis de movimiento separado** por:
  - Movimiento total del cuerpo
  - Movimiento de brazos
  - Movimiento de piernas
  - Movimiento de cabeza
- **Normalización por bounding box**: El movimiento se normaliza por el tamaño del bounding box, haciéndolo independiente de la distancia a la cámara
- **Mensajes OSC configurables** (default: cada 10 segundos)
- **Tracking de múltiples personas** simultáneamente
- **Fuentes de video flexibles**: webcam o archivos de video
- **Optimizado para Raspberry Pi** (12-25 FPS según configuración)

## Instalación

```bash
cd dance_movement_detector
./start.sh
```

El script automáticamente:
1. Crea un entorno virtual
2. Instala todas las dependencias
3. Inicia el detector

## Uso

### Modo básico (webcam)
```bash
./start.sh
```

### Usar archivo de video
```bash
./start.sh --video path/to/video.mp4
```

### Cambiar intervalo de mensajes (5 segundos)
```bash
./start.sh --interval 5
```

### Enviar a otro host
```bash
./start.sh --osc-host 192.168.1.100 --osc-port 7000
```

### Sin visualización (headless)
```bash
./start.sh --no-display
```

### Combinación de opciones
```bash
./start.sh --video dance_video.mp4 --interval 3 --osc-host 192.168.1.50
```

## Mensajes OSC

El detector envía los siguientes mensajes OSC:

- `/dance/person_count` - Número de personas detectadas (int)
- `/dance/total_movement` - Movimiento total promedio (float)
- `/dance/arm_movement` - Movimiento de brazos promedio (float)
- `/dance/leg_movement` - Movimiento de piernas promedio (float)
- `/dance/head_movement` - Movimiento de cabeza promedio (float)

## Configuración

### 📁 Configuraciones disponibles

| Config | FPS (RPi4) | OSC destinos | Uso |
|--------|-----------|--------------|-----|
| `multi_destination.json` | según params | 5005, 5007, etc. | **Por defecto (perfo)** en desktop/Mac — múltiples destinos (editable) |
| `raspberry_pi_optimized.json` ⭐ RPi | 12-18 | 5005, 5007, 5009, 57120 | **Por defecto en Raspberry Pi** (dashboard + visualizadores) |
| `config.json` | 5-8 | **solo 5005** | Testing; **no envía al visualizador** (puerto 5007) |

**Importante:** Para que el reconocimiento se vea en el **dashboard y en el visualizador** (cosmic_skeleton), el detector debe usar una config con `osc_destinations` que incluya 5005 (dashboard) y 5007 (cosmic_skeleton). Por defecto `perfo-start.sh` usa: en **Raspberry Pi** `raspberry_pi_optimized.json`, en desktop/Mac `multi_destination.json`. `config.json` solo tiene `osc_port: 5005`, por eso el visualizador no recibe datos si usás esa config.

### Usar configuración optimizada

```bash
# Por defecto (perfo) — múltiples destinos (dashboard + visualizador)
./start.sh --config config/multi_destination.json

# Alternativa optimizada RPi
./start.sh --config config/raspberry_pi_optimized.json

# Solo testing (solo dashboard recibe)
./start.sh --config config/config.json
```

### Configuración manual

Edita `config/config.json` o crea tu propio archivo:

```json
{
  "model": "yolov8n-pose.pt",  // Modelo (yolov8n más rápido)
  "imgsz": 416,                 // Tamaño imagen (320/416/640)
  "skip_frames": 1,             // Saltar frames (0=todos, 1=cada 2, 2=cada 3)
  "camera_width": 640,
  "camera_height": 480,
  "show_video": false,          // false en Raspberry Pi headless
  "conf_threshold": 0.35,
  "max_det": 5,
  "history_frames": 5
}
```

**📖 Guía completa**: Ver [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)

### Enviar a múltiples destinos

Para enviar datos a múltiples aplicaciones simultáneamente (dashboard + visualizer), usa `config/multi_destination.json`:

```json
{
  "video_source": 0,
  "message_interval": 10.0,
  "osc_destinations": [
    {
      "host": "127.0.0.1",
      "port": 5005,
      "description": "Dashboard"
    },
    {
      "host": "127.0.0.1",
      "port": 5006,
      "description": "Visualizer"
    }
  ],
  "osc_base_address": "/dance",
  "history_frames": 10,
  "show_video": true
}
```

Iniciar con configuración personalizada:
```bash
./start.sh --config config/multi_destination.json
```

## Cálculo de Movimiento

### Normalización por Bounding Box

El movimiento se calcula de forma **normalizada por el tamaño del bounding box** de cada persona. Esto significa que:

- **Independiente de la distancia**: Una persona cerca de la cámara y otra lejos, con el mismo movimiento relativo, producirán valores similares
- **Proporcional al tamaño**: El movimiento se mide como fracción del tamaño de la persona (normalizado)
- **Más preciso**: Los valores reflejan la intensidad del movimiento, no solo la distancia en píxeles

**Cómo funciona:**
1. Se calcula el tamaño del bounding box (promedio de ancho y alto)
2. El movimiento en píxeles se divide por el tamaño del bbox
3. El resultado es un valor normalizado que representa movimiento relativo

**Ejemplo:**
- Persona cerca (bbox 200px) moviendo 50px → movimiento normalizado: 0.25
- Persona lejos (bbox 100px) moviendo 25px → movimiento normalizado: 0.25
- Ambas tienen el mismo movimiento relativo, independientemente de la distancia

### Valores de Movimiento

Los valores de movimiento son **normalizados** (relativos al tamaño de la persona). Valores típicos:
- Movimiento mínimo: < 0.1
- Baile moderado: 0.1 - 0.3
- Baile energético: 0.3 - 0.6+
- Movimiento muy intenso: > 0.6

Puedes escalar estos valores según tu aplicación. Los valores anteriores (en píxeles absolutos) ya no son aplicables debido a la normalización.

## Requisitos del sistema

- Python 3.8+
- Webcam o archivos de video
- ~2GB RAM
- CPU moderna (GPU opcional para mejor rendimiento)

## Teclas

- `q` - Salir del detector

## 📚 Documentación

- **[CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)** - Guía completa de configuración
- **[RASPBERRY_PI_OPTIMIZATION.md](RASPBERRY_PI_OPTIMIZATION.md)** - Optimizaciones para Raspberry Pi

## Troubleshooting

### FPS bajo en Raspberry Pi
```bash
# 1. Usar configuración optimizada (envía a dashboard + visualizador)
./start_detector_rpi.sh config/raspberry_pi_optimized.json

# 2. Verificar temperatura (debe ser <80°C)
vcgencmd measure_temp

# 3. Verificar throttling
vcgencmd get_throttled  # Debe ser 0x0
```

### No se detecta la webcam
```bash
# Raspberry Pi: verificar cámara habilitada
vcgencmd get_camera  # Debe ser: supported=1 detected=1

# Probar diferentes índices
./start.sh --video 0
./start.sh --video 1
```

### Configuración no toma efecto
```bash
# Verificar sintaxis JSON
jq . config/raspberry_pi_optimized.json

# Usar ruta absoluta si hace falta
./start_detector_rpi.sh $(pwd)/config/raspberry_pi_optimized.json
```

### Mensajes OSC no se reciben / el reconocimiento no aparece en el visualizador
- **Causa frecuente:** Estás usando `config.json`, que solo envía al puerto 5005 (dashboard). El visualizador cosmic_skeleton escucha en **5007**.
- **Solución:** Usar una config con `osc_destinations` que incluya 5005 y 5007:
  ```bash
  ./start.sh --config config/multi_destination.json
  # o
  ./start.sh --config config/raspberry_pi_optimized.json
  ```
- Si arrancás todo con `./scripts/perfo-start.sh`, en RPi usa `raspberry_pi_optimized.json` y en desktop `multi_destination.json`.
- Verificar que dashboard y visualizador estén levantados antes que el detector y que los puertos 5005 y 5007 estén libres: `lsof -i:5005` y `lsof -i:5007`.

## Performance Esperada

### Raspberry Pi 4

| Configuración | FPS | CPU | Calidad |
|--------------|-----|-----|---------|
| Max Performance | 20-25 | 40-50% | ⭐⭐ |
| Balanced (raspberry_pi_optimized) | 12-18 | 50-70% | ⭐⭐⭐⭐ |
| High Quality (config.json) | 5-8 | 80-100% | ⭐⭐⭐⭐⭐ |

### MacOS / Desktop

| Configuración | FPS | CPU | Calidad |
|--------------|-----|-----|---------|
| Balanced | 30-40 | 30-40% | ⭐⭐⭐⭐ |
| High Quality | 20-30 | 50-60% | ⭐⭐⭐⭐⭐ |
