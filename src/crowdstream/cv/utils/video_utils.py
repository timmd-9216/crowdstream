import cv2


def video_summary(path_video: str) -> dict[str, float]:
    """
    Función que admite el path a un video y devuelve un resumen de características del mismo.
    """

    # Abre el video usando OpenCV
    cap = cv2.VideoCapture(path_video)

    # Verifica si el video se abrió correctamente
    if not cap.isOpened():
        raise ValueError(f"No se puede abrir el video en {path_video}")

    # Obtener ancho y alto del video
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Obtener frames por segundo (fps)
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Obtener duración del video en segundos
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps if fps != 0 else 0

    # Cierra el video
    cap.release()

    return {
        "ancho": width,
        "alto": height,
        "fps": fps,
        "duracion": duration
    }
    
    
if __name__ == "__main__":
    path_video = "data/raw/people_dancing_demo_0.mp4"
    print(video_summary(path_video))
    
    path_video = "data/standarized/people_dancing_demo_0_std.mp4"
    print(video_summary(path_video))