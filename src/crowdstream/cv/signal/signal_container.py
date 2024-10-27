import pickle
from typing import Optional

import numpy as np
import pandas as pd
from attrs import define, field

from crowdstream.cv.signal.matrix_ops import (
    calculate_distance_matrix, create_new_keypoints_matrix,
    extend_keypoints_matrix, get_idxs_and_kps_from_result,
    replace_zeros_with_keypoints_mask)
from crowdstream.cv.utils.keypoint import Keypoint


def _keypoint_converter(x: Optional[list]) -> list[list[int]]:
    """
    Convierte una lista de Keypoints y enteros en una lista de enteros. En caso de pasar None devuelve una lista con todos los valores de los Keypoints.
    """
    
    result = []
    
    if x is None:
        return [[kp.value] for kp in Keypoint]
    
    for item in x:
        if isinstance(item, Keypoint):
            result.append([item.value])
        elif isinstance(item, int):
            result.append([item])
        else:
            raise ValueError("All items in the list must be either Keypoints or ints.")
    return result



@define
class SignalContainer:
    # """
    # A class that manages signal updates, keypoints, and frame tracking across steps.

    # Attributes:
    # ----------
    # signals_matrix : List[np.ndarray]
    #     A list containing the signal updates for each step.
    # signal_frame_log : List[int]
    #     A list that stores the frame_id for each signal update.
    # signal : Optional[np.ndarray]
    #     A NumPy array representing the current signal matrix (initially None).
    # keypoints : Optional[np.ndarray]
    #     A NumPy array representing the keypoints of the previous step (initially None).
    # frame_id : int
    #     An integer tracking the number of frames advanced.
    # _new_keypoints : Optional[np.ndarray]
    #     A NumPy array representing the keypoints for the new step (initially None).
    # _new_idxs : Optional[np.ndarray]
    #     A NumPy array representing the idx vector for the new step keypoints (initially None).
    # """
    
    considered_indexes: Optional[list[int]] = field(factory=list)
    considered_keypoints: list[list[int]] = field(factory=list, converter=lambda x: _keypoint_converter(x))
    max_signal_len: int = 100

    signals_matrix: list[np.ndarray] = field(factory=list, init=False) #todo Esto tiene que tener una dimensión.
    signal_frame_log: list[int] = field(factory=list, init=False)
    signal: list[float] = field(factory=list, init=False)
    keypoints: Optional[np.ndarray] = field(default=None, init=False)
    frame_id: int = field(default=-1, init=False)
    _new_keypoints: Optional[np.ndarray] = field(default=None, init=False)
    _new_idxs: Optional[np.ndarray] = field(default=None, init=False)
    
    
    

    def update_new_data(self, new_idxs: Optional[np.ndarray], new_keypoints: Optional[np.ndarray]) -> None:
        """
        Actualiza los nuevos keypoints y los nuevos índices para el siguiente paso. En caso de que sean None no se actualiza nada.
        """
        if new_idxs is not None and new_keypoints is not None:
            self._new_idxs = new_idxs.copy()
            self._new_keypoints = new_keypoints.copy()

    def preprocess_data(self) -> None:
        """
        Procesa los nuevos keypoints y los keypoints actuales para que estén listos para el cálculo de la señal.
        
        create_new_keypoints_matrix: Esta función expande la matriz de keypoints nuevos para que sus keypoints respeten el orden según su index. Además, se 
        asegura que la dimensión de la nueva matriz sea igual o mayor a la actual de keypoints completando con ceros si es necesario.
        
        extend_keypoints_matrix: Expande la primera dimensión de la matriz de keypoints actuales para que sea igual que la matriz de keypoints nuevos actualizada.
        
        replace_zeros_with_keypoints_mask: Reemplaza los keypoints de la matriz de keypoints nuevos con los keypoints de la matriz de keypoints actuales si el valor 
        de la matriz de keypoints nuevos es 0.
        """

        if self._new_idxs is not None and self._new_keypoints is not None and self.keypoints is not None:
            self._new_keypoints = create_new_keypoints_matrix(self._new_idxs, self._new_keypoints, self.keypoints.shape[0]-1)
            self.keypoints = extend_keypoints_matrix(self.keypoints, self._new_keypoints)
            self._new_keypoints = replace_zeros_with_keypoints_mask(self.keypoints, self._new_keypoints)
            
        elif self._new_idxs is not None and self._new_keypoints is not None:
            # En caso de que los keypoints actuales sean None, se crea una matriz de keypoints nuevos con la dimensión máxima de la señal.
            self._new_keypoints = create_new_keypoints_matrix(self._new_idxs, self._new_keypoints, 1)


    def update_signal(self, considered_indexes: Optional[list[int]], considered_keypoints: list[list[int]]) -> None:
        """
        Actualiza la matriz de señales calculando las distancias entre los keypoints actuales y los nuevos keypoints.
        
        Actualiza la señal agregada de la matriz de señales usando los índices y keypoints considerados.
        """
        if self.keypoints is not None and self._new_keypoints is not None:
            # Calculamos la matriz de distancias entre los keypoints actuales y los nuevos keypoints.
            current_signal_matrix = calculate_distance_matrix(self.keypoints, self._new_keypoints)
            
            # Agregar la matriz de señales a la lista de matrices de señales.
            self.signals_matrix.append(current_signal_matrix)
            
            # Registrar el frame actual en la lista de frames.
            self.signal_frame_log.append(self.frame_id)
            
            # Calculamos la señal agregada de la matriz de señales usando los índices y keypoints considerados.
            if considered_indexes is None:
                self.signal.append(float(np.mean(current_signal_matrix[:, considered_keypoints])))
            else:
                considered_indexes = [i for i in considered_indexes if i < current_signal_matrix.shape[0]]
                self.signal.append(float(np.mean(current_signal_matrix[considered_indexes, considered_keypoints])))
            
    def update_keypoints(self) -> None:
        """
        Updates the current keypoints to be the new keypoints.
        """
        if self._new_keypoints is not None:
            self.keypoints = self._new_keypoints.copy()
            
    def control_signal_len(self) -> None:
        """
        Controla la longitud de la señal para que no exceda el máximo permitido.
        """
        if len(self.signals_matrix) > self.max_signal_len:
            self.signals_matrix.pop(0)
            self.signal_frame_log.pop(0)
            self.signal.pop(0)
                

    def empty_new_data(self) -> None:
        """
        Resetea los nuevos keypoints y los nuevos índices a None.
        """
        self._new_keypoints = None
        self._new_idxs = None

    def update(self, new_idxs: Optional[np.ndarray], new_keypoints: Optional[np.ndarray]) -> None:
        """
        Actualización completa de la señal. En caso de que no se proporcione nueva información, se salta el proceso de actualización.
        """
        # Advance the frame count regardless of the input
        self.frame_id += 1

        # If no new data is provided, skip the update process
        if new_idxs is None or new_keypoints is None:
            return
        
        # Update with new data
        self.update_new_data(new_idxs, new_keypoints)

        # Preprocess the keypoints matrices
        self.preprocess_data()

        # Update the signal and keypoints
        self.update_signal(considered_indexes=self.considered_indexes, considered_keypoints=self.considered_keypoints)
        
        # Update current keypoints to be the new keypoints
        self.update_keypoints()
        
        # Control the signal length
        self.control_signal_len()

        # Clear the new data after processing
        self.empty_new_data()

        # if self.frame_id > 0:

        #     # Update with new data
        #     self.update_new_data(new_idxs, new_keypoints)

        #     # Preprocess the keypoints matrices
        #     self.preprocess_data()

        #     # Update the signal and keypoints
        #     self.update_signal()
        #     self.update_keypoints()

        #     # Clear the new data after processing
        #     self.empty_new_data()
        
        # else:

        #     self.update_new_data(new_idxs, new_keypoints)

        #     self._new_keypoints = create_new_keypoints_matrix(self._new_idxs, self._new_keypoints, 1)

        #     self.keypoints = self._new_keypoints.copy()

        #     self.empty_new_data()



def get_signals_dataframe(signal_container: SignalContainer, df_format: str = "long") -> pd.DataFrame:
    
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
    
    
def get_signal_dataframe(signal_container: SignalContainer) -> pd.DataFrame:
    
    df = pd.DataFrame({"frame": signal_container.signal_frame_log, "signal": signal_container.signal})
    
    return df