# Processing Scripts

Estos módulos contienen funciones que permiten usar los distintos contenedores de señales para procesar videos y webcams. 

* `video_processing.py` contiene funciones para procesar videos con un modelo de pose y guarda los resultados en archivos pickle.
* `webcam_processing.py` contiene funciones para procesar webcams en tiempo real con el contenedor de señal (pose o diff) mostrando los resultados en la pantalla.
* `results_processing.py` contiene funciones para cargar los archivos pickle generados por `video_processing.py` y procesar los mismos usando cualquiera de los contendores de señal.