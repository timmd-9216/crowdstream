import pickle
from typing import Optional

import numpy as np
import pandas as pd
from attrs import define, field

from crowdstream.cv.matrix_ops import (calculate_distance_matrix,
                                       create_new_keypoints_matrix,
                                       extend_keypoints_matrix,
                                       get_idxs_and_kps_from_result,
                                       replace_zeros_with_keypoints_mask)
from crowdstream.cv.utils import Keypoint


@define
class SignalContainer:
    """
    A class that manages signal updates, keypoints, and frame tracking across steps.

    Attributes:
    ----------
    signal_list : List[np.ndarray]
        A list containing the signal updates for each step.
    signal_frame_log : List[int]
        A list that stores the frame_id for each signal update.
    signal : Optional[np.ndarray]
        A NumPy array representing the current signal matrix (initially None).
    keypoints : Optional[np.ndarray]
        A NumPy array representing the keypoints of the previous step (initially None).
    frame_id : int
        An integer tracking the number of frames advanced.
    _new_keypoints : Optional[np.ndarray]
        A NumPy array representing the keypoints for the new step (initially None).
    _new_idxs : Optional[np.ndarray]
        A NumPy array representing the idx vector for the new step keypoints (initially None).
    """
    signal_list: list[np.ndarray] = field(factory=list)
    signal_frame_log: list[int] = field(factory=list)
    signal: Optional[np.ndarray] = None
    keypoints: Optional[np.ndarray] = None
    frame_id: int = -1
    _new_keypoints: Optional[np.ndarray] = None
    _new_idxs: Optional[np.ndarray] = None
    #idxs: Optional[np.ndarray] = None

    def update_new_data(self, new_idxs: Optional[np.ndarray], new_keypoints: Optional[np.ndarray]) -> None:
        """
        Updates the new idxs and keypoints for future use.

        Parameters:
        ----------
        new_idxs : np.ndarray
            The new idx vector.
        new_keypoints : np.ndarray
            The new keypoints matrix.
        """
        if new_idxs is not None and new_keypoints is not None:
            self._new_idxs = new_idxs.copy()
            self._new_keypoints = new_keypoints.copy()

    def preprocess_data(self) -> None:

        if self._new_idxs is not None and self._new_keypoints is not None:
            self._new_keypoints = create_new_keypoints_matrix(self._new_idxs, self._new_keypoints, self.keypoints.shape[0]-1)
            self.keypoints = extend_keypoints_matrix(self.keypoints, self._new_keypoints)
            self._new_keypoints = replace_zeros_with_keypoints_mask(self.keypoints, self._new_keypoints)


    def update_signal(self) -> None:
        """
        Updates the signal matrix using the current keypoints and new keypoints after preprocessing.
        """
        if self.keypoints is not None and self._new_keypoints is not None:
            self.signal = calculate_distance_matrix(self.keypoints, self._new_keypoints)
            self.signal_list.append(self.signal)
            self.signal_frame_log.append(self.frame_id)

    def update_keypoints(self) -> None:
        """
        Updates the current keypoints to be the new keypoints.
        """
        self.keypoints = self._new_keypoints.copy()

    def empty_new_data(self) -> None:
        """
        Resets _new_keypoints and _new_idxs to None.
        """
        self._new_keypoints = None
        self._new_idxs = None

    def update(self, new_idxs: Optional[np.ndarray], new_keypoints: Optional[np.ndarray]) -> None:
        """
        Main update pipeline. Updates the entire container if new data is available.

        Parameters:
        ----------
        new_idxs : Optional[np.ndarray]
            The new idx vector for this update.
        new_keypoints : Optional[np.ndarray]
            The new keypoints matrix for this update.
        """
        # Advance the frame count regardless of the input
        self.frame_id += 1

        # If no new data is provided, skip the update process
        if new_idxs is None or new_keypoints is None:
            return

        if self.frame_id > 0:

            # Update with new data
            self.update_new_data(new_idxs, new_keypoints)

            # Preprocess the keypoints matrices
            self.preprocess_data()

            # Update the signal and keypoints
            self.update_signal()
            self.update_keypoints()

            # Clear the new data after processing
            self.empty_new_data()
        
        else:

            self.update_new_data(new_idxs, new_keypoints)

            self._new_keypoints = create_new_keypoints_matrix(self._new_idxs, self._new_keypoints, 1)

            self.keypoints = self._new_keypoints.copy()

            self.empty_new_data()



    def get_signal_dataframe(self, df_format: str = "long") -> pd.DataFrame:
        
        if df_format not in ["long", "wide"]:
            raise ValueError("df_format must be either 'long' or 'wide'.")

        df = []

        for i in range(len(self.signal_frame_log)):
            
            _df = pd.DataFrame(self.signal_list[i], columns=[Keypoint(j).name for j in range(17)])
            _df = _df.reset_index(names="idx").assign(frame=self.signal_frame_log[i], idx = lambda x: x.idx + 1)
            
            df.append(_df)
            
        df = pd.concat(df)
        
        if df_format == "wide":
            return df
        
        else:
            df_long = df.melt(id_vars=["idx", "frame"], var_name="keypoint", value_name="value")
            return df_long





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