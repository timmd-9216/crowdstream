# Flask-SocketIO on Jetson TX1 - Threading Mode

## Issue

Jetson TX1 has an old GCC compiler that doesn't support C++11, which is required by `greenlet` (dependency of `eventlet` and `gevent`).

**Error:**
```
error: 'noexcept' does not name a type
note: C++11 'noexcept' only available with -std=c++11 or -std=gnu++11
```

## Solution

Use `threading` mode instead of `eventlet` or `gevent` for Flask-SocketIO.

### Code Changes Required

In your Flask-SocketIO server files, explicitly set `async_mode='threading'`:

**Example** (`cosmic_journey/src/cosmic_server.py`):

```python
from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)

# IMPORTANT: Use threading mode on Jetson TX1
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8091)
```

## Performance Considerations

### Threading vs Eventlet

| Feature | Threading | Eventlet/Gevent |
|---------|-----------|-----------------|
| **Concurrency** | Real threads (OS-level) | Green threads (userspace) |
| **Performance** | Good for I/O-bound | Better for many connections |
| **CPU Usage** | Higher overhead | Lower overhead |
| **Max Connections** | ~100-500 | ~10,000+ |
| **Jetson TX1 Support** | ✅ Works | ❌ Fails to compile |

### Why Threading is Fine for Jetson TX1

1. **Limited Resources**: Jetson TX1 won't handle thousands of connections anyway
2. **I/O Bound**: OSC and camera processing are I/O-bound, not CPU-bound
3. **Simplicity**: No compilation issues, pure Python
4. **Sufficient**: For 2-10 concurrent clients, threading is perfect

## Requirements.txt

Remove these packages:
```
# eventlet  # Requires greenlet (C++11)
# gevent    # Requires greenlet (C++11)
# dnspython # Only needed for eventlet
```

Keep these:
```
flask==1.1.4
flask-socketio==4.3.2
python-socketio==4.6.1
python-engineio==3.14.2
werkzeug==1.0.1
markupsafe==1.1.1
jinja2==2.11.3
itsdangerous==1.1.0
click==7.1.2
six==1.16.0
```

## Testing

### Check Async Mode

```python
from flask_socketio import SocketIO
print(SocketIO().async_mode)  # Should print: 'threading'
```

### Performance Test

```bash
# Terminal 1: Start server
python cosmic_server.py

# Terminal 2: Test concurrent connections
for i in {1..10}; do
    curl http://localhost:8091 &
done
wait
```

## Alternative Solutions (Not Recommended)

### 1. Install Newer GCC (Complex)

```bash
# Would require building GCC 5+ from source
# Not worth it for minimal performance gain
```

### 2. Use Pre-compiled Wheels (Not Available)

```bash
# No ARM64 wheels for greenlet on Python 3.5
pip install greenlet  # Will fail
```

### 3. Cross-compile (Overkill)

```bash
# Would need to set up cross-compilation toolchain
# Too complex for this use case
```

## Conclusion

**Use `async_mode='threading'`** for Flask-SocketIO on Jetson TX1. It's simple, works reliably, and provides sufficient performance for typical use cases.

## Code Example: Minimal Working Server

```python
#!/usr/bin/env python3
# cosmic_server.py

from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('response', {'data': 'Connected', 'mode': socketio.async_mode})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    print(f"Starting Flask-SocketIO in {socketio.async_mode} mode")
    socketio.run(app, host='0.0.0.0', port=8091, debug=False)
```

This will work perfectly on Jetson TX1 without any compilation issues.
