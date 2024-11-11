import cv2


def stanzarize_video(input_path: str, output_path: str, width: int=1280, height: int=720, fps: int=24) -> None:
    """
    Lleva un video a una resolución de 1280x720 y lo guarda en el directorio de salida.

    Args:
        input_path (str): _description_
        output_path (str): _description_
        width (int, optional): _description_. Defaults to 1280.
        height (int, optional): _description_. Defaults to 720.
        fps (int, optional): _description_. Defaults to 24.
        
    #TODO Se puede agregar la opción de cambiar los fps pero debe mantener la duración original del video (por ahora no se usan los fps).
    """

    # Captura de video desde el archivo de entrada
    cap = cv2.VideoCapture(input_path)

    # Obtener propiedades originales del video
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Calculamos el factor de cambio de velocidad de fotogramas
    #frame_interval = int(original_fps / fps)

    # Define el codec y crea el objeto VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec para el archivo de salida #type: ignore
    #out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    out = cv2.VideoWriter(output_path, fourcc, original_fps, (width, height)) # POR AHORA MANTENEMOS LOS VIDEOS CON LOS FRAMES ORIGINALES.

    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Redimensiona el frame a 1280x720
        resized_frame = cv2.resize(frame, (width, height))

        out.write(resized_frame)

        # Guardamos cada frame al intervalo especificado para alcanzar los 24 fps
        # if frame_count % frame_interval == 0:
        #     out.write(resized_frame)

        frame_count += 1

    # Libera los recursos
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print("Video procesado y guardado en:", output_path)
    
    
    

    def stanzarize_raw_videos() -> None:
        
        videos = [
            "data/raw/people_dancing_demo_0.mp4",
            "data/raw/people_dancing_demo_1.mp4",
            "data/raw/people_dancing_demo_2.mp4",
            "data/raw/people_dancing_demo_3.mp4"
        ]
        
        for video in videos:
            output_video = video.replace("raw", "stanzarized").replace(".mp4", "_std.mp4")
            stanzarize_video(video, output_video, 1280, 720)