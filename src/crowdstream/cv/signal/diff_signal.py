from typing import Optional

import cv2
import numpy as np
from attrs import define, field


@define
class DiffSignalContainer:
    
    max_signal_len: int = 100
    
    signal_frame_log: list[int] = field(factory=list, init=False)
    signal: list[float] = field(factory=list, init=False)
    diff_matrix: Optional[np.ndarray] = field(default=None, init=False)
    frame: Optional[np.ndarray] = field(default=None, init=False)
    frame_id: int = field(default=-1, init=False)
            
    def update_signal(self, new_frame: Optional[np.ndarray]) -> None:
        
        if self.frame is not None and new_frame is not None:
            
            self.signal_frame_log.append(self.frame_id)
            
            diff_mat = cv2.absdiff(self.frame, new_frame)
            self.diff_matrix = diff_mat
            self.signal.append(float(np.sum(diff_mat)))
            
    def update_frame(self, new_frame: Optional[np.ndarray]) -> None:
        self.frame = new_frame
        
    def control_signal_len(self) -> None:
        """
        Controla la longitud de la señal para que no exceda el máximo permitido.
        """
        if len(self.signal) > self.max_signal_len:
            self.signal.pop(0)
            self.signal_frame_log.pop(0)
    
    def update(self, new_frame: Optional[np.ndarray]) -> None:
        """
        Updates the signal matrix and frame log with the new frame.
        """
        # Advance the frame count regardless of the input
        self.frame_id += 1
        
        # If no new data is provided, skip the update process
        if new_frame is None:
            return
        
        # Update signal
        self.update_signal(new_frame)
        
        # Update frame
        self.update_frame(new_frame)
        
        # Control the signal length
        self.control_signal_len()