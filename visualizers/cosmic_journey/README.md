# Cosmic Journey Visualizer

Visualizador espacial alternativo con una estética cósmica diferente. Presenta galaxias espirales, campos de asteroides, nebulosas y planetas orbitales.

## Características

- **Galaxia Espiral**: Rotación controlada por movimiento de piernas
- **Campo de Asteroides**: Velocidad controlada por movimiento de brazos
- **Zoom Cósmico**: Controlado por movimiento de cabeza
- **Nebulosas**: Densidad controlada por movimiento total
- **Campo de Energía**: Intensidad controlada por movimiento total
- **Planetas Orbitales**: Velocidad orbital controlada por combinación de brazos y piernas

## Instalación

```bash
# Crear entorno virtual e instalar dependencias
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

## Uso

### Inicio Rápido
```bash
./start_cosmic.sh
```

### Inicio Manual
```bash
venv/bin/python3 src/cosmic_server.py --osc-port 5007 --web-port 8091
```

### Parámetros
- `--osc-port`: Puerto para recibir mensajes OSC (por defecto: 5007)
- `--web-port`: Puerto del servidor web (por defecto: 8091)

## Acceso

Abre tu navegador en: http://localhost:8091

## Mapeo de Movimientos

| Movimiento | Efecto Visual |
|------------|---------------|
| Piernas | Rotación de la galaxia |
| Brazos | Velocidad de los asteroides |
| Cabeza | Zoom cósmico |
| Total | Energía y densidad de nebulosas |

## Controles

- **Pantalla Completa**: Botón en el panel de interfaz
- **Ocultar UI**: Ocultar/mostrar panel de información

## Configuración OSC

Para enviar datos desde el detector de movimiento, agrega este destino a `dance_movement_detector/config/multi_destination.json`:

```json
{
  "host": "127.0.0.1",
  "port": 5007,
  "description": "Cosmic Journey"
}
```

## Tecnologías

- **Backend**: Flask + Flask-SocketIO + python-osc
- **Frontend**: Three.js para renderizado 3D
- **Comunicación**: WebSockets para actualizaciones en tiempo real
