# Raspberry Pi 4 - Guía de Instalación

Este documento explica cómo ejecutar el sistema en Raspberry Pi 4.

## Requisitos

- Raspberry Pi 4 (4GB o 8GB RAM recomendado)
- Raspberry Pi OS (64-bit recomendado)
- MicroSD de 32GB o más
- Python 3.9+


Troubleshooting:
* Revisar alimentación
* Cable usb-c preferiblemente corto (más largos pueden traer problemas de alimentación)


## ⚠️ Limitaciones Importantes

### El Detector NO funcionará bien en RPi 4:

**YOLO v8 requiere mucha potencia de procesamiento:**
- En RPi 4: ~1-3 FPS (muy lento para tiempo real)
- En laptop/PC con GPU: 30-60 FPS

**Solución recomendada**: Ejecutar el detector en otra máquina más potente.

## Arquitectura Recomendada

```
┌─────────────────────┐
│  Laptop/PC          │
│  (Detector YOLO)    │
│                     │
│  Envía OSC →        │
└─────────────────────┘
           ↓
    (Red local)
           ↓
┌─────────────────────┐
│  Raspberry Pi 4     │
│  - Dashboard        │
│  - Visualizer       │
│  - Controller       │
└─────────────────────┘
```

## Instalación en Raspberry Pi 4

### 1. Preparar el sistema

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias
sudo apt install -y python3-pip python3-venv git

# Opcional: Aumentar swap (si tienes 4GB RAM)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Cambiar CONF_SWAPSIZE=100 a CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### 2. Clonar/copiar el proyecto

```bash
cd ~
# Copiar los archivos del proyecto a la RPi
# (puedes usar rsync, scp, o git)

cd crowdstream
```

### 3. Configuración para RPi

Crear configuración optimizada sin detector:

```bash
cd service_controller
cp config/services.json config/services_rpi.json
```

Editar `config/services_rpi.json`:

```json
{
  "services": [
    {
      "name": "dashboard",
      "directory": "dance_dashboard",
      "command": "./start.sh --osc-port 5005",
      "description": "Dashboard de estadísticas",
      "port": 8080,
      "auto_restart": false,
      "enabled": true
    },
    {
      "name": "visualizer",
      "directory": "space_visualizer",
      "command": "./start.sh --osc-port 5005",
      "description": "Visualizador espacial 3D",
      "port": 8090,
      "auto_restart": false,
      "enabled": true
    }
  ]
}
```

### 4. Iniciar servicios

```bash
cd ~/crowdstream/service_controller
./start.sh --config config/services_rpi.json
```

Abre en navegador (en la misma red):
```
http://RASPBERRY_PI_IP:8000
```

## Configuración del Detector (en otra máquina)

En tu laptop/PC con más potencia:

```bash
cd dance_movement_detector

# Encontrar IP de la Raspberry Pi
# En la RPi ejecuta: hostname -I

# Iniciar detector enviando OSC a la RPi
./start.sh --osc-host 192.168.1.XXX --osc-port 5005
```

## Acceso desde Otros Dispositivos

Todos los servicios escuchan en `0.0.0.0`, así que puedes acceder desde cualquier dispositivo en la red:

```
Dashboard:   http://RASPBERRY_PI_IP:8080
Visualizer:  http://RASPBERRY_PI_IP:8090
Controller:  http://RASPBERRY_PI_IP:8000
```

## Optimización para Raspberry Pi

### Reducir uso de memoria

1. **Dashboard** - Reducir historial:
```bash
./start.sh --history 50  # En vez de 100
```

2. **Visualizer** - Navegador optimizado:
- Usa Chromium (viene con RPi OS)
- Activa aceleración por hardware:
  ```bash
  # En Chromium, ir a: chrome://flags
  # Habilitar: "Override software rendering list"
  ```

### Mejorar rendimiento web

Editar `/boot/config.txt`:
```bash
sudo nano /boot/config.txt

# Agregar al final:
gpu_mem=256  # Más memoria para GPU (VideoCore)
```

