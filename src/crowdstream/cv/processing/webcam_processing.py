import random
from typing import Optional

import cv2
import matplotlib.pyplot as plt
from ultralytics import YOLO

from crowdstream.cv.signal.diff_signal import DiffSignalContainer
from crowdstream.cv.signal.matrix_ops import get_idxs_and_kps_from_result
from crowdstream.cv.signal.pose_signal import PoseSignalContainer
from crowdstream.cv.utils.keypoint import Keypoint


def webcam_processing(signal_container: PoseSignalContainer | DiffSignalContainer) -> None:


    ## OPEN CV PIPELINE ------
    # Open the default camera
    cam = cv2.VideoCapture(0)

    # Get the default frame width and height
    frame_width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Load a model
    if isinstance(signal_container, PoseSignalContainer):
        model = YOLO("models/yolov8n-pose.pt")

    # Plotting
    plt.ion()  # turning interactive mode on

    x = [0]
    y = [0.0]

    # Set up initial plot and legend outside the loop
    fig, ax = plt.subplots()
    
    line, = ax.plot([], [], color="green", label="Energy")

    # Show the legend only once
    plt.xlabel("Frame")
    plt.ylabel("Signal")
    plt.legend(loc="upper right")
        

    while True:
        
        # Capture the frame
        ret, frame = cam.read()
        
        if isinstance(signal_container, PoseSignalContainer):
            # Run the model on the frame and get the result
            r = model.track(source=frame, persist=True, stream=False, verbose=False)
            annotated_frame = r[0].plot()
            
            # Get the new indexes and keypoints from the result
            new_idxs, new_keypoints = get_idxs_and_kps_from_result(r[0])

            # Update the signal container with the new data
            signal_container.update(new_idxs, new_keypoints)
        
        else:
            signal_container.update(frame)
            annotated_frame = signal_container.diff_matrix if signal_container.diff_matrix is not None else frame
        
        
        try:
        
            print(signal_container.signal[-1])        
        
            # Update the x data with the new frame id
            x.append(signal_container.frame_id)  
            # Add the new signal value to the corresponding keypoint list
            y.append(signal_container.signal[-1])
             # Update the line data for the keypoint
            line.set_data(x, y)
            
            # Adjust plot limits
            ax.relim()
            ax.autoscale_view()
            
            # Show plot
            plt.show()
            plt.pause(0.005)
            
        except:
            pass

        #Display the captured frame
        cv2.imshow('Camera', annotated_frame)
        
        # Press 'q' to exit the loop
        if cv2.waitKey(1) == ord('q'):
            break

    # Release the capture and writer objects
    cam.release()
    cv2.destroyAllWindows()
    


def generate_colors(values, cmap_name='viridis'):
    """
    Generates a list of colors based on the input values using a colormap.

    Parameters:
    values (list): List of values for which to generate colors.
    cmap_name (str): Name of the colormap to use (default is 'viridis').

    Returns:
    list: List of color hex codes with the same size as values.
    """
    cmap = plt.cm.get_cmap(cmap_name, len(values))
    colors = [cmap(i) for i in range(len(values))]
    return colors



    
def webcam_processing_multikeypoint(signal_container: PoseSignalContainer) -> None:

    ## OPEN CV PIPELINE ------
    # Open the default camera
    cam = cv2.VideoCapture(0)

    # Get the default frame width and height
    frame_width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Load a model
    model = YOLO("models/yolov8n-pose.pt")

    # If no keypoints are provided, use all keypoints
    considered_keypoints = [Keypoint(i[0]) for i in signal_container.considered_keypoints]     
     
    plt.ion()  # turning interactive mode on
    
    x = [0]
    y = {k.name: [0.0] for k in considered_keypoints}
    colors = generate_colors(considered_keypoints, cmap_name='jet')
    
    # Set up initial plot and legend outside the loop
    fig, ax = plt.subplots()
    lines = {}
    for k, color in zip(considered_keypoints, colors):
        # Create a line for each keypoint with a label and store it in the dictionary
        line, = ax.plot([], [], color=color, label=k.name)
        lines[k.name] = line

    # Show the legend only once
    plt.xlabel("Frame")
    plt.ylabel("Signal")
    plt.legend(loc="upper right")
        
    while True:
        
        # Capture the frame
        ret, frame = cam.read()
        
        # Run the model on the frame and get the result
        r = model.track(source=frame, persist=True, stream=False, verbose=False)
        annotated_frame = r[0].plot()
        
        # Get the new indexes and keypoints from the result
        new_idxs, new_keypoints = get_idxs_and_kps_from_result(r[0])

        # Update the signal container with the new data
        signal_container.update(new_idxs, new_keypoints)
        
        try:
        
            print(signal_container.signal[-1])
            
            # Update the x data with the new frame id
            x.append(signal_container.frame_id)  
        
            for k in considered_keypoints:
                # Add the new signal value to the corresponding keypoint list
                y[k.name].append(float(signal_container.signals_matrix[-1][0, k.value]))
                # Update the line data for the keypoint
                lines[k.name].set_data(x, y[k.name])
            
            # Adjust plot limits
            ax.relim()
            ax.set_ylim((0,500))
            ax.autoscale_view()
            
            # Show plot
            plt.show()
            plt.pause(0.005)
            
        except:
            pass

        #Display the captured frame
        cv2.imshow('Camera', annotated_frame)
        
        # Press 'q' to exit the loop
        if cv2.waitKey(1) == ord('q'):
            break

    # Release the capture and writer objects
    cam.release()
    cv2.destroyAllWindows()




if __name__ == "__main__":
    
    selected_keypoints = [Keypoint.Nose, Keypoint.LeftWrist, Keypoint.RightWrist]
    max_signal_len = 10000
    
    signal_container = PoseSignalContainer(considered_keypoints=selected_keypoints, max_signal_len=max_signal_len)
    
    #signal_container = DiffSignalContainer(max_signal_len=max_signal_len)
    
    webcam_processing(signal_container)
    
    #webcam_processing_multikeypoint(signal_container)


    
