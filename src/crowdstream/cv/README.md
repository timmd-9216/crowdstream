# Directorios

Los directorios `data` y `models` contienen los datos y modelos necesarios para la ejecución de los scripts. Los mismos se encuentran ignorados por `git` y deben ser descargados manualmente.

El directorio `data` debe contener los siguientes subdirectorios:
* `raw`: Videos crudos originales
* `standarized`: Videos preprocesados para ajustar su tamaño.
* `pickles`: Archivos pickles con resultados de procesamiento.

Los videos de demo usados se pueden descargar de [demo data](https://drive.google.com/drive/u/4/folders/1GMU_CvWpG4gZym7t1xUWhN_kysXQBIrD).

El directorio `models` contiene el modelo de estimación de pose utilizado. En caso de correr el script `video_processing.py` o `webcam_processing.py` se descargará automáticamente.