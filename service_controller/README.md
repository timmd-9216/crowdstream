# Service Controller

Sistema de control remoto web para gestionar todos los servicios del proyecto de detección de movimiento de bailarines. Permite iniciar, detener, reiniciar y monitorear servicios desde una interfaz web centralizada.

## Características

- **Control remoto** de todos los servicios vía web
- **Monitoreo en tiempo real**:
  - Estado del servicio (corriendo, detenido, error)
  - CPU y memoria utilizados
  - Tiempo de actividad (uptime)
  - PID del proceso
- **Gestión individual**:
  - Iniciar servicio
  - Detener servicio
  - Reiniciar servicio
  - Ver logs en tiempo real
- **Gestión grupal**:
  - Iniciar todos los servicios
  - Detener todos los servicios
- **Actualización automática** vía WebSockets
- **Interfaz moderna** y responsive

## Servicios Gestionados

1. **Dashboard** - Dashboard FastAPI (OSC: 5005, Web: 8082)
2. **Visualizer** - Visualizador espacial 3D (OSC: 5006, Web: 8090)
3. **Detector** - Dance Movement Detector (envía a ambos puertos OSC)

## Instalación

```bash
cd service_controller
./start.sh
```

El script automáticamente:
1. Crea un entorno virtual
2. Instala todas las dependencias (Flask, SocketIO, psutil)
3. Inicia el controlador

## Uso

### Iniciar el controlador

```bash
cd service_controller
./start.sh
```

Luego abre tu navegador en: http://localhost:8000

### Opciones de configuración

```bash
# Usar puerto diferente
./start.sh --port 9000

# Usar archivo de configuración diferente
./start.sh --config custom_services.json

# Especificar directorio base diferente
./start.sh --base-dir /path/to/services
```

## Interfaz Web

### Panel Principal

El panel principal muestra una tarjeta por cada servicio con:

- **Nombre y descripción** del servicio
- **Estado actual**: Detenido, Iniciando, Ejecutando, Deteniendo, Error
- **Estadísticas**:
  - Puerto del servicio
  - PID del proceso
  - Tiempo activo
  - Uso de CPU y RAM
- **Mensajes de error** (si aplica)
- **Botones de acción**:
  - ▶️ Iniciar
  - ⏹️ Detener
  - 🔄 Reiniciar
  - 📋 Ver Logs

### Acciones Globales

En el header hay botones para:
- **▶️ Iniciar Todos**: Inicia todos los servicios habilitados
- **⏹️ Detener Todos**: Detiene todos los servicios en ejecución

### Visualizador de Logs

Click en "📋 Logs" para ver los logs de un servicio en tiempo real. Los logs muestran:
- Últimas 100 líneas de salida
- Timestamp de cada línea
- Actualización en tiempo real

## Configuración de Servicios

Edita `config/services.json` para agregar o modificar servicios:

```json
{
  "services": [
    {
      "name": "dashboard",
      "directory": "dance_dashboard_alt",
      "command": "venv/bin/python3 src/server.py --osc-port 5005 --web-port 8082",
      "description": "Dashboard FastAPI (OSC: 5005, Web: 8082)",
      "port": 8082,
      "auto_restart": false,
      "enabled": true,
      "monitor_ports": [5005, 8082]
    },
    {
      "name": "visualizer",
      "directory": "visualizers/space_visualizer",
      "command": "venv/bin/python3 src/visualizer_server.py --osc-port 5006 --web-port 8090",
      "description": "Visualizador espacial 3D (OSC: 5006, Web: 8090)",
      "port": 8090,
      "auto_restart": false,
      "enabled": true,
      "monitor_ports": [5006, 8090]
    },
    {
      "name": "detector",
      "directory": "dance_movement_detector",
      "command": "venv/bin/python3 src/dance_movement_detector.py --config config/multi_destination.json",
      "description": "Detector de movimiento con YOLO (envía a Dashboard y Visualizer)",
      "port": 0,
      "auto_restart": false,
      "enabled": true
    }
  ]
}
```

### Parámetros de configuración

- `name`: Identificador único del servicio
- `directory`: Directorio relativo al base-dir
- `command`: Comando para iniciar el servicio
- `description`: Descripción mostrada en la UI
- `port`: Puerto en el que escucha el servicio (0 si no aplica)
- `auto_restart`: Reiniciar automáticamente si se cae (default: false)
- `enabled`: Si el servicio está habilitado (default: true)
- `monitor_ports`: Lista de puertos (TCP o UDP) a monitorear para detectar instancias externas (incluye el puerto principal por defecto)

## Arquitectura

```
Navegador Web
    ↑
    | HTTP REST API + WebSocket
    ↓
Service Controller (Flask)
    ↓
    | subprocess + psutil
    ↓
Servicios (detector, dashboard, visualizer)
```

### Componentes

1. **Backend (service_manager.py)**:
   - ServiceManager: Gestiona procesos con subprocess
   - ServiceConfig: Configuración de servicios
   - ServiceStatus: Estado y métricas de servicios
   - ControllerApp: API REST y WebSocket

