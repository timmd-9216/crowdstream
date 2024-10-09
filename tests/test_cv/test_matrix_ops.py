import numpy as np
import pytest

from crowdstream.cv.matrix_ops import (calculate_distance_matrix,
                                       create_new_keypoints_matrix,
                                       extend_keypoints_matrix,
                                       replace_zeros_with_keypoints_mask)


def test_create_new_keypoints_matrix_default():

    new_idxs = np.array([1, 2, 3])
    new_kps = np.array([[[1, 1], [2, 2], [3, 3]], [[4, 4], [5, 5], [6, 6]], [[7, 7], [8, 8], [9, 9]]])
    output = create_new_keypoints_matrix(new_idxs, new_kps, 1)
    expected = np.array([[[1, 1], [2, 2], [3, 3]], [[4, 4], [5, 5], [6, 6]], [[7, 7], [8, 8], [9, 9]]])

    np.testing.assert_equal(output, expected)
    
    new_idxs = np.array([1, 4, 3])
    new_kps = np.array([[[1, 1], [2, 2], [3, 3]], [[4, 4], [5, 5], [6, 6]], [[7, 7], [8, 8], [9, 9]]])
    output = create_new_keypoints_matrix(new_idxs, new_kps, 1)
    expected = np.array([[[1, 1], [2, 2], [3, 3]], [[0, 0], [0, 0], [0, 0]], [[7, 7], [8, 8], [9, 9]], [[4, 4], [5, 5], [6, 6]]])

    np.testing.assert_equal(output, expected)

    new_idxs = np.array([1, 3, 4, 6])
    new_kps = np.array([[[1, 1], [2, 2], [3, 3]], [[4, 4], [5, 5], [6, 6]], [[7, 7], [8, 8], [9, 9]], [[10, 10], [11, 11], [12, 12]]])
    output = create_new_keypoints_matrix(new_idxs, new_kps, 1)
    expected = np.array([[[1, 1], [2, 2], [3, 3]], [[0, 0], [0, 0], [0, 0]], [[4, 4], [5, 5], [6, 6]], [[7, 7], [8, 8], [9, 9]], [[0, 0], [0, 0], [0, 0]], [[10, 10], [11, 11], [12, 12]]])
    
    np.testing.assert_equal(output, expected)
    
    
def test_create_new_keypoints_matrix_max_index():

    new_idxs = np.array([1, 2, 3])
    new_kps = np.array([[[1, 1], [2, 2], [3, 3]], [[4, 4], [5, 5], [6, 6]], [[7, 7], [8, 8], [9, 9]]])
    output = create_new_keypoints_matrix(new_idxs, new_kps, 3)
    expected = np.array([[[1, 1], [2, 2], [3, 3]], [[4, 4], [5, 5], [6, 6]], [[7, 7], [8, 8], [9, 9]], [[0, 0], [0, 0], [0, 0]]])

    np.testing.assert_equal(output, expected)
    
    new_idxs = np.array([1, 4, 3])
    new_kps = np.array([[[1, 1], [2, 2], [3, 3]], [[4, 4], [5, 5], [6, 6]], [[7, 7], [8, 8], [9, 9]]])
    output = create_new_keypoints_matrix(new_idxs, new_kps, 4)
    expected = np.array([[[1, 1], [2, 2], [3, 3]], [[0, 0], [0, 0], [0, 0]], [[7, 7], [8, 8], [9, 9]], [[4, 4], [5, 5], [6, 6]], [[0, 0], [0, 0], [0, 0]]])

    np.testing.assert_equal(output, expected)

    new_idxs = np.array([1, 3, 4, 6])
    new_kps = np.array([[[1, 1], [2, 2], [3, 3]], [[4, 4], [5, 5], [6, 6]], [[7, 7], [8, 8], [9, 9]], [[10, 10], [11, 11], [12, 12]]])
    output = create_new_keypoints_matrix(new_idxs, new_kps, 7)
    expected = np.array([[[1, 1], [2, 2], [3, 3]], [[0, 0], [0, 0], [0, 0]], [[4, 4], [5, 5], [6, 6]], [[7, 7], [8, 8], [9, 9]], [[0, 0], [0, 0], [0, 0]], [[10, 10], [11, 11], [12, 12]], [[0, 0], [0, 0], [0, 0]], [[0, 0], [0, 0], [0, 0]]])
    
    np.testing.assert_equal(output, expected)
    

    
