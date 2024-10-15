# Paso a paso para construir un Dataset

    * Recolectar IDs de artistas de spotify
    * Agregar IDs en dict archivos: 
        self.artist_catalogue = @ 1_spotify_30sec_samples_download.py 

## 0: Instalar dependencias

    $ pip install -r requirements.txt

## 0: Credenciales Spotify

Generar credenciales en la página de Spotify y exportarlas para que esten disponibles en la sesión

    export SPOTIPY_CLIENT_ID=""
    export SPOTIPY_CLIENT_SECRET=""

## 1: Bajar samples de Spotify por artista 

    $ python 1_spotify_30sec_samples_download.py 

* Baja archivos .mp3 en sample_audio/[Artist]
* Genera metadata en track_data/[Artist]/[SpotifyId].json

## 2: Procesar metadata con Rekordbox

    $ python 2_build_rekordbox_xml.py

* Open Rekordbox
* Select files & Import to Collection (BPM/Key/Phrase)
* File/Export Collection in xml format
    
## 3: Separar en stems con Spleeter

    $ python 3_spleeter_processing.py 

Para cada archivo mp3, extrar:
    * Vocals
    * drums
    * bass
    * piano
    * other separation (track original - 4stemsDetectados)

Opciones: manual/docker/gcp-job

WARNING: Spleeter problems with M1/M2/M3 chips

    Copiar archivos a bucket GCP:
         gsutil -m cp -R "sample_audio/" gs://[bucket-name]/input/
        
(exceute processing job)

    $ gsutil -m cp -R gs://[bucketname]/output .

# 4: Genera tempo y track metadata
WARNING: lower/upper bpm hardcodeados

    $ python 4_tempo_tracka_metadata_gen.py


# 5: Adds tracks metadata with spotify API

    $ 5_adds-tracks-metadata.py

# 6: Segment audios (by BPM)

Check stems_location='output/'

    $ python 6_segment.py

# 7: Genera el archivo final con metadata

    $ python 7_audio_processor_build_final_metadata_file.py

Salida: loops_metadata.csv

# 8:

Abrir SonicPi

Ajustar paths de

Archivos segmentados para cada stem:
    solenoids = ".../sample_audio/loops/"

Metadata:
    loops = CSV.parse( "../loops_metadata.csv )

