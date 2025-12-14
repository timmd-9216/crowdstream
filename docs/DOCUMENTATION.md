# CrowdStream - Documentación Técnica Completa

## Índice
1. [Descripción General](#descripción-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Módulo de Computer Vision](#módulo-de-computer-vision)
4. [Módulo de Música](#módulo-de-música)
5. [Configuración e Instalación](#configuración-e-instalación)
6. [Uso de los Módulos](#uso-de-los-módulos)
7. [Testing](#testing)
8. [Dependencias](#dependencias)
9. [Mejoras Propuestas](#mejoras-propuestas)

## Descripción General

CrowdStream es una plataforma integral de procesamiento multimedia que combina análisis de video en tiempo real con procesamiento avanzado de audio musical. El proyecto integra técnicas de computer vision para detección de movimiento humano y un pipeline completo de procesamiento musical con inteligencia artificial.

### Propósito
- **Análisis de Movimiento**: Detección y análisis de poses humanas en tiempo real
- **Procesamiento Musical**: Pipeline completo para separación de stems, análisis musical y reproducción interactiva
- **Aplicaciones Multimedia**: Herramientas para DJs, productores musicales y aplicaciones de streaming inteligente

## Arquitectura del Sistema

```
crowdstream/
├── src/crowdstream/
│   ├── cv/                     # Módulo Computer Vision
│   │   ├── data_helpers/       # Utilidades para datos de video
│   │   ├── processing/         # Pipeline de procesamiento CV
│   │   ├── signal/            # Contenedores de señales y operaciones
│   │   └── utils/             # Utilidades generales CV
│   └── music/                 # Módulo Música
│       ├── dataset-build/     # Pipeline construcción datasets
│       ├── GCP-jobs/         # Jobs en Google Cloud Platform
│       └── sc-engine/        # Motor SuperCollider tiempo real
├── tests/                    # Suite de tests
├── notebooks/               # Jupyter notebooks para análisis
└── requirements.txt         # Dependencias del proyecto
```

## Módulo de Computer Vision

### Componentes Principales

#### 1. Contenedores de Señales

**PoseSignalContainer** (`signal/pose_signal.py`)
- Gestiona tracking de poses humanas usando YOLO
- Rastrea hasta 17 puntos clave del cuerpo humano
- Calcula señales de movimiento basadas en distancias euclidianas
- Soporte para múltiples personas con persistencia de ID

**DiffSignalContainer** (`signal/diff_signal.py`)
- Calcula diferencias pixel-nivel entre frames consecutivos
- Genera señales agregadas sumando diferencias absolutas
- Alternativa ligera a la estimación de poses

#### 2. Pipeline de Procesamiento

**Funciones Principales:**
- `video_processing()`: Procesa videos pregrabados
- `webcam_processing()`: Análisis en tiempo real con visualización
- `process_results()`: Post-procesamiento de resultados YOLO

#### 3. Operaciones Matriciales (`signal/matrix_ops.py`)

- `get_idxs_and_kps_from_result()`: Extrae IDs de personas y keypoints
- `create_new_keypoints_matrix()`: Convierte datos sparse a matrices estructuradas
- `calculate_distance_matrix()`: Calcula distancias euclidianas entre keypoints
- `extend_keypoints_matrix()`: Maneja dimensiones de matrices dinámicamente

#### 4. Utilidades de Datos

- `download_video()`: Descarga videos de YouTube usando yt-dlp
- `stanzarize_video()`: Estandariza videos a resolución 1280x720

### Flujo de Datos CV

1. **Captura de Video**: OpenCV captura frames de webcam o archivo
2. **Inferencia YOLO**: Modelo YOLOv8n-pose detecta humanos y extrae 17 keypoints
3. **Tracking de ID**: Mantiene identidad de personas entre frames
4. **Operaciones Matriciales**: Convierte keypoints a matrices estructuradas
5. **Cálculo de Distancias**: Distancias euclidianas entre keypoints correspondientes
6. **Generación de Señales**: Agrega datos de movimiento en señales escalares
7. **Visualización**: Plotting en tiempo real y video anotado

## Módulo de Música

### Pipeline de Construcción de Datasets

#### Etapa 1: Descarga de Samples de Spotify
- Utiliza Spotify Web API con autenticación OAuth2
- Descarga previews de 30 segundos con metadatos completos
- Organiza samples por artista en formato MP3

#### Etapa 2: Integración Rekordbox
- Extrae BPM, tonalidades y análisis de frases
- Exporta metadatos de colección como XML

#### Etapa 3: Separación de Audio (Spleeter)
- Implementa Spleeter de Deezer para separación de stems
- Separa tracks en 4-5 stems: vocals, drums, bass, piano, other
- Soporte para procesamiento local, Docker y GCP

#### Etapa 4: Consolidación de Metadatos
- Combina metadatos de Spotify con análisis de Rekordbox
- Valida completitud de generación de stems
- Crea base de datos resumen de tracks

#### Etapa 5: Segmentación de Audio
- Extrae loops musicales de 48 beats
- Implementa crossfading y looping sin costuras
- Crea segmentos sincronizados por BPM

#### Etapa 6: Creación de Dataset Final
- Genera metadatos CSV con relaciones de tonalidad armónica
- Crea algoritmos de playlist inteligente
- Produce espectrogramas para aplicaciones ML

### Servicios en la Nube

#### Google Cloud Platform Jobs
- **Spleeter GCP**: Procesamiento containerizado con integración GCS
- **Drum Separation**: Separación avanzada usando Facebook Demucs

#### Motor de Audio en Tiempo Real
- **SuperCollider Engine**: Mixing en tiempo real y control de stems
- **Interface Python OSC**: Comunicación Python-SuperCollider
- **API de Control**: `/play_sound`, `/set_volume`, `/stop_sound`

### Extracción de Características MIR
- **MFCC**: Coeficientes Cepstrales Mel-frequency
- **Análisis Espectral**: Centroide spectral y loudness
- **Detección de Tempo y Tonalidad**
- **Agregación de Features** para aplicaciones ML

## Configuración e Instalación

### Requisitos del Sistema
- Python 3.8+
- OpenCV
- YOLO models (se descargan automáticamente)
- SuperCollider (para funciones de audio en tiempo real)

### Instalación

```bash
# Clonar repositorio
git clone [repository_url]
cd crowdstream

# Instalar dependencias
pip install -r requirements.txt

# Instalar proyecto en modo desarrollo
pip install -e .
```

### Variables de Entorno
Crear archivo `.env` en el directorio raíz:

```bash
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
```

## Uso de los Módulos

### Computer Vision

#### Análisis de Webcam en Tiempo Real
```python
from crowdstream.cv.processing.webcam_processing import webcam_processing

# Procesamiento con poses
webcam_processing(signal_container_type="pose")

# Procesamiento con diferencias de frame
webcam_processing(signal_container_type="diff")
```

#### Procesamiento de Video
```python
from crowdstream.cv.processing.video_processing import video_processing

# Procesar video pregrabado
signals = video_processing("path/to/video.mp4", "pose")
```

### Módulo de Música

#### Pipeline Completo de Dataset
```python
# Ejecutar pipeline completo
from crowdstream.music.dataset_build import pipeline_orchestration

# Configurar y ejecutar pipeline
pipeline_orchestration.run_complete_pipeline()
```

#### Control de Stems en Tiempo Real
```python
from crowdstream.music.sc_engine.examples import StemController

controller = StemController()
controller.play_stem("vocals", volume=0.8)
controller.set_volume("drums", 0.5)
```

## Testing

### Estructura de Tests
```
tests/
├── test_cv/
│   ├── test_matrix_ops.py
│   └── test_signal_container.py
```

### Ejecutar Tests
```bash
pytest tests/
```

## Dependencias

### Computer Vision
- **ultralytics**: Modelos YOLO para pose estimation
- **opencv-python**: Procesamiento de video y captura
- **matplotlib**: Visualización en tiempo real
- **numpy**: Operaciones matriciales

### Procesamiento de Audio
- **spotipy**: Cliente API de Spotify
- **pydub**: Manipulación de archivos de audio
- **librosa**: Análisis avanzado de audio
- **spleeter**: Separación de stems con IA

### Orchestración y Cloud
- **dagster**: Orchestración de pipelines de datos
- **google-cloud-storage**: Almacenamiento distribuido
- **docker**: Containerización para environments reproducibles

### Visualización y Análisis
- **pandas**: Manipulación de datos estructurados
- **plotly**: Visualizaciones interactivas
- **attrs**: Definición de clases con decoradores

## Mejoras Propuestas

### Computer Vision
1. **Optimización de Performance**
   - Implementar procesamiento multi-thread para YOLO inference
   - Cache de modelos YOLO para startup más rápido
   - Optimización de memoria para señales largas

2. **Funcionalidades Avanzadas**
   - Detección de gestos específicos
   - Análisis de emociones faciales
   - Tracking de objetos además de personas

3. **Robustez**
   - Mejor handling de lighting conditions
   - Mejora en tracking de IDs entre frames
   - Validación de integridad de keypoints

### Módulo de Música
1. **Escalabilidad**
   - Implementar processing distribuido con Celery
   - Optimizar batch processing para grandes datasets
   - Caching inteligente de resultados de Spleeter

2. **Calidad de Audio**
   - Integrar modelos más avanzados como DEMUCS
   - Implementar noise reduction en stems
   - Mejora en algoritmos de crossfading

3. **Funcionalidades IA**
   - Clasificación automática de géneros
   - Generación de playlists con ML
   - Análisis de similaridad musical avanzado

### Arquitectura General
1. **Configuración**
   - Sistema de configuración centralizado (YAML/TOML)
   - Variables de entorno más completas
   - Profiles de configuración por ambiente

2. **Monitoring y Logging**
   - Sistema de logging estructurado
   - Métricas de performance en tiempo real
   - Health checks para componentes

3. **Documentación**
   - API documentation con Sphinx
   - Tutoriales interactivos
   - Ejemplos de uso más extensivos

4. **Testing**
   - Cobertura de tests más amplia
   - Tests de integración end-to-end
   - Tests de performance y benchmarking

5. **DevOps**
   - CI/CD pipeline completo
   - Docker Compose para desarrollo local
   - Deployment automatizado a diferentes environments

## Conclusión

CrowdStream representa una plataforma multimedia robusta que combina técnicas avanzadas de computer vision con procesamiento inteligente de audio musical. La arquitectura modular permite extensibilidad y mantenimiento eficiente, mientras que la integración con servicios cloud proporciona escalabilidad para aplicaciones de producción.

El sistema está diseñado para soportar aplicaciones en tiempo real así como procesamiento batch de grandes datasets, lo que lo hace adecuado tanto para investigación académica como para aplicaciones comerciales en la industria musical y multimedia.