def test_extend_keypoints_matrix_default():
    
    kps_1 = np.array([[[1, 1], [2, 2], [3, 3]], [[4, 4], [5, 5], [6, 6]], [[7, 7], [8, 8], [9, 9]]])
    kps_2 = np.array([[[1, 1], [2, 2], [3, 3]], [[0, 0], [0, 0], [0, 0]], [[7, 7], [8, 8], [9, 9]], [[4, 4], [5, 5], [6, 6]]])
    kps_3 = np.array([[[1, 1], [2, 2], [3, 3]], [[0, 0], [0, 0], [0, 0]], [[4, 4], [5, 5], [6, 6]], [[7, 7], [8, 8], [9, 9]], [[0, 0], [0, 0], [0, 0]], [[10, 10], [11, 11], [12, 12]]])

    output = extend_keypoints_matrix(kps_1, kps_2)
    expected = np.array([[[1, 1], [2, 2], [3, 3]], [[4, 4], [5, 5], [6, 6]], [[7, 7], [8, 8], [9, 9]], [[4, 4], [5, 5], [6, 6]]])

    np.testing.assert_equal(output, expected)
    
    output = extend_keypoints_matrix(kps_2, kps_3)
    expected = np.array([[[1, 1], [2, 2], [3, 3]], [[0, 0], [0, 0], [0, 0]], [[7, 7], [8, 8], [9, 9]], [[4, 4], [5, 5], [6, 6]], [[0, 0], [0, 0], [0, 0]], [[10, 10], [11, 11], [12, 12]]])

    np.testing.assert_equal(output, expected)

    output = extend_keypoints_matrix(kps_1, kps_3)
    expected = np.array([[[1, 1], [2, 2], [3, 3]], [[4, 4], [5, 5], [6, 6]], [[7, 7], [8, 8], [9, 9]], [[7, 7], [8, 8], [9, 9]], [[0, 0], [0, 0], [0, 0]], [[10, 10], [11, 11], [12, 12]]])
    
    np.testing.assert_equal(output, expected)
    
    











# kps_1 = np.array([[[1, 1], [2, 2], [3, 3]], [[9, 9], [9, 9], [9, 9]], [[7, 7], [8, 8], [9, 9]], [[4, 4], [5, 5], [6, 6]], [[0, 0], [0, 0], [0, 0]]])
# kps_new_1 = np.array([[[1, 1], [2, 2], [3, 3]], [[0, 0], [0, 0], [0, 0]], [[1, 1], [1, 1], [1, 1]], [[2, 2], [2, 2], [2, 2]], [[0, 0], [0, 0], [0, 0]], [[10, 10], [11, 11], [12, 12]]])

# output_1 = np.array([[[1, 1], [2, 2], [3, 3]], [[9, 9], [9, 9], [9, 9]], [[1, 1], [1, 1], [1, 1]], [[2, 2], [2, 2], [2, 2]], [[0, 0], [0, 0], [0, 0]], [[10, 10], [11, 11], [12, 12]]])

# np.testing.assert_equal(replace_zeros_with_keypoints_mask(kps_1, kps_new_1), output_1)

# replace_zeros_with_keypoints_mask(kps_1, kps_new_1)


# kps_2 = np.array([[[1, 1], [2, 2], [3, 3]], [[9, 9], [9, 9], [9, 9]], [[7, 7], [8, 8], [9, 9]], [[4, 4], [5, 5], [6, 6]], [[1, 1], [0, 0], [2, 2]]])
# kps_new_2 = np.array([[[1, 1], [2, 2], [3, 3]], [[1, 1], [0, 0], [2, 2]], [[1, 1], [1, 1], [1, 1]], [[2, 2], [2, 2], [2, 2]], [[0, 0], [0, 0], [0, 0]], [[10, 10], [11, 11], [12, 12]]])

# output_2 = np.array([[[1, 1], [2, 2], [3, 3]], [[1, 1], [9, 9], [2, 2]], [[1, 1], [1, 1], [1, 1]], [[2, 2], [2, 2], [2, 2]], [[1, 1], [0, 0], [2, 2]], [[10, 10], [11, 11], [12, 12]]])

# np.testing.assert_equal(replace_zeros_with_keypoints_mask(kps_2, kps_new_2), output_2)

# replace_zeros_with_keypoints_mask(kps_2, kps_new_2)





# kps_1 = extend_keypoints_matrix(kps_1, kps_new_1)
# kps_new_1 = replace_zeros_with_keypoints_mask(kps_1, kps_new_1)

# print(calculate_distance_matrix(kps_1, kps_new_1))

# kps_2 = extend_keypoints_matrix(kps_2, kps_new_2)
# kps_new_2 = replace_zeros_with_keypoints_mask(kps_2, kps_new_2)

# print(calculate_distance_matrix(kps_2, kps_new_2))




