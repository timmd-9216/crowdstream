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

### 📁 Configuraciones Pre-hechas

| Config | FPS (RPi4) | CPU | Uso Recomendado |
|--------|-----------|-----|-----------------|
| `config_rpi_max_performance.json` | 20-25 | 40-50% | Shows en vivo, máxima velocidad |
| `config_rpi_optimized.json` ⭐ | 12-18 | 50-70% | Uso general (recomendado) |
| `config.json` | 5-8 | 80-100% | Testing, debugging |

### Usar configuración optimizada

```bash
# Raspberry Pi - Máximo rendimiento
./start_detector_rpi.sh config/config_rpi_max_performance.json

# Raspberry Pi - Balanceado (recomendado)
./start_detector_rpi.sh config/config_rpi_optimized.json

# Alta calidad (más lento)
./start_detector_rpi.sh config/config.json
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

## Ejemplo de recepción (Processing/Max/Pure Data)

Los valores de movimiento son pixeles de desplazamiento promedio. Valores típicos:
- Baile moderado: 10-50
- Baile energético: 50-150+
- Movimiento mínimo: <10

Puedes escalar/normalizar estos valores según tu aplicación.

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
# 1. Usar configuración de máximo rendimiento
./start_detector_rpi.sh config/config_rpi_max_performance.json

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
jq . config/config_rpi_optimized.json

# Usar ruta absoluta
./start_detector_rpi.sh /home/hordia/dev/crowdstream-audio/dance_movement_detector/config/config_rpi_max_performance.json
```

### Mensajes OSC no se reciben
```bash
# Verificar puerto correcto
# El visualizador debe estar escuchando en el mismo puerto (default: 5005)

# Probar con múltiples destinos en config/multi_destination.json
```

## Performance Esperada

### Raspberry Pi 4

| Configuración | FPS | CPU | Calidad |
|--------------|-----|-----|---------|
| Max Performance | 20-25 | 40-50% | ⭐⭐ |
| Balanced | 12-18 | 50-70% | ⭐⭐⭐⭐ |
| High Quality | 5-8 | 80-100% | ⭐⭐⭐⭐⭐ |

### MacOS / Desktop

| Configuración | FPS | CPU | Calidad |
|--------------|-----|-----|---------|
| Balanced | 30-40 | 30-40% | ⭐⭐⭐⭐ |
| High Quality | 20-30 | 50-60% | ⭐⭐⭐⭐⭐ |
