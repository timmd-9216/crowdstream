# 🌌 Cosmic Journey - Guía Rápida

## Inicio Rápido

```bash
cd cosmic_journey
./start_cosmic.sh
```

Luego abre en tu navegador: **http://localhost:8091**

## Características Únicas

Este visualizador presenta un estilo visual completamente diferente al Space Journey original:

### Efectos Visuales

1. **Galaxia Espiral** 🌀
   - 3 brazos espirales con 9000 partículas
   - Rotación controlada por movimiento de piernas
   - Colores que van de azul (centro) a púrpura (bordes)

2. **Campo de Asteroides** ☄️
   - 200 asteroides rocosos en órbita
   - Velocidad controlada por movimiento de brazos
   - Rotación individual realista

3. **Nebulosas Cósmicas** ☁️
   - 5 nebulosas de colores (púrpura, cyan, magenta, azul, rosa)
   - Densidad controlada por movimiento total
   - Efecto de pulsación suave

4. **Planetas Orbitales** 🪐
   - 4 planetas con diferentes tamaños y colores
   - Algunos con anillos
   - Velocidad orbital controlada por brazos+piernas

5. **Campo de Energía** ⚡
   - Esfera envolvente con shader personalizado
   - Intensidad controlada por movimiento total
   - Efecto de brillo dinámico

6. **Zoom Cósmico** 🔭
   - Acercamiento/alejamiento de cámara
   - Controlado por movimiento de cabeza
   - Transición suave

## Mapeo de Movimientos

| Parte del Cuerpo | Parámetro Visual | Rango |
|------------------|------------------|-------|
| **Piernas** | Rotación de galaxia | 0.0 - 3.0 rad/s |
| **Brazos** | Velocidad asteroides | 0.5 - 10.0x |
| **Cabeza** | Zoom cósmico | 0.5x - 3.0x |
| **Total** | Energía cósmica | 0% - 100% |
| **Total** | Densidad nebulosa | 0% - 100% |
| **Total** | Brillo estrellas | 20% - 100% |
| **Brazos+Piernas** | Órbita planetas | 0.0 - 2.0x |

## Puertos y Configuración

- **Puerto OSC**: 5007 (recibe datos del detector)
- **Puerto Web**: 8091 (interfaz web)
- **WebSocket**: Socket.IO en el mismo puerto web

## Comparación con Space Journey

| Característica | Space Journey | Cosmic Journey |
|----------------|---------------|----------------|
| Estilo | Túnel estelar de viaje | Galaxia y cosmos |
| Estrellas | Campo de estrellas lineales | Galaxia espiral |
| Objetos | Planetas y nebulosas | Asteroides y planetas orbitales |
| Efecto principal | Warp drive | Campo de energía |
| Color dominante | Azul/cyan | Púrpura/magenta |
| Cámara | Movimiento hacia adelante | Zoom dinámico |

## Controles de Interfaz

- **Pantalla Completa**: Botón en panel UI
- **Ocultar UI**: Ocultar/mostrar panel de estadísticas
- **F11**: Pantalla completa del navegador (alternativa)

## Tecnología

- **Renderizado**: Three.js r128
- **Partículas**: ~9200 partículas de galaxia + 200 asteroides
- **Shaders**: GLSL custom para campo de energía
- **Física**: Movimiento orbital de planetas
- **Comunicación**: WebSocket en tiempo real

## Solución de Problemas

### El visualizador no recibe datos

1. Verifica que el detector esté ejecutándose
2. Confirma que el puerto 5007 esté en `multi_destination.json`
3. Reinicia el detector para aplicar los cambios

```bash
# Ver configuración actual
cat ../dance_movement_detector/config/multi_destination.json
```

### El servidor no inicia

```bash
# Verificar dependencias
venv/bin/pip install -r requirements.txt

# Verificar puerto disponible
lsof -i :8091
```

### Rendimiento lento

- Reduce el número de asteroides en `cosmic.js` (línea 138)
- Reduce partículas de galaxia (línea 103)
- Desactiva el campo de energía temporalmente

## Personalización

### Cambiar colores de la galaxia

Edita `static/js/cosmic.js` líneas 116-119

### Agregar más planetas

Modifica el array `planetData` en `cosmic.js` línea 201

### Ajustar sensibilidad

Modifica los multiplicadores en `cosmic_server.py` líneas 122-143

## Próximas Mejoras

- [ ] Múltiples galaxias basadas en número de personas
- [ ] Cometas con estelas
- [ ] Agujeros negros
- [ ] Modo VR
- [ ] Grabación de sesiones
