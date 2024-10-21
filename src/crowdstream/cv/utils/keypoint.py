from enum import Enum


class Keypoint(Enum):
    Nose = 0
    LeftEye = 1
    RightEye = 2
    LeftEar = 3
    RightEar = 4
    LeftShoulder = 5
    RightShoulder = 6
    LeftElbow = 7
    RightElbow = 8
    LeftWrist = 9
    RightWrist = 10
    LeftHip = 11
    RightHip = 12
    LeftKnee = 13
    RightKnee = 14
    LeftAnkle = 15
    RightAnkle = 16
    
    
    
if __name__ == "__main__":
    print(Keypoint.Nose.name)
    print(Keypoint.Nose.value)
    print(Keypoint(10).name)
    KEYPOINTS = [9, 10, 11]
    KEYPOINTS = [Keypoint(k) for k in KEYPOINTS]
    print({k.value: [0] for k in KEYPOINTS})