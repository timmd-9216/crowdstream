# Dance Dashboard (FastAPI)

Dashboard alternativo que muestra la misma información que el dashboard original
pero implementado con **FastAPI**, WebSockets nativos y Chart.js.

## Características

- Recepción de mensajes OSC en `/dance/*`
- Actualización en tiempo real vía WebSocket nativo (sin Socket.IO)
- Estadísticas actuales, acumuladas e historial de movimiento
- Botón de reinicio que sincroniza todos los clientes al instante

## Requisitos

- Python 3.9+
- Dependencias del archivo `requirements.txt`

## Uso

```bash
cd dance_dashboard_alt
./start.sh --osc-port 5005 --web-port 8082
```

Luego abre `http://localhost:8082` en el navegador.

## Estructura

```
dance_dashboard_alt/
├── requirements.txt
├── start.sh
├── src/
│   └── server.py           # Servidor FastAPI + OSC
├── static/
│   ├── css/dashboard.css   # Estilos
│   └── js/dashboard.js     # Cliente WebSocket + Charts
└── templates/
    └── dashboard.html      # Interfaz
```

## Configuración

- `--osc-port`: Puerto donde escucha mensajes OSC (default 5005)
- `--web-port`: Puerto HTTP/WebSocket (default 8082)
- `--history`: cantidad de puntos guardados para los gráficos (default 100)

## Diferencias vs. dashboard original

- Usa FastAPI + uvicorn en lugar de Flask + Flask-SocketIO
- Implementa WebSockets nativos (sin Socket.IO) para simplificar el cliente
- Código separado en `dance_dashboard_alt` para probar la nueva arquitectura sin
  tocar el dashboard existente
