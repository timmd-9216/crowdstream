
import pickle
from typing import Optional

from crowdstream.cv.signal.matrix_ops import get_idxs_and_kps_from_result
from crowdstream.cv.signal.signal_container import SignalContainer
from crowdstream.cv.utils.keypoint import Keypoint


def process_results(update_freq: int=1, considered_keypoints: Optional[list[Keypoint]]=None, max_signal_len: int=9999) -> None:
    
    with open('data/pickles/people_dancing_demo_0_results.pkl', 'rb') as f:
        results = pickle.load(f)
    
    print(results[0])
    print(len(results))
    print(type(results[0]))
    
    signal_container = SignalContainer(considered_keypoints, max_signal_len)

    print(signal_container)
                
    i = 0

    for r in results:

        print("[INFO] Processing frame", i)

        if i % update_freq == 0:
            new_idxs, new_keypoints = get_idxs_and_kps_from_result(r)

        else:
            new_idxs = None
            new_keypoints = None

        signal_container.update(new_idxs, new_keypoints)
        
        i += 1


if __name__ == "__main__":
    
    update_freq = 1
    selected_keypoints = [Keypoint.LeftWrist, Keypoint.RightWrist]
    max_signal_len = 9999
    
    process_results(update_freq, selected_keypoints, max_signal_len)