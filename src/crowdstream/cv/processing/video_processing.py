import pickle

import cv2
from ultralytics import YOLO

from crowdstream.cv.signal.matrix_ops import get_idxs_and_kps_from_result


def main() -> None:
    # Load a model
    model = YOLO("models/yolov8n-pose.pt")  # load an official model

    # Predict with the model
    results = model.track('data/standarized/people_dancing_demo_0_std.mp4', save=False, stream=False)
    
    # Save results in pickle file.
    with open('pickles/people_dancing_demo_0_results.pkl', 'wb') as f:
        pickle.dump(results, f, pickle.HIGHEST_PROTOCOL)
        


from crowdstream.cv.signal.diff_signal import DiffSignalContainer
from crowdstream.cv.signal.pose_signal import PoseSignalContainer


def video_processing(video_path: str, signal_container: PoseSignalContainer | DiffSignalContainer, verbose: bool=False) -> PoseSignalContainer | DiffSignalContainer:


    ## OPEN CV PIPELINE ------
    # Open the default camera
    cam = cv2.VideoCapture(video_path)

    # Get the default frame width and height
    frame_width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n_frames = int(cam.get(cv2.CAP_PROP_FRAME_COUNT))

    # Load a model
    if isinstance(signal_container, PoseSignalContainer):
        model = YOLO("models/yolov8n-pose.pt")        

    for i in range(n_frames):
        
        if verbose:
            print("[INFO] Processing frame", i)

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
        

    # Release the capture and writer objects
    cam.release()
    cv2.destroyAllWindows()

    return signal_container
    
    
    
if __name__ == "__main__":
    main()
    
    #* people_dancing_demo_0_std -> Speed: 1.3ms preprocess, 51.1ms inference, 1.3ms postprocess per image at shape (1, 3, 384, 640)