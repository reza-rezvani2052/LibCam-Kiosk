from __future__ import annotations

import unittest

import numpy as np

from app.components.member_photo_kiosk.core.gesture_detector import (
    HandRaiseDetector,
    is_hand_raised,
    is_left_hand_raised,
    is_right_hand_raised,
)
from app.components.member_photo_kiosk.core.image_cropper import crop_detected_face
from app.components.member_photo_kiosk.core.camera_policy import (
    is_camera_allowed,
    is_virtual_camera_name,
)


class PhysicalCameraPolicyTests(unittest.TestCase):
    def test_known_virtual_webcams_are_rejected(self) -> None:
        self.assertTrue(is_virtual_camera_name("ManyCam Virtual Webcam"))
        self.assertTrue(is_virtual_camera_name("OBS Virtual Camera"))
        self.assertTrue(is_virtual_camera_name("DroidCam Source 3"))

    def test_normal_hardware_camera_names_are_allowed(self) -> None:
        self.assertFalse(is_virtual_camera_name("Integrated Camera"))
        self.assertFalse(is_virtual_camera_name("USB Video Device"))

    def test_virtual_camera_is_allowed_only_when_development_opts_in(self) -> None:
        self.assertFalse(
            is_camera_allowed("ManyCam Virtual Webcam", allow_virtual_cameras=False)
        )
        self.assertTrue(
            is_camera_allowed("ManyCam Virtual Webcam", allow_virtual_cameras=True)
        )

    def test_physical_camera_is_allowed_in_both_modes(self) -> None:
        self.assertTrue(is_camera_allowed("Integrated Camera", allow_virtual_cameras=False))
        self.assertTrue(is_camera_allowed("Integrated Camera", allow_virtual_cameras=True))


class LeftHandRaiseTests(unittest.TestCase):
    @staticmethod
    def make_keypoints(*, shoulder_y: float, wrist_y: float, confidence: float = 0.9):
        points = [[0.0, 0.0, 0.0] for _ in range(17)]
        points[5] = [100.0, shoulder_y, confidence]
        points[9] = [105.0, wrist_y, confidence]
        return points

    def test_only_left_wrist_above_left_shoulder_counts(self) -> None:
        keypoints = self.make_keypoints(shoulder_y=250, wrist_y=180)
        self.assertTrue(is_left_hand_raised(keypoints, 480))

    def test_wrist_below_shoulder_does_not_count(self) -> None:
        keypoints = self.make_keypoints(shoulder_y=180, wrist_y=250)
        self.assertFalse(is_left_hand_raised(keypoints, 480))

    def test_low_confidence_keypoints_do_not_count(self) -> None:
        keypoints = self.make_keypoints(
            shoulder_y=250,
            wrist_y=150,
            confidence=0.1,
        )
        self.assertFalse(is_left_hand_raised(keypoints, 480))

    def test_either_raised_hand_triggers_gesture(self) -> None:
        # COCO keypoints: right shoulder 6, right wrist 10.
        points = [[0.0, 0.0, 0.0] for _ in range(17)]
        points[6] = [200.0, 250.0, 0.9]
        points[10] = [210.0, 150.0, 0.9]
        self.assertTrue(is_right_hand_raised(points, 480))
        self.assertTrue(is_hand_raised(points, 480))

    def test_a_lowered_right_hand_does_not_trigger(self) -> None:
        points = [[0.0, 0.0, 0.0] for _ in range(17)]
        points[6] = [200.0, 180.0, 0.9]
        points[10] = [210.0, 250.0, 0.9]
        self.assertFalse(is_hand_raised(points, 480))

    def test_either_side_requires_confident_keypoints(self) -> None:
        points = [[0.0, 0.0, 0.0] for _ in range(17)]
        points[6] = [200.0, 250.0, 0.9]
        points[10] = [210.0, 150.0, 0.1]
        self.assertFalse(is_hand_raised(points, 480))

    def test_raise_must_be_sustained_and_is_one_shot(self) -> None:
        detector = HandRaiseDetector(confirmation_seconds=0.8, release_seconds=0.5)
        self.assertFalse(detector.update(True, 10.0))
        self.assertFalse(detector.update(True, 10.4))
        self.assertTrue(detector.update(True, 10.8))
        self.assertFalse(detector.update(True, 11.2))
        self.assertFalse(detector.update(False, 11.3))
        self.assertFalse(detector.update(False, 11.7))
        self.assertFalse(detector.update(False, 11.9))
        self.assertFalse(detector.update(True, 12.0))
        self.assertTrue(detector.update(True, 12.9))


class FaceCropTests(unittest.TestCase):
    def test_crop_adds_face_margin_and_owns_its_memory(self) -> None:
        frame = np.zeros((100, 120, 3), dtype=np.uint8)
        crop = crop_detected_face(frame, (40, 30, 60, 70))
        self.assertIsNotNone(crop)
        assert crop is not None
        self.assertGreater(crop.shape[0], 40)
        self.assertGreater(crop.shape[1], 20)
        self.assertFalse(np.shares_memory(crop, frame))

    def test_crop_clips_to_frame_bounds(self) -> None:
        frame = np.zeros((80, 90, 3), dtype=np.uint8)
        crop = crop_detected_face(frame, (0, 0, 20, 30))
        self.assertIsNotNone(crop)
        assert crop is not None
        self.assertLessEqual(crop.shape[0], 80)
        self.assertLessEqual(crop.shape[1], 90)

    def test_invalid_face_box_returns_none(self) -> None:
        frame = np.zeros((50, 50, 3), dtype=np.uint8)
        self.assertIsNone(crop_detected_face(frame, (20, 20, 20, 40)))


if __name__ == "__main__":
    unittest.main()
