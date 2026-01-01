# Space Journey Visualizer

Visualización 3D en tiempo real de un viaje espacial controlado por movimiento de bailarines. Usa Three.js para crear una experiencia inmersiva con estrellas, planetas y nebulosas que reaccionan a los datos de movimiento recibidos vía OSC.

## Características

- **Viaje espacial 3D** con Three.js
- **Control en tiempo real** basado en movimiento:
  - Movimiento total → Velocidad de viaje
  - Brazos → Intensidad de color
  - Piernas → Efecto warp drive
  - Cabeza → Rotación de cámara
  - Cantidad de personas → Densidad de estrellas
- **Efectos visuales**:
  - Campo de estrellas dinámico (500-5000 partículas)
  - Planetas con efecto glow
  - Nebulosas de colores
  - Efecto warp cuando hay movimiento de piernas
- **Interfaz interactiva**:
  - Panel de estadísticas en tiempo real
  - Modo pantalla completa
  - Ocultar/mostrar UI
  - Overlay de instrucciones

## Instalación

```bash
cd space_visualizer
./start.sh
```

El script automáticamente:
1. Crea un entorno virtual
2. Instala todas las dependencias
3. Inicia el servidor

## Uso

### Modo básico
```bash
./start.sh
```

Luego abre tu navegador en: http://localhost:8090

### Cambiar puertos
```bash
# Escuchar OSC en puerto diferente
./start.sh --osc-port 7000

# Usar puerto web diferente
./start.sh --web-port 9090
```

## Uso Completo del Sistema

### Setup con 3 aplicaciones

**Terminal 1 - Detector de Movimiento:**
```bash
cd dance_movement_detector
./start.sh
```

**Terminal 2 - Dashboard (opcional):**
```bash
cd dance_dashboard
./start.sh
```

**Terminal 3 - Visualizador Espacial:**
```bash
cd space_visualizer
./start.sh
```

**Navegador:**
- Visualizador: http://localhost:8090
- Dashboard: http://localhost:8080 (si está corriendo)

## Mapeo de Movimiento a Visual

### Velocidad de Viaje
- **Fuente**: Movimiento total del cuerpo
- **Efecto**: Velocidad de desplazamiento por el espacio
- **Rango**: 0.5x a 5.0x velocidad base
- **Visual**: Estrellas se mueven más rápido hacia la cámara

### Intensidad de Color
- **Fuente**: Movimiento de brazos
- **Efecto**: Vibrancia de colores de estrellas y planetas
- **Rango**: 20% a 100% intensidad
- **Visual**: Estrellas y planetas brillan más

### Warp Drive
- **Fuente**: Movimiento de piernas
- **Efecto**: Efecto de estiramiento tipo "warp speed"
- **Rango**: 0% a 100%
- **Visual**: Las estrellas se estiran creando líneas de luz

### Rotación de Cámara
- **Fuente**: Movimiento de cabeza
- **Efecto**: Rotación orbital de la cámara
- **Rango**: -2.0 a 2.0 radianes/segundo
- **Visual**: La vista espacial gira suavemente

### Densidad de Estrellas
- **Fuente**: Cantidad de personas detectadas
- **Efecto**: Número de estrellas visibles
- **Rango**: 500 a 5000 partículas
- **Visual**: Más bailarines = más estrellas en el cielo

### Nebulosas
- **Fuente**: Promedio de todos los movimientos
- **Efecto**: Opacidad de nubes de nebulosa
- **Rango**: 0% a 30% opacidad
- **Visual**: Nubes coloridas aparecen con más movimiento

## Controles en el Navegador

- **Pantalla Completa**: Click en el botón "⛶ Pantalla Completa"
- **Ocultar UI**: Click en "🔘 Ocultar UI" para vista limpia
- **Comenzar**: Click en "Comenzar el Viaje" en la pantalla inicial

## Configuración Técnica

### Puertos por defecto
- **OSC**: 5005
- **Web**: 8090

### Requisitos del sistema
- Navegador moderno con soporte WebGL
- GPU recomendada para mejor rendimiento
- Resolución mínima: 1024x768

### Optimización de rendimiento

Para mejor rendimiento en sistemas más lentos, edita `src/visualizer_server.py` y ajusta los límites:

```python
# Línea ~91-92: Reducir máximo de partículas
self.state.particle_count = 500 + (self.state.person_count * 300)  # era 500
self.state.particle_count = min(self.state.particle_count, 3000)   # era 5000
```

## Arquitectura

```
Cliente Web (Three.js)
    ↑
    | WebSocket (Socket.IO)
    ↓
Servidor Flask
    ↑
    | OSC Messages
    ↓
Detector de Movimiento
```

## Mensajes OSC Recibidos

El visualizador espera estos mensajes OSC:

- `/dance/person_count` (int)
- `/dance/total_movement` (float)
- `/dance/arm_movement` (float)
- `/dance/leg_movement` (float)
- `/dance/head_movement` (float)

## Estructura de Archivos

```
space_visualizer/
├── src/
│   └── visualizer_server.py    # Servidor Flask + OSC
├── templates/
│   └── visualizer.html         # Template HTML
├── static/
│   ├── css/
│   │   └── visualizer.css      # Estilos
│   └── js/
│       └── space_visualizer.js # Three.js + WebSocket client
├── requirements.txt
├── start.sh
└── README.md
```

## Desarrollo

### Dependencias principales
- Flask: Framework web
- Flask-SocketIO: WebSockets en tiempo real
- python-osc: Recepción de mensajes OSC
- Three.js: Motor 3D (CDN)

### Personalizar la visualización

Edita `static/js/space_visualizer.js` para:
- Cambiar colores de estrellas (línea ~60-80)
- Ajustar velocidad base (línea ~200)
- Modificar efectos de nebulosa (línea ~340-360)
- Cambiar distribución de planetas (línea ~110-130)

## Troubleshooting

### El visualizador no recibe datos
1. Verifica que el detector esté corriendo
2. Verifica que ambos usen el mismo puerto OSC (default: 5005)
3. Chequea la consola del navegador (F12)

### Rendimiento bajo
1. Cierra otras pestañas del navegador
2. Reduce el número máximo de partículas (ver Optimización)
3. Usa pantalla completa para mejor experiencia
4. Verifica que tu navegador tenga aceleración de hardware activada

### Pantalla negra
1. Verifica que tu navegador soporte WebGL: https://get.webgl.org/
2. Actualiza los drivers de tu GPU
3. Revisa la consola del navegador para errores

### Las estrellas no se mueven
1. Verifica que estés recibiendo mensajes OSC
2. Chequea el panel de estadísticas (debe mostrar valores > 0)
3. Intenta reiniciar el detector

## Tips para Presentaciones

- Usa modo pantalla completa para mejor inmersión
- Oculta el UI para proyecciones públicas
- Conecta a un proyector o pantalla grande
- Ajusta el brillo de la sala para mejor efecto
- El efecto warp se ve mejor con movimiento intenso de piernas

## Ideas para Extensión

- Agregar más tipos de objetos espaciales (asteroides, cometas)
- Sincronizar colores con análisis de audio
- Crear diferentes "modos" de viaje (galaxia, nebulosa, agujero negro)
- Agregar trails/estelas a las estrellas
- Implementar cambios de escena basados en energía

## Créditos

Visualización creada con:
- Three.js - Motor 3D
- Socket.IO - Comunicación en tiempo real
- Flask - Servidor web
- python-osc - Protocolo OSC
