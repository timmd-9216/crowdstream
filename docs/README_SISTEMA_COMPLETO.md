# Sistema de Detección de Movimiento de Bailarines

Sistema completo para detectar y visualizar movimiento de bailarines usando YOLO v8, con dashboard de estadísticas y visualizador espacial 3D interactivo.

## 🚀 Inicio Rápido

### Instalación de Entornos Virtuales

Cada servicio tiene su propio entorno virtual. Para instalar todos:

```bash
./scripts/setup-all-venvs.sh
```

Este script crea los entornos virtuales para:
- `movement_dashboard/venv` - Dashboard de monitoreo
- `visualizers/cosmic_skeleton/venv` - Visualizador skeleton
- `visualizers/skeleton_visualizer/venv` - Otro visualizador skeleton
- `visualizers/cosmic_journey/venv` - Visualizador cósmico
- `visualizers/space_visualizer/venv` - Visualizador espacial
- `dance_movement_detector/venv` - Detector de movimiento
- `audio-mixer/venv` - Mezclador de audio

Cada servicio también puede instalarse individualmente ejecutando `./install.sh` dentro de su directorio.

### Iniciar Sistema de Detección y Visualización

Para iniciar el detector de movimiento, visualizador skeleton y dashboard de monitoreo:

```bash
./scripts/perfo-start.sh
```

Este script inicia:
- 🤖 **Detector de movimiento** - Detecta personas y analiza movimiento
- 💀 **Visualizador skeleton** (`cosmic_skeleton`) - Visualización en tiempo real
- 📊 **Dashboard de monitoreo** (`movement_dashboard`) - Estadísticas y gráficos

**Interfaces disponibles:**
- 📊 **Dashboard**: http://localhost:8082
- 💀 **Visualizador Skeleton**: http://localhost:8091

### Iniciar Mezclador de Audio Interactivo

El mezclador de audio recibe mensajes de movimiento (al igual que las visuales) y ajusta la mezcla en tiempo real:

```bash
cd audio-mixer
./scripts/audio-mix-start.sh
```

Este script inicia:
- 🎛️ **Servidor de audio** - Motor de mezcla con filtros EQ
- 🎵 **Mezclador interactivo** - Recibe mensajes OSC de movimiento en puerto 57120

**Puertos:**
- Audio Server OSC: 57122
- Movement OSC: 57120 (recibe del detector)

### Detener todo
```bash
./scripts/kill-all-services.sh
./scripts/kill_audio.sh
```

## 📁 Componentes del Sistema

### 1. 🤖 Dance Movement Detector (`dance_movement_detector/`)
- Detecta personas con YOLO v8 Pose
- Analiza movimiento de brazos, piernas y cabeza
- **Normalización por bounding box**: El movimiento se normaliza por el tamaño del bounding box, haciéndolo independiente de la distancia a la cámara
- Envía datos vía OSC a múltiples destinos

**Puerto OSC de salida**: Envía a 5005 y 5006

**Movimiento Normalizado:**
- Los valores de movimiento son relativos al tamaño de la persona (normalizados)
- No dependen de la distancia a la cámara
- Valores típicos: 0.0 (sin movimiento) a 0.6+ (movimiento muy intenso)

### 2. 📊 Dashboard (`movement_dashboard/`)
- Visualiza estadísticas en tiempo real
- Gráficos históricos con Chart.js
- Estadísticas acumuladas
- Implementado con FastAPI y WebSockets nativos

**Puertos**: OSC 5005, Web 8082

### 3. 💀 Visualizadores (`visualizers/`)
Todos los visualizadores están organizados en la carpeta `visualizers/`:

- **`cosmic_skeleton/`** - Visualización skeleton cósmica (puerto 8091)
- **`skeleton_visualizer/`** - Visualizador skeleton básico (puerto 8093)
- **`cosmic_journey/`** - Viaje cósmico 3D (puerto 8091)
- **`space_visualizer/`** - Visualización espacial 3D con Three.js (puerto 8090)
- **`blur_skeleton_visualizer/`** - Skeleton con efecto blur (puerto 8092)
- **`cosmic_skeleton_standalone/`** - Skeleton con detector integrado (puerto 8094)

Todos reciben mensajes OSC de movimiento y reaccionan en tiempo real.

### 4. 🎵 Audio Mixer (`audio-mixer/`)
- Mezclador de audio interactivo que recibe mensajes de movimiento
- Ajusta filtros EQ (low/mid/high) basado en movimiento
- Mezcla múltiples pistas con transiciones suaves
- Filtros EQ con interpolación suave (50ms por defecto)

**Puertos**: 
- Audio Server OSC: 57122
- Movement OSC: 57120 (recibe del detector)

### 5. 🎮 Service Controller (`service_controller/`)
- Panel web para gestionar todos los servicios
- Iniciar/detener/reiniciar servicios
- Ver logs en tiempo real

**Puerto**: Web 8000 (opcional)

## 🎯 Flujo de Datos

```
📹 Cámara/Video
    ↓
🤖 Detector YOLO v8
    ↓ (OSC Messages)
    ├─→ Puerto 5005 → 📊 Dashboard (8082)
    ├─→ Puerto 5007 → 💀 Visualizadores Skeleton (8091, 8093)
    └─→ Puerto 57120 → 🎵 Audio Mixer (57122)
```

## ⚙️ Configuración de Puertos

**¿Por qué cada servicio necesita su propio puerto OSC?**

Solo un servicio puede escuchar en un puerto a la vez. Por eso:
- Dashboard escucha en puerto OSC **5005**
- Visualizer escucha en puerto OSC **5006**
- Detector **envía a ambos** simultáneamente

