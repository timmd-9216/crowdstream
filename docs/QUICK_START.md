# Quick Start Guide

Guía rápida para iniciar y gestionar todos los servicios del sistema de detección de movimiento de bailarines.

## Scripts Disponibles

### 🟢 Iniciar Todos los Servicios
```bash
./start-all-services.sh
```
Inicia detector, dashboard y visualizador automáticamente con la configuración correcta de puertos.

### 🔴 Detener Todos los Servicios
```bash
./kill-all-services.sh
```
Detiene todos los servicios corriendo (detector, dashboard, visualizador, controlador).

### 📋 Ver Logs
```bash
tail -f logs/dashboard.log
tail -f logs/visualizer.log
tail -f logs/detector.log
```

## Configuración Inicial

### Opción 1: Script Automatizado (RECOMENDADO)

**Inicio rápido en 1 comando:**
```bash
./start-all-services.sh
```

Esto automáticamente:
- Detiene servicios previos
- Inicia Dashboard en puerto OSC 5005, web 8081
- Inicia Visualizer en puerto OSC 5006, web 8090
- Inicia Detector enviando a ambos puertos
- Crea logs en `logs/`

**Abrir interfaces:**
- Dashboard: http://localhost:8081
- Visualizer: http://localhost:8090

**Para detener:**
```bash
./kill-all-services.sh
```

### Opción 2: Inicio Manual (3 terminales)

**Terminal 1 - Dashboard**
```bash
cd dance_dashboard
./start.sh --web-port 8081 --osc-port 5005
```
Abre: http://localhost:8081

**Terminal 2 - Visualizador Espacial**
```bash
cd space_visualizer
./start.sh --osc-port 5006 --web-port 8090
```
Abre: http://localhost:8090

**Terminal 3 - Detector de Movimiento**
```bash
cd dance_movement_detector
python3 src/dance_movement_detector.py --config config/multi_destination.json
```

### Opción 2: Controlador de Servicios (1 terminal)

**Iniciar el controlador:**
```bash
cd service_controller
./start.sh
```
Abre: http://localhost:8000

Luego desde el navegador:
1. Click en "▶️ Iniciar Todos"
2. Espera que todos estén en estado "Ejecutando"
3. Abre las otras interfaces:
   - Dashboard: http://localhost:8080
   - Visualizer: http://localhost:8090

**Nota:** El controlador necesita configuración adicional para multi-destino OSC.

## Mapeo de Puertos

| Servicio | Puerto OSC | Puerto Web |
|----------|-----------|------------|
| Dashboard | 5005 | 8081 |
| Visualizer | 5006 | 8090 |
| Controller | - | 8000 |
| Detector | Envía a 5005 + 5006 | - |

## Configuración de Mapeo Visual

El visualizador soporta mapeo configurable de movimientos a efectos:

**Ver configuración actual:**
```bash
cat space_visualizer/config/mapping.json
```

**Usar mapeo personalizado:**
```bash
cd space_visualizer
python3 src/visualizer_server.py \
  --osc-port 5006 \
  --mapping config/mi_mapeo.json
```

Ver [MAPPING_CONFIG.md](MAPPING_CONFIG.md) para detalles completos.

## Mapeo Actual (Default)

- 🙌 **Brazos** → Velocidad de viaje espacial
- 🗣️ **Cabeza** → Tamaño de estrellas
- 🦵 **Piernas** → Rotación de cámara
- 💃 **Movimiento Total** → Intensidad de color y warp drive
- 👥 **Personas** → Densidad de estrellas

## Troubleshooting

### Error "Address already in use"

```bash
# Detener todos los servicios
./kill-all-services.sh

# Ver qué está usando los puertos
lsof -i:5005
lsof -i:5006
lsof -i:8080
lsof -i:8090
```

### El detector no envía datos

**Verificar configuración multi-destino:**
```bash
cat dance_movement_detector/config/multi_destination.json
```

Debe incluir:
```json
{
  "osc_destinations": [
    {"host": "127.0.0.1", "port": 5005},
    {"host": "127.0.0.1", "port": 5006}
  ]
}
```

### Dashboard o Visualizer no reciben datos

1. Verifica que el detector esté corriendo
2. Chequea que los puertos OSC coincidan
3. Revisa logs del detector para ver si envía mensajes
4. Verifica la conexión WebSocket (indicador en UI)

### Problemas de rendimiento

**En sistemas lentos:**

1. Reduce intervalo de mensajes:
```bash
# En multi_destination.json
"message_interval": 1.0  # Cambiar a 2.0 o 5.0
```

2. Reduce número de estrellas:
```bash
# En mapping.json
"particle_count": {
  "max_output": 3000  # Reducir de 5000
}
```

## Comandos Útiles

### Ver procesos corriendo
```bash
ps aux | grep -E "(dashboard|visualizer|detector|controller)" | grep -v grep
```

### Ver puertos en uso
```bash
lsof -i -P | grep -E "5005|5006|8000|8080|8081|8090" | grep LISTEN
```

### Matar un servicio específico
```bash
# Dashboard
pkill -f dashboard_server.py

# Visualizer
pkill -f visualizer_server.py

# Detector
pkill -f dance_movement_detector.py

# Controller
pkill -f service_manager.py
```

### Ver logs en tiempo real
```bash
# Si corriste con start.sh, los logs están en la terminal
# Para capturar logs:
cd dance_movement_detector
python3 src/dance_movement_detector.py --config config/multi_destination.json 2>&1 | tee detector.log
```

## Flujo de Datos

```
📹 Cámara
    ↓
🤖 Detector YOLO
    ↓
📡 OSC Messages
    ├─→ 5005 → 📊 Dashboard (8081)
    └─→ 5006 → 🌌 Visualizer (8090)
```

## Setup para Presentación

### Configuración Recomendada

1. **Una laptop/PC con GPU** (detector)
2. **Raspberry Pi o segunda PC** (dashboard + visualizer)
3. **Proyector/TV** conectado a RPi mostrando visualizer

### Conexión de Red

**En la laptop (detector):**
```bash
# Editar multi_destination.json
{
  "osc_destinations": [
    {"host": "192.168.1.XXX", "port": 5005},  # IP de la RPi
    {"host": "192.168.1.XXX", "port": 5006}
  ]
}
```

**En la Raspberry Pi:**
```bash
# Terminal 1
./start.sh --osc-port 5005

# Terminal 2
cd ../space_visualizer
./start.sh --osc-port 5006
```

## Personalización Rápida

### Cambiar intervalo de mensajes
```bash
# Editar dance_movement_detector/config/multi_destination.json
"message_interval": 1.0  # Segundos entre mensajes (default: 10)
```

### Cambiar mapeo de movimientos
```bash
# Editar space_visualizer/config/mapping.json
# Ver MAPPING_CONFIG.md para ejemplos
```

### Cambiar colores/efectos
```bash
# Editar space_visualizer/static/js/space_visualizer.js
# Líneas 89-99: Colores de estrellas
# Líneas 128-142: Colores de nebulosas
```

## Recursos

- [RASPBERRY_PI_SETUP.md](RASPBERRY_PI_SETUP.md) - Setup en Raspberry Pi
- [MAPPING_CONFIG.md](MAPPING_CONFIG.md) - Configuración de mapeo visual
- READMEs individuales en cada directorio de servicio
