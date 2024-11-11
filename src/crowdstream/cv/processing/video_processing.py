import pickle

from ultralytics import YOLO


def main() -> None:
    # Load a model
    model = YOLO("models/yolov8n-pose.pt")  # load an official model

    # Predict with the model
    results = model.track('data/standarized/people_dancing_demo_0_std.mp4', save=False, stream=False)
    
    # Save results in pickle file.
    with open('pickles/people_dancing_demo_0_results.pkl', 'wb') as f:
        pickle.dump(results, f, pickle.HIGHEST_PROTOCOL)
    
    
    
if __name__ == "__main__":
    main()
    
    #* people_dancing_demo_0_std -> Speed: 1.3ms preprocess, 51.1ms inference, 1.3ms postprocess per image at shape (1, 3, 384, 640)