2. **Frontend**:
   - HTML: Interfaz de usuario
   - CSS: Estilos modernos con tema oscuro
   - JavaScript: Cliente WebSocket y gestión de UI

3. **Configuración**:
   - services.json: Definición de servicios

## API REST

### Endpoints disponibles

```
GET  /                              - Interfaz web
GET  /api/services                  - Lista de servicios y estados
POST /api/service/<name>/start      - Iniciar servicio
POST /api/service/<name>/stop       - Detener servicio
POST /api/service/<name>/restart    - Reiniciar servicio
GET  /api/service/<name>/logs       - Obtener logs del servicio
POST /api/start-all                 - Iniciar todos los servicios
POST /api/stop-all                  - Detener todos los servicios
```

### WebSocket Events

```
connect              - Cliente conectado
disconnect           - Cliente desconectado
status_update        - Actualización de estados (cada 2 segundos)
```

## Monitoreo

El sistema monitorea continuamente:

- **Estado del proceso**: Verifica si el proceso sigue vivo
- **Uso de recursos**: CPU y memoria con psutil
- **Logs**: Captura stdout/stderr de cada servicio
- **Tiempo de actividad**: Calcula uptime desde el inicio
- **Auto-restart**: Reinicia servicios configurados si se caen

## Estructura de Archivos

```
service_controller/
├── src/
│   └── service_manager.py      # Backend principal
├── templates/
│   └── controller.html         # Interfaz web
├── static/
│   ├── css/
│   │   └── controller.css      # Estilos
│   └── js/
│       └── controller.js       # Cliente WebSocket
├── config/
│   └── services.json           # Configuración de servicios
├── requirements.txt
├── start.sh
└── README.md
```

## Casos de Uso

### Iniciar todo el sistema

1. Abre http://localhost:8000
2. Click en "▶️ Iniciar Todos"
3. Espera a que todos los servicios estén en estado "Ejecutando"
4. Abre las interfaces individuales:
   - Dashboard: http://localhost:8082
   - Visualizer: http://localhost:8090

### Depurar un servicio

1. Si un servicio está en estado "Error"
2. Click en "📋 Logs" para ver el error
3. Click en "🔄 Reiniciar" para intentar nuevamente
4. Si persiste, detén todos y reinicia el sistema

### Apagar el sistema

1. Click en "⏹️ Detener Todos"
2. Espera a que todos estén en estado "Detenido"
3. Cierra el navegador
4. Ctrl+C en la terminal del controller

## Troubleshooting

### Los servicios no inician

1. Verifica que los scripts `start.sh` de cada servicio sean ejecutables:
   ```bash
   chmod +x dance_movement_detector/start.sh
   chmod +x dance_dashboard/start.sh
   chmod +x visualizers/space_visualizer/start.sh
   ```

2. Verifica que las rutas en `config/services.json` sean correctas

3. Revisa los logs del servicio para ver el error específico

### El controller no puede detener un servicio

1. El controller usa SIGTERM primero, luego SIGKILL
2. Si un proceso está colgado, espera 5 segundos antes de forzar
3. En último caso, usa el comando `kill` manualmente:
   ```bash
   kill -9 <PID>
   ```

### Los logs no se actualizan

1. Verifica la conexión WebSocket (indicador verde en header)
2. Recarga la página
3. Click en "🔄 Actualizar" en el modal de logs

### Uso alto de memoria

El controller mantiene los últimos 100 logs por servicio en memoria. Si esto es un problema, edita `src/service_manager.py` línea ~277:

```python
if len(logs) > 50:  # Reducir de 100 a 50
    logs.pop(0)
```

## Acceso Remoto

Para acceder al controller desde otro dispositivo en la red:

1. Encuentra tu IP local:
   ```bash
   ifconfig | grep "inet " | grep -v 127.0.0.1
   ```

2. El controller ya escucha en `0.0.0.0`, así que puedes acceder desde:
   ```
   http://TU_IP:8000
   ```

3. Ejemplo: `http://192.168.1.100:8000`

**Nota de seguridad**: No expongas el controller a Internet sin autenticación.

## Extensión Futura

Ideas para mejorar el controller:

- [ ] Autenticación de usuarios
- [ ] Historial de eventos (inicio/parada/errores)
- [ ] Gráficos de uso de recursos
- [ ] Notificaciones cuando un servicio se cae
- [ ] Backup/restore de configuración
- [ ] Programación de inicio/parada automática
- [ ] Gestión de configuración de servicios desde UI
- [ ] Exportar logs a archivo

## Dependencias

- Flask: Framework web
- Flask-SocketIO: WebSockets en tiempo real
- psutil: Monitoreo de procesos y recursos
- eventlet: Servidor WSGI asíncrono

## Contribuir

Para agregar un nuevo servicio:

1. Edita `config/services.json`
2. Agrega una entrada con la configuración del servicio
3. Asegúrate de que el comando de inicio funcione
4. Reinicia el controller
5. El nuevo servicio aparecerá en la UI

## Licencia

Parte del proyecto Dance Movement Detection System
