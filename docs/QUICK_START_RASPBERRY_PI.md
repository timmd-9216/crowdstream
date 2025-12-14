# Quick Start Guide - Raspberry Pi

Guía rápida para configurar y optimizar crowdstream en Raspberry Pi 4.

---

## 🚀 Inicio Rápido (5 minutos)

### 1. Audio Server
```bash
cd ~/dev/crowdstream-audio
./losdones-start.sh
```

**Configuración**: 8 segundos de delay para arranque confiable.

**Opcional - Filtros optimizados** (34x más rápido):
```bash
# Instalar scipy
pip install scipy

# Arrancar con filtros optimizados
python audio_server.py --buffer-size 2048 --enable-filters --optimized-filters
```

---

### 2. Dance Movement Detector
```bash
cd ~/dev/crowdstream-audio/dance_movement_detector
./start_detector_rpi.sh
```

**Configuración por defecto**: 12-18 FPS, balanceado.

**Para máximo rendimiento** (20-25 FPS):
```bash
./start_detector_rpi.sh config/config_rpi_max_performance.json
```

---

### 3. Cosmic Skeleton Visualizer
```bash
cd ~/dev/crowdstream-audio/cosmic_skeleton
python app.py
```

Luego abre en el navegador: `http://localhost:5000`

---

## ⚙️ Configuraciones Disponibles

### Dance Movement Detector

| Comando | FPS | CPU | Uso |
|---------|-----|-----|-----|
| `./start_detector_rpi.sh config/config_rpi_max_performance.json` | 20-25 | 40-50% | Shows en vivo |
| `./start_detector_rpi.sh` (default) | 12-18 | 50-70% | Uso general ⭐ |
| `./start_detector_rpi.sh config/config.json` | 5-8 | 80-100% | Testing |

---

## 📁 Dónde Configurar Parámetros

### Máximo Rendimiento (`imgsz: 320`, `skip_frames: 2`)

Edita el archivo:
```bash
nano ~/dev/crowdstream-audio/dance_movement_detector/config/config_rpi_max_performance.json
```

O usa el archivo ya creado:
```bash
./start_detector_rpi.sh config/config_rpi_max_performance.json
```

**Ya configurado con**:
- `imgsz: 320` (imagen más pequeña = más rápido)
- `skip_frames: 2` (procesa 1 de cada 3 frames = 3x más rápido)
- `max_det: 3` (máximo 3 personas)
- `show_video: false` (sin display = -30% CPU)

---

## 🔥 Optimización Extrema (30+ FPS)

Si necesitas **aún más velocidad**:

```json
{
  "model": "yolov8n-pose.pt",
  "imgsz": 256,
  "skip_frames": 3,
  "camera_width": 640,
  "camera_height": 360,
  "conf_threshold": 0.5,
  "max_det": 2,
  "history_frames": 2,
  "show_video": false
}
```

Guárdalo como `config/config_rpi_extreme.json` y úsalo:
```bash
./start_detector_rpi.sh config/config_rpi_extreme.json
```

**Advertencia**: Calidad de detección muy baja.

---

## 🌡️ Monitoreo

### Temperatura
```bash
watch -n 2 vcgencmd measure_temp
```

**Rangos**:
- ✅ <70°C - Excelente
- ⚠️ 70-80°C - Bien (agregar ventilador recomendado)
- ❌ >80°C - Throttling (agregar ventilador URGENTE)

---

### CPU
```bash
htop
```

**Rangos esperados**:
- Max performance: 40-50%
- Balanced: 50-70%
- High quality: 80-100%

---

### FPS
El detector muestra FPS en consola. Observa los logs.

---

## 🛠️ Troubleshooting Rápido

### Audio no se escucha
```bash
# Verificar que el delay sea 8 segundos en losdones-start.sh
grep "sleep" losdones-start.sh
# Debe decir: sleep 8
```

### FPS muy bajo
```bash
# 1. Usar máximo rendimiento
./start_detector_rpi.sh config/config_rpi_max_performance.json

# 2. Verificar temperatura
vcgencmd measure_temp

# 3. Verificar throttling
vcgencmd get_throttled
# Debe ser: throttled=0x0
```

### Cámara no detectada
```bash
# Verificar cámara habilitada
vcgencmd get_camera
# Debe decir: supported=1 detected=1

# Si no, habilitar con:
sudo raspi-config
# Interface Options > Camera > Enable
```

### Solo se ve 1 esqueleto de 2 personas
Ya está arreglado en `cosmic_skeleton/static/js/cosmic.js`. Solo asegúrate de tener la última versión.

---

## 📚 Documentación Completa

- **[PERFORMANCE_OPTIMIZATIONS_INDEX.md](PERFORMANCE_OPTIMIZATIONS_INDEX.md)** - Índice completo
- **[dance_movement_detector/CONFIGURATION_GUIDE.md](dance_movement_detector/CONFIGURATION_GUIDE.md)** - Guía de configuración detallada
- **[dance_movement_detector/RASPBERRY_PI_OPTIMIZATION.md](dance_movement_detector/RASPBERRY_PI_OPTIMIZATION.md)** - Optimizaciones Raspberry Pi
- **[OPTIMIZATIONS_SUMMARY.md](OPTIMIZATIONS_SUMMARY.md)** - Resumen completo

---

## 🎯 Configuración Recomendada por Escenario

### Show en vivo con muchas personas
```bash
./start_detector_rpi.sh config/config_rpi_max_performance.json
```
**Razón**: Máxima velocidad (20-25 FPS), acepta menor precisión.

---

### Uso general / ensayos
```bash
./start_detector_rpi.sh
```
**Razón**: Balance perfecto (12-18 FPS), buena precisión.

---

### Testing / debugging
```bash
./start_detector_rpi.sh config/config.json
```
**Razón**: Máxima calidad, acepta menor velocidad (5-8 FPS).

---

## ✅ Checklist Pre-Show

- [ ] Temperatura <70°C en reposo
- [ ] `vcgencmd get_throttled` retorna `0x0`
- [ ] Audio server arranca sin errores
- [ ] Dance detector muestra 12+ FPS
- [ ] Visualizer muestra esqueletos correctamente
- [ ] OSC messages llegan al destino
- [ ] Ventilador funcionando (si está instalado)

---

## 💡 Tips Finales

1. **Siempre usa `show_video: false`** en Raspberry Pi headless (ahorra 30% CPU)
2. **Monitorea temperatura** durante los primeros 10 minutos
3. **Prueba configuraciones** antes del show
4. **Usa Ethernet** en lugar de WiFi si es posible
5. **Cierra procesos innecesarios** antes de arrancar

---

## 🚨 En Caso de Emergencia

### Audio se corta
```bash
# Aumentar buffer size
python audio_server.py --buffer-size 4096
```

### FPS cae dramáticamente
```bash
# Verificar temperatura
vcgencmd measure_temp

# Si >85°C, apagar inmediatamente y agregar cooling
sudo shutdown -h now
```

### Sistema muy lento
```bash
# Reiniciar Raspberry Pi
sudo reboot

# Después de reiniciar, verificar procesos
htop
# Matar procesos innecesarios
```

---

## 📞 Soporte

Si algo no funciona:

1. Verifica temperatura y throttling
2. Consulta [PERFORMANCE_OPTIMIZATIONS_INDEX.md](PERFORMANCE_OPTIMIZATIONS_INDEX.md)
3. Revisa los logs del servicio
4. Prueba con configuración de menor rendimiento

---

**¡Listo para el show! 🎉**
