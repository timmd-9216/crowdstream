# Signal Containers

Este submodulo contiene dos contenedores de señales, `DiffSignalContainer` y `PoseSignalContainer`.

El primero en `diff_sinal.py` es un contenedor de señales de diferencias entre frames de video. El segundo en `pose_signal.py` es un contenedor de señales de poses humanas. Cada contenedor contiene una señal (serie) y un método de update para actualizarla cada frame.