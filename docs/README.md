# crowdstream

![Dashboard example 1](./dance_dashboard_alt/dance_dashboard_example_1.png)
![Dashboard example 2](./dance_dashboard_alt/dance_dashboard_example_2.png)

## Ver imagen del detector

Para ver la ventana del detector con la cámara en vivo mostrando las detecciones YOLO y el esqueleto:

1. Editar el archivo de configuración: `dance_movement_detector/config/multi_destination.json`
2. Cambiar `"show_video": false` a `"show_video": true` (línea 33)
3. Reiniciar los servicios:
   ```bash
   ./kill-all-services.sh
   ./start-all-services.sh --visualizer blur_skeleton
   ```

Esto abrirá una ventana OpenCV mostrando:
- Video de la cámara en tiempo real
- Detecciones YOLO sobre las personas
- Esqueleto dibujado con keypoints
- Valores de movimiento (cabeza, brazos, piernas)

**Nota:** Si obtienes el error `RuntimeError: Cannot open video source: 0`, verifica:
- La cámara no esté en uso por otra aplicación
- Tengas permisos para acceder a la cámara
- El índice de cámara sea correcto (prueba `"video_source": 1` si tienes múltiples cámaras)

## Instalación

### Opción 1: Instalación global del proyecto

Instalar los requerimientos del proyecto.

```bash
pip install -r requirements.txt
```

Instalar el proyecto en modo desarrollo.

```bash
pip install -e .
```

### Opción 2: Instalación de servicios individuales (Recomendado)

Crear entornos virtuales para todos los servicios:

```bash
./setup-all-venvs.sh
```

O instalar servicios individuales:

```bash
cd dance_dashboard_alt && ./install.sh
cd cosmic_skeleton && ./install.sh
cd cosmic_journey && ./install.sh
cd space_visualizer && ./install.sh
cd blur_skeleton_visualizer && ./install.sh
cd dance_movement_detector && ./install.sh
```

## Ejecutar servicios

### Iniciar todos los servicios

El dashboard se inicia por defecto. Debes elegir un visualizador:

```bash
# Dashboard + visualizador (recomendado)
./start-all-services.sh --visualizer cosmic_skeleton

# Sin dashboard
./start-all-services.sh --visualizer cosmic_skeleton --no-dashboard

# Otros visualizadores disponibles
./start-all-services.sh --visualizer cosmic_journey
./start-all-services.sh --visualizer space_visualizer
./start-all-services.sh --visualizer blur_skeleton
```

### Opciones disponibles

- `--visualizer`: Selecciona el visualizador (requerido)
  - `cosmic_skeleton`: Visualizador de esqueletos cósmico
  - `cosmic_journey`: Visualizador cosmic journey
  - `space_visualizer`: Visualizador espacial
  - `blur_skeleton`: **Autónomo** - Video borroso con líneas de esqueleto intensas (puerto 8092)
- `--no-dashboard`: Omite iniciar el dashboard (dashboard se inicia por defecto)

### Nota sobre blur_skeleton

**Blur es autónomo y no requiere el detector**. Hace su propia detección YOLO y puede funcionar completamente solo:

```bash
cd blur_skeleton_visualizer
./install.sh
./start_blur.sh
```

Ver [blur_skeleton_visualizer/ARCHITECTURE.md](blur_skeleton_visualizer/ARCHITECTURE.md) para más detalles sobre su arquitectura.

### Detener servicios

```bash
./kill-all-services.sh
```

### Ver logs

```bash
tail -f logs/detector.log
tail -f logs/skeleton.log      # o cosmic.log, space.log, blur.log
tail -f logs/dashboard_alt.log  # si usas --dashboard
```

### Notas importantes

- El detector no muestra ventana de video cuando se ejecuta con el script (configurado con `show_video: false` para reducir recursos)
- El visualizador `blur_skeleton` captura video directamente y lo procesa con efecto blur + overlay de esqueleto
- Los keypoints son enviados vía OSC desde el detector a todos los visualizadores configurados

## Variables de entorno

Setear manualmente o configurar archivo .env en el path de ejecución

Por ejemplo:
    SPOTIPY_CLIENT_ID=""
    SPOTIPY_CLIENT_SECRET=""