from typing import Tuple

import numpy as np
import ultralytics


def get_idxs_and_kps_from_result(
    result: ultralytics.engine.results.Results #type: ignore
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extracts the vector of ids (idxs) and the matrix of keypoints (kps) from a
    Ultralytics `Results` object.

    Parameters:
    ----------
    result : Results
        A `Results` object from which the ids and keypoints are extracted.

    Returns:
    -------
    Tuple[np.ndarray, np.ndarray]
        A tuple containing:
        - idxs: A 1D NumPy array of integer ids.
        - kps: A 3D NumPy array of keypoints associated with those ids.

    Example:
    -------
    >>> idxs, kps = get_idxs_and_kps_from_result(result)
    >>> idxs.shape  # Example output: (5,)
    >>> kps.shape   # Example output: (5, 17, 3)
    """

    # Extract idxs using result.boxes.id, converting to a NumPy array of integers
    idxs = result.boxes.id.numpy().astype("int")

    # Extract keypoints using result.keypoints, converting to a NumPy array of floats
    kps = result.keypoints.xy.numpy()


    # TODO Revisar acá y ver que devolver si no tiene detecciones.
    # Asegúrate de que los objetos boxes.id y keypoints existan en el objeto result. Si pueden estar ausentes en algunas ejecuciones, podrías necesitar manejar esos casos con verificaciones adicionales.

    return idxs, kps



def create_new_keypoints_matrix(
    idx: np.ndarray, kps: np.ndarray, current_max_index: int
) -> np.ndarray:
    """
    Combines a single pair of index array and keypoint array into a 3D matrix,
    converting indices to 0-based indexing.

    The input consists of:
    - idx: 1D NumPy array of integer indices (minimum value 1) indicating where keypoints should be placed.
    - kps: 3D NumPy array of shape (len(idx), d1, d2) containing keypoint data.
    - current_max_index: The current maximum index for .

    The output is a 3D NumPy array of shape (j, d1, d2), where j is the max value between: highest index found
    in the idx array (converted to 0-based indexing) and the current_max_index. Each keypoint from kps is placed
    in the output array at the position specified by its corresponding index in idx.

    Parameters:
    ----------
    idx : np.ndarray
        1D NumPy array of integers representing indices with a minimum value of 1.
    kps : np.ndarray
        3D NumPy array with shape (len(idx), d1, d2) containing keypoint data.
    current_max_index : int
        The current maximum index found in processing. This value is used to determine the size of the first dimension, if it's 
        larger than the maximum index in idx. This will force the output matrix to have current_max_index or higher as its first dimension.

    Returns:
    -------
    np.ndarray
        A 3D NumPy array with shape (j, d1, d2), containing all keypoints placed according to their 0-based indices.

    Raises:
    ------
    ValueError
        If the input idx and kps arrays are incompatible.
        If any index in idx is less than 1.
        If kps is not 3D or the dimensions do not match.

    Example:
    -------
    >>> idx = np.array([1, 2, 4])
    >>> kps = np.random.rand(3, 5, 5)
    >>> combined = combine_keypoints_single(idx, kps, 1)
    >>> combined.shape
    (4, 5, 5)
    
    >>> idx = np.array([1, 2, 4])
    >>> kps = np.random.rand(3, 5, 5)
    >>> combined = combine_keypoints_single(idx, kps, 6)
    >>> combined.shape
    (6, 5, 5)
    """

    # Ensure that the kps array is 3D
    if kps.ndim != 3:
        raise ValueError("kps array must be 3-dimensional.")

    # Ensure that the length of idx matches the first dimension of kps
    if len(idx) != kps.shape[0]:
        raise ValueError("The length of idx must match the first dimension of kps.")

    # Ensure that the minimum index is at least 1
    if idx.min() < 1:
        raise ValueError("All values in idx must be >= 1.")
    
    # Ensure that the current_max_index is at least 1
    if current_max_index < 1:
        raise ValueError("current_max_index must be >= 1.")

    # Convert idx from 1-based to 0-based indexing
    idx_zero_based = idx - 1

    # Get the maximum index from idx_zero_based to define the size of the first dimension (j)
    max_index = idx_zero_based.max()
    max_index = max(max_index, current_max_index)
    
    # Get the second and third dimensions (d1 and d2) from kps
    d1, d2 = kps.shape[1], kps.shape[2]

    # Initialize the output array with zeros (or another suitable default value)
    # No need to add 1 to max_index here since we already converted to 0-based indexing
    output = np.zeros((max_index + 1, d1, d2), dtype=kps.dtype)

    # Iterate through each index and corresponding keypoint
    for i, index in enumerate(idx_zero_based):
        if not isinstance(index, (int, np.integer)):
            raise TypeError(f"Index at position {i} is not an integer.")

        # Place the keypoint in the output array at the corresponding index
        output[index] = kps[i]

    return output



def extend_keypoints_matrix(
    kps: np.ndarray, new_kps: np.ndarray
) -> np.ndarray:
    """
    Extends the first dimension of the kps matrix to match the size of new_kps,
    filling in the additional positions with values from new_kps.

    Parameters:
    ----------
    kps : np.ndarray
        A 3D NumPy array of shape (j, d1, d2) to be extended.
    new_kps : np.ndarray
        A 3D NumPy array of shape (j_new, d1, d2), where j_new >= j, and d1, d2 are equal to those in kps.

    Returns:
    -------
    np.ndarray
        A 3D NumPy array with shape (j_new, d1, d2), where the original kps matrix is extended
        to match the size of new_kps. Positions added are filled with the corresponding values from new_kps.

    Raises:
    ------
    ValueError
        If the second and third dimensions of kps and new_kps are not equal.
        If the first dimension of kps is larger than new_kps.

    Example:
    -------
    >>> kps = np.random.rand(3, 5, 5)
    >>> new_kps = np.random.rand(5, 5, 5)
    >>> extended_kps = extend_keypoints(kps, new_kps)
    >>> extended_kps.shape
    (5, 5, 5)
    """

    # Ensure the second and third dimensions are the same
    if kps.shape[1:] != new_kps.shape[1:]:
        raise ValueError("The second and third dimensions of kps and new_kps must be the same.")

    # Ensure that the first dimension of new_kps is larger or equal to that of kps
    if kps.shape[0] > new_kps.shape[0]:
        raise ValueError("The first dimension of kps cannot be larger than new_kps.")

    # Initialize an output array with the shape of new_kps
    extended_kps = np.copy(new_kps)

    # Copy the values from kps into the corresponding positions in the new array
    extended_kps[:kps.shape[0], :, :] = kps

    return extended_kps



def replace_zeros_with_keypoints_mask(
    kps: np.ndarray, new_kps: np.ndarray
) -> np.ndarray:
    """
    Replaces the zero values in new_kps with the corresponding values from kps.
    If any element in the last dimension of new_kps is zero, it will be replaced
    with the value from kps at the same position.

    Parameters:
    ----------
    kps : np.ndarray
        A 3D NumPy array of shape (j, d1, d2).
    new_kps : np.ndarray
        A 3D NumPy array of shape (j_new, d1, d2), where j_new >= j, and d1, d2 are equal to those in kps.

    Returns:
    -------
    np.ndarray
        A 3D NumPy array with shape (j_new, d1, d2), where the zero values in new_kps are replaced
        by the corresponding values from kps.

    Raises:
    ------
    ValueError
        If the second and third dimensions of kps and new_kps are not equal.
        If the first dimension of kps is larger than new_kps.

    Example:
    -------
    >>> kps = np.random.rand(3, 5, 5)
    >>> new_kps = np.zeros((5, 5, 5))
    >>> updated_kps = replace_partial_zeros_with_keypoints(kps, new_kps)
    >>> updated_kps.shape
    (5, 5, 5)
    """

    # Ensure the second and third dimensions are the same
    if kps.shape[1:] != new_kps.shape[1:]:
        raise ValueError("The second and third dimensions of kps and new_kps must be the same.")

    # Ensure that the first dimension of new_kps is larger or equal to that of kps
    if kps.shape[0] > new_kps.shape[0]:
        raise ValueError("The first dimension of kps cannot be larger than new_kps.")

    # Create a mask that identifies where the elements in new_kps are zero
    zero_mask = (new_kps[:kps.shape[0]] == 0)

    # Replace the zero elements in new_kps with the corresponding elements from kps
    new_kps[:kps.shape[0]][zero_mask] = kps[:kps.shape[0]][zero_mask]

    return new_kps




def calculate_distance_matrix(
    kps: np.ndarray, new_kps: np.ndarray
) -> np.ndarray:
    """
    Calculates a 2D matrix of distances between corresponding vectors from two 3D matrices.

    The function computes the Euclidean distance (using np.linalg.norm) between
    corresponding vectors across the third dimension of `kps` and `new_kps`.

    Parameters:
    ----------
    kps : np.ndarray
        A 3D NumPy array with shape (d1, d2, d3).
    new_kps : np.ndarray
        A 3D NumPy array with shape (d1, d2, d3). Must have the same shape as `kps`.

    Returns:
    -------
    np.ndarray
        A 2D NumPy array of shape (d1, d2), where each element represents the Euclidean distance
        between corresponding vectors from `kps` and `new_kps` across the third dimension.

    Raises:
    ------
    ValueError
        If the shapes of `kps` and `new_kps` are not identical.

    Example:
    -------
    >>> kps = np.random.rand(5, 5, 3)
    >>> new_kps = np.random.rand(5, 5, 3)
    >>> distance_matrix = calculate_distance_matrix(kps, new_kps)
    >>> distance_matrix.shape
    (5, 5)
    """

    # Ensure that kps and new_kps have the same shape
    if kps.shape != new_kps.shape:
        raise ValueError("Both kps and new_kps must have the same shape.")

    # Calculate the Euclidean distance along the third dimension (d3)
    distances = np.linalg.norm(kps - new_kps, axis=2)

    return distances