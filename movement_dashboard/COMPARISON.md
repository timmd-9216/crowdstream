# Comparación: `dance_dashboard` vs `movement_dashboard`

Este documento resume las diferencias entre las dos implementaciones del dashboard de movimiento.

## Visión general

| Componente                  | `dance_dashboard` (original)                | `movement_dashboard` (FastAPI)                 |
|-----------------------------|--------------------------------------------|------------------------------------------------|
| Framework web               | Flask + Flask-SocketIO (WSGI)               | FastAPI + Uvicorn (ASGI)                       |
| Transporte tiempo real      | Socket.IO                                   | WebSocket nativo                               |
| Servidor OSC                | `pythonosc.ThreadingOSCUDPServer` dentro de un hilo (sin captura de errores) | Mismo servidor OSC pero con captura explícita del bind y mensaje amigable |
| Plantillas/estáticos        | Jinja vía Flask (`url_for('static', ...)`)  | Jinja2 de FastAPI (`url_for('static', path=...)`)|
| Puertos por defecto         | OSC 5005 / HTTP 8081                        | OSC 5005 / HTTP 8082                           |
| Script de inicio            | `start.sh` + `start-all-services.sh` (antes lanzaba esta versión) | `movement_dashboard/start.sh` y ahora `start-all-services.sh` lanza esta versión |

## Backend

### Original (`dance_dashboard/src/dashboard_server.py`)
- Clase `DashboardServer` combina Flask, Socket.IO y el receptor OSC.
- Cada handler OSC actualiza `self.current_data` y emite inmediatamente un evento `update` por Socket.IO (previo throttle).
- El botón de reinicio invoca `reset_stats` como evento Socket.IO para limpiar acumulados y reenviar el snapshot.

### Alternativa (`movement_dashboard/src/server.py`)
- Usa una clase `DashboardState` que es thread-safe y expone snapshots.
- FastAPI sirve `/` con la misma plantilla y expone `/api/current` + `/ws` para WebSockets.
- Reseteos llegan como mensajes JSON `{"action":"reset"}` por el mismo socket y se retransmiten a todos los clientes.
- Captura `OSError` al levantar el servidor OSC y muestra `RuntimeError: No se pudo abrir el puerto OSC ...` si el puerto está ocupado.

## Frontend

### Original (`dance_dashboard/static/js/dashboard.js`)
- Cliente Socket.IO (`io({ transports: ['websocket'] ... })`).
- Eventos: `update`, `stats_reset`, `reset_stats` con callback de confirmación.
- Charts con Chart.js y actualizaciones en tiempo real.

### Alternativa (`movement_dashboard/static/js/dashboard.js`)
- Conexión `WebSocket` nativa (`ws://host/ws`).
- Los mensajes se envían como JSON con campo `type` (`update`).
- El botón “Reiniciar” envía `{ action: 'reset' }` y se apoya en el broadcast inmediato del servidor.

## Integración con scripts

- `start-all-services.sh` ahora arranca `movement_dashboard/src/server.py` (HTTP 8082) y deja el registro en `logs/movement_dashboard.log`. Antes lanzaba el dashboard original en 8081.
- Para iniciar manualmente:
  - Original: `cd dance_dashboard && ./start.sh`
  - Alternativa: `cd movement_dashboard && ./start.sh --osc-port 5005 --web-port 8082`

## Recomendaciones

- Usar `movement_dashboard` cuando se prefiera FastAPI/ASGI o WebSockets nativos.
- Mantener `dance_dashboard` si se necesita compatibilidad con Socket.IO u otros servicios ya integrados.
