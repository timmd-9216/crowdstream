import pytest

from crowdstream.cv.signal.signal_container import (SignalContainer,
                                                    _keypoint_converter)
from crowdstream.cv.utils.keypoint import Keypoint


def test_keypoint_converter_default():
    assert _keypoint_converter([9, 10, 11]) == [9, 10, 11]
    
def test_keypoint_converter_keypoints():
    assert _keypoint_converter([Keypoint(9), Keypoint(10), Keypoint(11)]) == [9, 10, 11]
    
def test_keypoint_converter_mixed():
    assert _keypoint_converter([9, Keypoint(10), 11]) == [9, 10, 11]
    
def test_keypoint_converter_error():
    with pytest.raises(ValueError):
        _keypoint_converter([9, "a", 11])

def test_keypoint_converter_none():
    assert _keypoint_converter(None) == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]