# Dance Movement Detector

Sistema de detección de movimiento de bailarines usando YOLO v8 Pose Detection. Analiza grupos de personas bailando y envía mensajes OSC periódicos al DJ con información sobre el movimiento.

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

Edita `config/config.json` para cambiar configuración permanente:

```json
{
  "video_source": 0,           // 0 para webcam, o path a video
  "message_interval": 10.0,    // Segundos entre mensajes
  "osc_host": "127.0.0.1",     // IP destino
  "osc_port": 5005,            // Puerto OSC
  "osc_base_address": "/dance", // Base address para mensajes OSC
  "history_frames": 10,        // Frames para calcular movimiento
  "show_video": true,          // Mostrar video con detecciones
  "save_to_file": false,       // Guardar stats en JSON
  "output_file": "movement_stats.json"
}
```

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

## Troubleshooting

### No se detecta la webcam
```bash
./start.sh --video 0  # Intenta webcam 0
./start.sh --video 1  # O webcam 1
```

### Mejor rendimiento
El modelo usa YOLOv8n (nano) por defecto. Para mayor precisión pero menor velocidad, edita `src/dance_movement_detector.py` línea 177:
```python
self.model = YOLO('yolov8m-pose.pt')  # medium model
```

### Mensajes OSC no se reciben
Verifica que el DJ software esté escuchando en el puerto correcto (default: 5005)