| Servicio | Puerto OSC (entrada) | Puerto Web (salida) |
|----------|---------------------|---------------------|
| Dashboard | 5005 | 8082 |
| Visualizadores Skeleton | 5007 | 8091, 8093 |
| Audio Mixer | 57120 | - |
| Detector | Envía a múltiples puertos | - |
| Controller | - | 8000 |

## 📝 Mapeo de Movimiento a Visuales

### Dashboard
Muestra estadísticas de:
- Número de personas
- Movimiento total, brazos, piernas, cabeza
- Promedios y máximos acumulados
- Gráficos históricos

### Visualizador Espacial (configurable)
- 🙌 **Brazos** → Velocidad de viaje
- 🗣️ **Cabeza** → Tamaño de estrellas
- 🦵 **Piernas** → Rotación de cámara
- 💃 **Total** → Intensidad de color y warp drive
- 👥 **Personas** → Densidad de estrellas

Ver [MAPPING_CONFIG.md](MAPPING_CONFIG.md) para personalizar.

## 🛠️ Uso Avanzado

### Ver logs en tiempo real
```bash
tail -f logs/detector.log
tail -f logs/dashboard.log
tail -f logs/visualizer.log
```

### Cambiar intervalo de mensajes
```bash
# Editar dance_movement_detector/config/multi_destination.json
"message_interval": 1.0  # segundos (default: 10)
```

### Personalizar mapeo visual
```bash
# Editar space_visualizer/config/mapping.json
# Ver MAPPING_CONFIG.md para ejemplos
```

### Usar video en lugar de webcam
```bash
cd dance_movement_detector
python3 src/dance_movement_detector.py \
  --config config/multi_destination.json \
  --video path/to/video.mp4
```

## 🔧 Troubleshooting

### "Address already in use"
```bash
./scripts/kill-all-services.sh
# Espera 2 segundos
./scripts/start-all-services.sh
```

### El detector no detecta movimiento
- Verifica que la cámara funcione
- Revisa `logs/detector.log`
- Prueba con `--show-video` para ver detecciones

### Dashboard/Visualizer no actualiza
- Verifica conexión WebSocket (indicador verde en UI)
- Revisa que el detector esté enviando a los puertos correctos
- Chequea `logs/` para errores

### Ver procesos corriendo
```bash
ps aux | grep -E "(detector|dashboard|visualizer)" | grep -v grep
```

### Ver puertos en uso
```bash
lsof -i:5005
lsof -i:5006
lsof -i:8081
lsof -i:8090
```

## 📚 Documentación Adicional

- [QUICK_START.md](QUICK_START.md) - Guía de inicio rápido
- [MAPPING_CONFIG.md](MAPPING_CONFIG.md) - Configuración de mapeo visual
- [RASPBERRY_PI_SETUP.md](RASPBERRY_PI_SETUP.md) - Setup en Raspberry Pi
- Cada componente tiene su propio README en su directorio

## 🎪 Setup para Presentación

### Configuración Recomendada
1. **Laptop/PC con GPU** - Corre el detector
2. **Raspberry Pi o segunda PC** - Corre dashboard + visualizer
3. **Proyector/TV** - Conectado a RPi mostrando visualizer en pantalla completa

### Red Local
```bash
# En laptop (detector) - editar multi_destination.json
{
  "osc_destinations": [
    {"host": "192.168.1.XXX", "port": 5005},  // IP de la RPi
    {"host": "192.168.1.XXX", "port": 5006}
  ]
}

# En Raspberry Pi
./scripts/start-all-services.sh
# Abrir visualizer en fullscreen en el proyector
```

## 🔑 Comandos Clave

```bash
# Iniciar todo
./scripts/start-all-services.sh

# Detener todo
./scripts/kill-all-services.sh

# Ver logs
tail -f logs/detector.log

# Limpiar logs
rm logs/*.log

# Reiniciar un servicio específico
./scripts/kill-all-services.sh
cd dance_visualizer
./start.sh --osc-port 5006
```

## 🐛 Debugging

### Modo verbose del detector
```bash
cd dance_movement_detector
python3 src/dance_movement_detector.py \
  --config config/multi_destination.json \
  --show-video  # Ver detecciones en vivo
```

### Test de mensajes OSC
```bash
# Instalar oscdump
pip install python-osc

# Escuchar en puerto 5005
python3 -m pythonosc.osc_udp_client 127.0.0.1 5005
```

## 📊 Estadísticas del Sistema

**Uso de recursos esperado:**
- Detector: CPU 50-90%, RAM 500MB-1GB
- Dashboard: CPU 5-10%, RAM 100MB
- Visualizer: CPU 10-20%, RAM 150MB

**Rendimiento:**
- Detector: 15-30 FPS (depende de hardware)
- Dashboard: Actualización cada 1-10s (configurable)
- Visualizer: 60 FPS en navegador

## 🎨 Personalización

### Cambiar colores del visualizador
```bash
# Editar space_visualizer/static/js/space_visualizer.js
# Líneas 89-100: Colores de estrellas
```

### Cambiar estilos del dashboard
```bash
# Editar dance_dashboard/static/css/dashboard.css
```

### Agregar nuevos efectos visuales
Ver [MAPPING_CONFIG.md](MAPPING_CONFIG.md) para crear mapeos personalizados.

## 🤝 Contribuir

1. Documentar cambios en README correspondiente
2. Probar con `./scripts/start-all-services.sh`
3. Verificar que `./scripts/kill-all-services.sh` funcione

## 📜 Licencia

Proyecto académico - FIUBA Seminario

## 🔗 Enlaces

- YOLO v8: https://docs.ultralytics.com/
- Three.js: https://threejs.org/
- Chart.js: https://www.chartjs.org/
- python-osc: https://pypi.org/project/python-osc/
