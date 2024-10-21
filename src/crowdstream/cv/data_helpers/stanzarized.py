import cv2


def stanzarize_video(input_path: str, output_path: str, width: int=1280, height: int=720, fps: int=24) -> None:
    """
    Función que usa archivos de input y output.
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