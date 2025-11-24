# crowdstream

![Dashboard example 1](./dance_dashboard_alt/dance_dashboard_example_1.png)
![Dashboard example 2](./dance_dashboard_alt/dance_dashboard_example_2.png)

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

El detector siempre se ejecuta. Debes elegir un visualizador y opcionalmente el dashboard:

```bash
# Solo detector y visualizador
./start-all-services.sh --visualizer cosmic_skeleton

# Con dashboard
./start-all-services.sh --dashboard --visualizer cosmic_skeleton

# Otros visualizadores disponibles
./start-all-services.sh --visualizer cosmic_journey
./start-all-services.sh --visualizer space_visualizer
./start-all-services.sh --visualizer blur_skeleton
```

### Opciones disponibles

- `--dashboard`: Inicia el dashboard FastAPI (opcional)
- `--visualizer`: Selecciona el visualizador (requerido)
  - `cosmic_skeleton`: Visualizador de esqueletos
  - `cosmic_journey`: Visualizador cosmic journey
  - `space_visualizer`: Visualizador espacial
  - `blur_skeleton`: Video borroso con líneas de esqueleto intensas (puerto 8092)

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