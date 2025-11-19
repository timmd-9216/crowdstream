# Sistema de Mapeo Configurable

El visualizador espacial ahora soporta configuración de mapeo vía JSON, permitiendo cambiar qué movimientos controlan qué efectos visuales sin modificar código.

## Archivo de Configuración

Ubicación: `space_visualizer/config/mapping.json`

### Estructura Básica

```json
{
  "mappings": {
    "nombre_parametro": {
      "source": "arm_movement",
      "min_input": 0,
      "max_input": 80,
      "min_output": 0.5,
      "max_output": 10.0,
      "description": "Descripción del efecto"
    }
  }
}
```

## Parámetros Disponibles

### Fuentes de Datos (sources)
- `arm_movement` - Movimiento de brazos
- `leg_movement` - Movimiento de piernas
- `head_movement` - Movimiento de cabeza
- `total_movement` - Movimiento total del cuerpo
- `person_count` - Número de personas detectadas
- `average` - Promedio de múltiples fuentes (requiere campo `sources: []`)

### Efectos Visuales (parámetros)
- `speed` - Velocidad de viaje espacial
- `star_size` - Tamaño de las estrellas
- `rotation_speed` - Velocidad de rotación de cámara
- `color_intensity` - Intensidad de colores
- `warp_factor` - Intensidad del efecto warp
- `particle_count` - Cantidad de estrellas
- `nebula_intensity` - Opacidad de nebulosas

## Ejemplos de Configuración

### Mapeo por Defecto (Actual)
```json
{
  "mappings": {
    "speed": {
      "source": "arm_movement",
      "min_input": 0,
      "max_input": 80,
      "min_output": 0.5,
      "max_output": 10.0
    },
    "star_size": {
      "source": "head_movement",
      "min_input": 0,
      "max_input": 60,
      "min_output": 1.0,
      "max_output": 4.0
    }
  }
}
```

### Mapeo Alternativo 1: Todo por Movimiento Total
```json
{
  "mappings": {
    "speed": {
      "source": "total_movement",
      "min_input": 0,
      "max_input": 100,
      "min_output": 1.0,
      "max_output": 8.0
    },
    "star_size": {
      "source": "total_movement",
      "min_input": 0,
      "max_input": 100,
      "min_output": 1.0,
      "max_output": 3.0
    },
    "rotation_speed": {
      "source": "total_movement",
      "min_input": 0,
      "max_input": 100,
      "min_output": 0.0,
      "max_output": 2.0
    }
  }
}
```

### Mapeo Alternativo 2: Piernas=Velocidad, Brazos=Tamaño
```json
{
  "mappings": {
    "speed": {
      "source": "leg_movement",
      "min_input": 0,
      "max_input": 100,
      "min_output": 0.5,
      "max_output": 12.0
    },
    "star_size": {
      "source": "arm_movement",
      "min_input": 0,
      "max_input": 80,
      "min_output": 0.5,
      "max_output": 5.0
    },
    "rotation_speed": {
      "source": "head_movement",
      "min_input": 0,
      "max_input": 60,
      "min_output": 0.0,
      "max_output": 4.0
    }
  }
}
```

### Ejemplo con Promedio de Múltiples Fuentes
```json
{
  "mappings": {
    "nebula_intensity": {
      "source": "average",
      "sources": ["arm_movement", "leg_movement", "head_movement"],
      "min_input": 0,
      "max_input": 80,
      "min_output": 0.0,
      "max_output": 1.0
    }
  }
}
```

## Uso

### Modo por Defecto
```bash
cd space_visualizer
./start.sh --osc-port 5006
```
Usa `config/mapping.json` automáticamente.

### Con Archivo Personalizado
```bash
cd space_visualizer
python3 src/visualizer_server.py --osc-port 5006 --mapping config/mi_mapeo.json
```

## Crear Nuevos Mapeos

1. **Copiar el archivo base:**
```bash
cd space_visualizer/config
cp mapping.json mi_mapeo_custom.json
```

2. **Editar el JSON:**
```bash
nano mi_mapeo_custom.json
```

3. **Modificar los mapeos:**
   - Cambiar el `source` para usar diferentes movimientos
   - Ajustar `min_input` y `max_input` según intensidad deseada
   - Ajustar `min_output` y `max_output` para el rango del efecto

4. **Iniciar con tu mapeo:**
```bash
python3 src/visualizer_server.py --osc-port 5006 --mapping config/mi_mapeo_custom.json
```

## Tips de Configuración

### Velocidad más Rápida
Aumenta `max_output`:
```json
"speed": {
  "max_output": 15.0  // Más rápido (default: 10.0)
}
```

### Más Sensibilidad
Reduce `max_input`:
```json
"star_size": {
  "max_input": 40  // Más sensible (default: 60)
}
```

### Invertir Efecto
Invierte min/max output:
```json
"rotation_speed": {
  "min_output": 3.0,
  "max_output": 0.0  // Invertido
}
```

### Más Estrellas
Ajusta multiplicador de particle_count:
```json
"particle_count": {
  "source": "person_count",
  "base": 1000,      // Base más alta
  "multiplier": 800, // Más por persona
  "max_output": 8000 // Límite más alto
}
```

## Validación

El sistema valida automáticamente:
- ✅ Si el archivo existe, lo carga
- ✅ Si falla, usa mapeo por defecto
- ✅ Muestra mensaje en consola indicando qué mapeo está usando

## Troubleshooting

### "Using defaults" en consola
- Verifica que el archivo existe en `config/`
- Revisa sintaxis JSON (usa un validador online)
- Verifica permisos de lectura del archivo

### Efectos no funcionan como esperado
- Revisa los rangos `min_input` / `max_input`
- Verifica que el `source` sea válido
- Chequea que los valores estén en rangos razonables

### Cambios no se aplican
- Reinicia el visualizador después de editar el JSON
- Verifica que estés pasando el archivo correcto con `--mapping`
