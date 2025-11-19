# Sistema de Detección de Movimiento de Bailarines

Sistema completo para detectar y visualizar movimiento de bailarines usando YOLO v8, con dashboard de estadísticas y visualizador espacial 3D interactivo.

## 🚀 Inicio Rápido

### Iniciar todo el sistema
```bash
./start-all-services.sh
```

### Abrir interfaces
- 📊 **Dashboard**: http://localhost:8081
- 🌌 **Visualizador Espacial**: http://localhost:8090

### Detener todo
```bash
./kill-all-services.sh
```

## 📁 Componentes del Sistema

### 1. 🤖 Dance Movement Detector (`dance_movement_detector/`)
- Detecta personas con YOLO v8 Pose
- Analiza movimiento de brazos, piernas y cabeza
- Envía datos vía OSC a múltiples destinos

**Puerto OSC de salida**: Envía a 5005 y 5006

### 2. 📊 Dashboard (`dance_dashboard/`)
- Visualiza estadísticas en tiempo real
- Gráficos históricos con Chart.js
- Estadísticas acumuladas

**Puertos**: OSC 5005, Web 8081

### 3. 🌌 Space Visualizer (`space_visualizer/`)
- Visualización 3D con Three.js
- Viaje espacial reactivo al movimiento
- Mapeo configurable vía JSON

**Puertos**: OSC 5006, Web 8090

### 4. 🎮 Service Controller (`service_controller/`)
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
    ├─→ Puerto 5005 → 📊 Dashboard (8081)
    └─→ Puerto 5006 → 🌌 Visualizer (8090)
```

## ⚙️ Configuración de Puertos

**¿Por qué cada servicio necesita su propio puerto OSC?**

Solo un servicio puede escuchar en un puerto a la vez. Por eso:
- Dashboard escucha en puerto OSC **5005**
- Visualizer escucha en puerto OSC **5006**
- Detector **envía a ambos** simultáneamente

| Servicio | Puerto OSC (entrada) | Puerto Web (salida) |
|----------|---------------------|---------------------|
| Dashboard | 5005 | 8081 |
| Visualizer | 5006 | 8090 |
| Detector | Envía a 5005 + 5006 | - |
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
./kill-all-services.sh
# Espera 2 segundos
./start-all-services.sh
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
./start-all-services.sh
# Abrir visualizer en fullscreen en el proyector
```

## 🔑 Comandos Clave

```bash
# Iniciar todo
./start-all-services.sh

# Detener todo
./kill-all-services.sh

# Ver logs
tail -f logs/detector.log

# Limpiar logs
rm logs/*.log

# Reiniciar un servicio específico
./kill-all-services.sh
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
2. Probar con `./start-all-services.sh`
3. Verificar que `./kill-all-services.sh` funcione

## 📜 Licencia

Proyecto académico - FIUBA Seminario

## 🔗 Enlaces

- YOLO v8: https://docs.ultralytics.com/
- Three.js: https://threejs.org/
- Chart.js: https://www.chartjs.org/
- python-osc: https://pypi.org/project/python-osc/