Reiniciar:
```bash
sudo reboot
```

## Autostart (Opcional)

Para que los servicios inicien automáticamente al arrancar la RPi:

### Usando systemd

Crear servicio:
```bash
sudo nano /etc/systemd/system/dance-controller.service
```

Contenido:
```ini
[Unit]
Description=Dance Movement Service Controller
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/crowdstream/service_controller
ExecStart=/home/pi/crowdstream/service_controller/start.sh --config config/services_rpi.json
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Habilitar:
```bash
sudo systemctl daemon-reload
sudo systemctl enable dance-controller
sudo systemctl start dance-controller

# Ver estado
sudo systemctl status dance-controller

# Ver logs
sudo journalctl -u dance-controller -f
```

## Rendimiento Esperado

### En Raspberry Pi 4 (4GB):

| Servicio    | CPU   | RAM   | Rendimiento |
|-------------|-------|-------|-------------|
| Dashboard   | 5-10% | 100MB | ✅ Excelente |
| Visualizer  | 5-15% | 150MB | ✅ Excelente |
| Controller  | 2-5%  | 80MB  | ✅ Excelente |
| **TOTAL**   | ~25%  | ~330MB| ✅ **Viable** |

### Si intentas correr el Detector:

| Servicio    | CPU    | RAM   | Rendimiento |
|-------------|--------|-------|-------------|
| Detector    | 95-99% | 1.5GB | ❌ 1-3 FPS  |

**Conclusión**: RPi 4 es perfecta para dashboard y visualizer, pero NO para el detector YOLO.

## Troubleshooting

### Error "ImportError: libGL.so.1"

```bash
sudo apt install -y libgl1-mesa-glx
```

### Error de memoria

```bash
# Cerrar aplicaciones innecesarias
# Aumentar swap (ver paso 1)
```

### Visualizer se ve lento en navegador

```bash
# Reducir partículas en space_visualizer/src/visualizer_server.py
# Línea ~91-92:
self.state.particle_count = 500 + (self.state.person_count * 200)  # era 500
self.state.particle_count = min(self.state.particle_count, 2000)   # era 5000
```

### No puedo acceder desde otro dispositivo

```bash
# Verificar firewall
sudo ufw allow 8000
sudo ufw allow 8080
sudo ufw allow 8090
sudo ufw allow 5005/udp  # OSC

# Verificar IP
hostname -I
```

## Modo "Solo Detector" (Experimental)

Si realmente quieres probar el detector en RPi 4:

1. Usa modelo más pequeño:
```python
# En dance_movement_detector/src/dance_movement_detector.py línea 177
self.model = YOLO('yolov8n-pose.pt')  # Ya es el más pequeño
```

2. Reduce resolución de video:
```python
# Agregar después de línea 209 en _detection_loop()
frame = cv2.resize(frame, (320, 240))  # Muy baja resolución
```

3. Procesa cada N frames:
```python
# En _detection_loop(), agregar:
if frame_count % 3 != 0:  # Procesar 1 de cada 3 frames
    continue
```

**Resultado esperado**: ~3-5 FPS (todavía lento, pero semi-funcional)

## Recomendación Final

**Setup ideal**:
- **Raspberry Pi 4**: Dashboard + Visualizer + Controller
- **Laptop/PC**: Detector YOLO
- **Conexión**: Red local WiFi/Ethernet
- **Display**: TV/proyector conectado a la RPi vía HDMI mostrando el visualizer

**Ventajas**:
- Todo corre fluido
- RPi puede quedar fija en la instalación
- Laptop móvil con la cámara

## Recursos

- [Raspberry Pi OS Download](https://www.raspberrypi.com/software/)
- [Python on Raspberry Pi](https://www.raspberrypi.com/documentation/computers/os.html#python)
- [Remote Access](https://www.raspberrypi.com/documentation/computers/remote-access.html)
