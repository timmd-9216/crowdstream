import random

import cv2
import matplotlib.pyplot as plt
from ultralytics import YOLO

from crowdstream.cv.signal.matrix_ops import get_idxs_and_kps_from_result
from crowdstream.cv.signal.signal_container import SignalContainer
from crowdstream.cv.utils.keypoint import Keypoint

# INPUTS 

colors = ["red", "green", "blue"]
KEYPOINTS = [9, 10, 11]
IDXS = "ALL"
#KEYPOINTS = [Keypoint(k) for k in KEYPOINTS]

## OPEN CV PIPELINE ------
# Open the default camera
cam = cv2.VideoCapture(0)

# Get the default frame width and height
frame_width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Load a model
model = YOLO("models/yolov8n-pose.pt")

signal_container = SignalContainer()

plt.ion()  # turning interactive mode on
# preparing the data


y = {k: [0] for k in KEYPOINTS}
x = [0]
 
# plotting the first frame
graph = plt.plot(x,y[list(y.keys())[0]])[0]
# plt.ylim(0,100)
#plt.pause(1)

# # Define the codec and create VideoWriter object
# fourcc = cv2.VideoWriter_fourcc(*'mp4v')
# out = cv2.VideoWriter('output.mp4', fourcc, 20.0, (frame_width, frame_height))

while True:
    
    ret, frame = cam.read()

    # # Write the frame to the output file
    # out.write(frame)
    
    r = model.track(source=frame, persist=True, stream=False, verbose=False)
    annotated_frame = r[0].plot()
    
    new_idxs, new_keypoints = get_idxs_and_kps_from_result(r[0])

    signal_container.update(new_idxs, new_keypoints)
    
    try:
        print(signal_container.signal[0, 10])
        # removing the older graph
        graph.remove()
        
        x.append(signal_container.frame_id)
        for k in KEYPOINTS:
            y[k].append(signal_container.signal[0, k])
        
        # plotting newer graph
        for k, color in zip(KEYPOINTS, colors):
            graph = plt.plot(x,y[k], color=color, label=str(Keypoint(k).name))[0]
            plt.xlabel("Frame")
            plt.ylabel("Signal")
        
        # calling pause function for 0.25 seconds
        plt.pause(0.1)
        # plt.xlim(x[0], x[-1])
        
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







 
# plt.ion()  # turning interactive mode on
 
# # preparing the data
# y = [random.randint(1,10) for i in range(20)]
# x = [*range(1,21)]
 
# # plotting the first frame
# graph = plt.plot(x,y)[0]
# plt.ylim(0,10)
# plt.pause(1)
 
# # the update loop
# while(True):
#     # updating the data
#     y.append(random.randint(1,10))
#     x.append(x[-1]+1)
     
#     # removing the older graph
#     graph.remove()
     
#     # plotting newer graph
#     graph = plt.plot(x,y,color = 'g')[0]
#     plt.xlim(x[0], x[-1])
     
#     # calling pause function for 0.25 seconds
#     plt.pause(0.25)
    
    
