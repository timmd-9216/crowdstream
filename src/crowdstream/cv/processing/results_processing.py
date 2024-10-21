
import pickle

from crowdstream.cv.signal.matrix_ops import get_idxs_and_kps_from_result
from crowdstream.cv.signal.signal_container import SignalContainer


def main() -> None:
    
    with open('data/pickles/people_dancing_demo_0_results.pkl', 'rb') as f:
        results = pickle.load(f)
    
    print(results[0])
    print(len(results))
    print(type(results[0]))
    
    signal_container = SignalContainer()

    print(signal_container)
    
    i = 0
    
    for r in results:

        print("[INFO] Processing frame", i)
        
        if len(r.boxes) > 0:

            new_idxs, new_keypoints = get_idxs_and_kps_from_result(r)

            signal_container.update(new_idxs, new_keypoints)

        else:
            signal_container.update(None, None)
        
        i += 1


if __name__ == "__main__":
    
    main()