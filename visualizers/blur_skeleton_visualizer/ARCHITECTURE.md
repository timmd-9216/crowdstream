# Blur Skeleton Visualizer - Arquitectura

## Cambio Arquitectural (Noviembre 2024)

### Problema Original

El `blur_skeleton_visualizer` tenía un conflicto de recursos con el `dance_movement_detector`:

**Arquitectura anterior (problemática):**
```
┌─────────────────────┐         ┌──────────────────────┐
│  Detector           │         │  Blur Visualizer     │
│                     │         │                      │
│  ✓ Abre cámara (0)  │         │  ✓ Abre cámara (0)   │
│  ✓ Procesa con YOLO │         │  ✓ Recibe OSC        │
│  ✓ Envía OSC        │──OSC──→ │  ✗ Conflicto!        │
│                     │         │                      │
└─────────────────────┘         └──────────────────────┘
```

**Síntomas:**
- Error: `RuntimeError: Cannot open video source: 0`
- Error: `Camera index out of range`
- Funcionaba con `cosmic_journey` (no abre cámara) pero fallaba con `blur_skeleton`

### Solución Implementada

Blur ahora es **autónomo** - hace su propia detección YOLO y no depende del detector externo:

**Arquitectura nueva (correcta):**
```
┌─────────────────────┐         ┌──────────────────────┐
│  Detector           │         │  Blur Visualizer     │
│                     │         │                      │
│  ✓ Abre cámara (0)  │         │  ✓ Abre cámara (0)   │
│  ✓ Procesa con YOLO │         │  ✓ Procesa con YOLO  │
│  ✓ Envía OSC        │         │  ✓ Autónomo          │
│  │                  │         │  ✓ Sin conflicto     │
│  └──→ otros visuals │         │                      │
│      (cosmic, etc)  │         └──────────────────────┘
└─────────────────────┘
```

### Cambios Realizados

1. **Agregado YOLO al blur**:
   - Importa `ultralytics.YOLO`
   - Carga modelo `yolov8n-pose.pt` en `__init__`
   - Procesa frames directamente

2. **Cálculo de movimiento interno**:
   - Método `_calculate_movement()`
   - Tracking de pose history
   - Cálculo de movimiento head/arms/legs

3. **Independencia del detector**:
   - No necesita OSC del detector
   - Abre su propia cámara sin conflicto
   - Puede funcionar completamente solo

4. **Dependencias actualizadas**:
   ```
   ultralytics>=8.0.0  # Agregado
   ```

### Uso

El blur ahora puede usarse de dos formas:

**Opción 1: Solo blur (recomendado)**
```bash
cd blur_skeleton_visualizer
./install.sh
./start_blur.sh
```

**Opción 2: Con detector (para otros visualizadores)**
```bash
./scripts/start-all-services.sh --visualizer cosmic_journey
# El detector alimenta cosmic_journey
# Blur funciona independiente en otro puerto
```

### Puertos

- **Blur**: Puerto web 8092, OSC 5009
- **Detector**: OSC múltiple (5005-5009)

Ambos pueden correr simultáneamente sin conflicto porque blur es autónomo.

### Beneficios

✅ No hay conflicto de cámara
✅ Blur funciona independiente
✅ Más simple de debuggear
✅ Puede funcionar sin detector
✅ Menor latencia (procesamiento directo)

### Desventajas

❌ Duplicación de lógica YOLO
❌ Usa más recursos si ambos corren
❌ Dos procesos accediendo hardware

### Futuro

Si se desea compartir una única fuente de video, considerar:
- Streaming de frames vía OSC/WebRTC
- Servicio de cámara centralizado
- Pipeline de video compartido
