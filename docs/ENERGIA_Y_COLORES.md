# Separacion de energia por partes del cuerpo y colores

Documento conceptual basado en la documentacion existente del proyecto (`README.md`, `README_SISTEMA_COMPLETO.md`, `space_visualizer/README.md`, `cosmic_journey/QUICK_START.md`, `dance_movement_detector/README.md`, `skeleton_visualizer/README.md`).

## Fuentes de datos de energia
- El detector (`dance_movement_detector/`) calcula movimiento separado para piernas, brazos y cabeza, ademas del movimiento total y la cantidad de personas, y los publica por OSC (`/dance/leg_movement`, `/dance/arm_movement`, `/dance/head_movement`, `/dance/total_movement`, `/dance/person_count`).
- Valores tipicos: movimiento moderado 10-50, energetico 50-150+, minimo <10 (segun `dance_movement_detector/README.md`).
- Los destinos habituales son dashboard (puerto 5005) y visualizadores (5006/5007), configurados en `config/multi_destination.json`.

## Uso actual en visualizadores
- `space_visualizer`: mapea brazos a intensidad de color, piernas a efecto warp drive, cabeza a rotacion de camara y movimiento total a intensidad general de color y warp (ver README). La densidad de estrellas depende de la cantidad de personas.
- `cosmic_journey`: usa piernas para rotacion de galaxia, brazos para velocidad de asteroides, cabeza para zoom y movimiento total para energia/densidad de nebulosas y brillo de estrellas.
- `skeleton_visualizer`: colorea por parte del cuerpo para diferenciar visualmente los segmentos del esqueleto: cabeza 🔴, torso 🔵, brazos 🟡, piernas 🟢. Aunque no escala por energia, provee la paleta base para separar las zonas.

## Propuesta conceptual de separacion de energia por colores
- **Piernas → Verde**: usa `leg_movement` para intensidad del canal verde y para activar efectos de velocidad (warp/rotacion). Verdes mas brillantes indican patadas/saltos, verdes tenues pasos suaves.
- **Brazos → Amarillo**: usa `arm_movement` para el canal amarillo (rojo+verde) y efectos de vibrancia. Golpes y ondas de brazos aumentan la saturacion amarilla de estrellas/nebulosas.
- **Cabeza → Rojo**: usa `head_movement` para el canal rojo y para influir en rotacion/zoom. Inclinaciones o movimientos rapidos de cabeza elevan la presencia roja en el fondo o en halos.
- **Movimiento total → Intensidad global**: escala la luminancia/general (ya usado en `space_visualizer` y `cosmic_journey`) como multiplicador comun, manteniendo las proporciones de cada canal de color por parte del cuerpo.
- **Personas → Densidad**: mantiene la logica existente (mas personas = mas particulas), sin cambiar la codificacion de color por parte.

## Flujo sugerido
1. Leer valores OSC y normalizarlos a 0-1 por tipo de movimiento (usar rangos actuales: brazos 0-80, piernas 0-100, cabeza 0-60 como referencias de `MAPPING_CONFIG.md` y visualizadores).
2. Asignar cada valor al canal de color definido arriba y calcular un color compuesto `rgb = (rojo_cabeza, amarillo_brazos, verde_piernas)` antes de aplicar el multiplicador de movimiento total.
3. Aplicar el color compuesto a los elementos visuales principales (estrellas, nebulosas, skeleton glow) y mantener efectos especificos existentes (warp con piernas, rotacion con cabeza, velocidad con brazos) para coherencia.
4. Usar la paleta del `skeleton_visualizer` como leyenda consistente entre UI/dashboard y visualizadores para que el publico identifique de inmediato que parte del cuerpo domina la energia en pantalla.

## Notas de implementacion
- Mantener rangos y mapeos configurables via `space_visualizer/config/mapping.json` para ajustar sensibilidad por venue.
- El dashboard puede sumar barras de color por parte del cuerpo usando la misma paleta, alineando la lectura con el visualizador.
- Evitar nuevas dependencias: el pipeline OSC existente ya entrega los valores separados necesarios.
