import pandas as pd

from crowdstream.cv.signal.diff_signal import DiffSignalContainer
from crowdstream.cv.signal.pose_signal import PoseSignalContainer
from crowdstream.cv.utils.keypoint import Keypoint


def get_pose_signals_dataframe(signal_container: PoseSignalContainer, df_format: str = "long") -> pd.DataFrame:
    
    if df_format not in ["long", "wide"]:
        raise ValueError("df_format must be either 'long' or 'wide'.")

    df = []

    for i in range(len(signal_container.signal_frame_log)):
        
        _df = pd.DataFrame(signal_container.signals_matrix[i], columns=[Keypoint(j).name for j in range(17)])
        _df = _df.reset_index(names="idx").assign(frame=signal_container.signal_frame_log[i], idx = lambda x: x.idx + 1)
        
        df.append(_df)
        
    df = pd.concat(df)
    
    if df_format == "wide":
        return df
    
    else:
        df_long = df.melt(id_vars=["idx", "frame"], var_name="keypoint", value_name="value")
        return df_long
    
    
def get_signal_dataframe(signal_container: DiffSignalContainer | PoseSignalContainer) -> pd.DataFrame:
    
    df = pd.DataFrame({"frame": signal_container.signal_frame_log, "signal": signal_container.signal})
    
    return df