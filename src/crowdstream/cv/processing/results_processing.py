
import pickle
from typing import Optional

from ultralytics.engine.results import Results

from crowdstream.cv.signal.diff_signal import DiffSignalContainer
from crowdstream.cv.signal.matrix_ops import get_idxs_and_kps_from_result
from crowdstream.cv.signal.pose_signal import PoseSignalContainer
from crowdstream.cv.utils.keypoint import Keypoint


def process_results(results: Results, signal_container: PoseSignalContainer | DiffSignalContainer, update_freq: int=1) -> PoseSignalContainer | DiffSignalContainer:
        
    #print(results[0])
    print(len(results)) #type: ignore
    print(type(results[0]))
    
    print(signal_container)
                
    i = 0

    for r in results:

        print("[INFO] Processing frame", i)
        
        if isinstance(signal_container, PoseSignalContainer):

            if i % update_freq == 0:
                new_idxs, new_keypoints = get_idxs_and_kps_from_result(r)

            else:
                new_idxs = None
                new_keypoints = None

            signal_container.update(new_idxs, new_keypoints)
            
        else:
            
            new_frame = r.orig_img 

            signal_container.update(new_frame)
            
        
        i += 1
        
    return signal_container


if __name__ == "__main__":
    
    update_freq = 1
    selected_keypoints = [Keypoint.LeftWrist, Keypoint.RightWrist]
    max_signal_len = 9999
    
    signal_container = PoseSignalContainer(considered_keypoints=selected_keypoints, max_signal_len=max_signal_len)
    signal_container = DiffSignalContainer(max_signal_len=max_signal_len)
    
    with open('data/pickles/people_dancing_demo_0_results.pkl', 'rb') as f:
        results = pickle.load(f)
    
    process_results(results, signal_container)