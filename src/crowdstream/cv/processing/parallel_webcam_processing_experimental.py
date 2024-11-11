# import queue
# import random
# import threading

# import cv2
# import matplotlib.pyplot as plt
# from ultralytics import YOLO

# from crowdstream.cv.signal.matrix_ops import get_idxs_and_kps_from_result
# from crowdstream.cv.signal.pose_signal import PoseSignalContainer
# from crowdstream.cv.utils.keypoint import Keypoint

# # INPUTS 

# colors = ["red", "green", "blue"]
# KEYPOINTS = [9, 10, 11]
# IDXS = "ALL"
# #KEYPOINTS = [Keypoint(k) for k in KEYPOINTS]

# ## OPEN CV PIPELINE ------
# # Open the default camera
# cam = cv2.VideoCapture(0)

# # Get the default frame width and height
# frame_width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
# frame_height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))

# # Load a model
# model = YOLO("models/yolov8n-pose.pt")

# signal_container = PoseSignalContainer()

# # Cola para enviar datos del hilo de detección al de plotting
# plot_queue = queue.Queue()

# def plotting_thread_func(plot_queue, stop_event):
#     plt.ion()  # Modo interactivo
#     fig, ax = plt.subplots()
#     lines = {}
#     colors_plot = ["red", "green", "blue"]
    
#     # Inicializar líneas para cada keypoint
#     for idx, k in enumerate(KEYPOINTS):
#         lines[k], = ax.plot([], [], color=colors_plot[idx % len(colors_plot)], label=str(Keypoint(k).name))
    
#     ax.set_xlabel("Frame")
#     ax.set_ylabel("Signal")
#     ax.legend()
#     plt.show()
    
#     x_data = []
#     y_data = {k: [] for k in KEYPOINTS}
    
#     while not stop_event.is_set():
#         try:
#             frame_id, signals = plot_queue.get(timeout=0.1)  # Espera hasta 0.1 segundos por datos
#             x_data.append(frame_id)
#             for k in KEYPOINTS:
#                 y_data[k].append(signals[k])
#                 lines[k].set_data(x_data, y_data[k])
            
#             ax.relim()
#             ax.autoscale_view()
#             fig.canvas.draw()
#             fig.canvas.flush_events()
#         except queue.Empty:
#             continue  # No hay nuevos datos, continuar esperando

# # Evento para detener el hilo de plotting
# stop_event = threading.Event()

# # Iniciar el hilo de plotting
# plot_thread = threading.Thread(target=plotting_thread_func, args=(plot_queue, stop_event))
# plot_thread.start()

# while True:
#     ret, frame = cam.read()
#     if not ret:
#         break

#     r = model.track(source=frame, persist=True, stream=False, verbose=False)
#     annotated_frame = r[0].plot()

#     new_idxs, new_keypoints = get_idxs_and_kps_from_result(r[0])
#     signal_container.update(new_idxs, new_keypoints)

#     try:
#         # Obtener los datos de los keypoints relevantes
#         current_signals = {k: signal_container.signals_matrix[0, k] for k in KEYPOINTS}
#         frame_id = signal_container.frame_id

#         # Enviar los datos al hilo de plotting
#         plot_queue.put((frame_id, current_signals))
#     except Exception as e:
#         print(f"Error al actualizar los datos de plot: {e}")

#     # Mostrar el frame anotado
#     cv2.imshow('Camera', annotated_frame)

#     # Salir si se presiona 'q'
#     if cv2.waitKey(1) == ord('q'):
#         break

# # Señalar al hilo de plotting que debe detenerse
# stop_event.set()
# plot_thread.join()

# # Liberar la cámara y cerrar las ventanas
# cam.release()
# cv2.destroyAllWindows()
# plt.ioff()
# plt.close()
