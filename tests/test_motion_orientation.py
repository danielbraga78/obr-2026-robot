import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.camera import apply_camera_orientation
from raspberry.main import RobotApp
from raspberry.motion import normalize_motor_command


class CameraOrientationTests(unittest.TestCase):
    def test_normal_camera_returns_the_same_frame(self):
        frame = np.arange(24, dtype=np.uint8).reshape((2, 4, 3))

        with patch("raspberry.camera.CAMERA_INVERTED", False):
            result = apply_camera_orientation(frame)

        self.assertIs(result, frame)

    def test_inverted_camera_rotates_frame_exactly_180_degrees(self):
        frame = np.arange(24, dtype=np.uint8).reshape((2, 4, 3))

        with patch("raspberry.camera.CAMERA_INVERTED", True):
            result = apply_camera_orientation(frame)

        np.testing.assert_array_equal(result, frame[::-1, ::-1])


class MotorOrientationTests(unittest.TestCase):
    def test_normal_camera_preserves_move(self):
        with patch("raspberry.motion.CAMERA_INVERTED", False), patch(
            "raspberry.motion.CURVE_CORRECTION", 1.0
        ):
            self.assertEqual(normalize_motor_command("MOVE,100,-20,30"), "MOVE,100,-20,30")

    def test_inverted_camera_rotates_linear_command_axes(self):
        with patch("raspberry.motion.CAMERA_INVERTED", True), patch(
            "raspberry.motion.CURVE_CORRECTION", 1.0
        ):
            self.assertEqual(normalize_motor_command("MOVE,100,-20,30"), "MOVE,-100,20,30")

    def test_curve_correction_scales_turning_component_symmetrically(self):
        with patch("raspberry.motion.CAMERA_INVERTED", False), patch(
            "raspberry.motion.CURVE_CORRECTION", 0.5
        ):
            left_soft = normalize_motor_command("MOVE,180,0,-40")
        with patch("raspberry.motion.CURVE_CORRECTION", 1.0):
            left_default = normalize_motor_command("MOVE,180,0,-40")
        with patch("raspberry.motion.CURVE_CORRECTION", 1.5):
            left_strong = normalize_motor_command("MOVE,180,0,-40")
            right_strong = normalize_motor_command("MOVE,180,0,40")

        self.assertEqual(left_soft, "MOVE,180,0,-20")
        self.assertEqual(left_default, "MOVE,180,0,-40")
        self.assertEqual(left_strong, "MOVE,180,0,-60")
        self.assertEqual(right_strong, "MOVE,180,0,60")

    def test_curve_correction_clamps_turning_component(self):
        with patch("raspberry.motion.CURVE_CORRECTION", 10.0):
            self.assertEqual(normalize_motor_command("MOVE,180,0,40"), "MOVE,180,0,255")

    def test_stop_and_emergency_stop_are_never_transformed(self):
        with patch("raspberry.motion.CAMERA_INVERTED", True), patch(
            "raspberry.motion.CURVE_CORRECTION", 10.0
        ):
            self.assertEqual(normalize_motor_command("STOP"), "STOP")
            self.assertEqual(normalize_motor_command("EMERGENCY STOP"), "EMERGENCY STOP")
            self.assertEqual(normalize_motor_command("EMERGENCY_STOP"), "EMERGENCY_STOP")

    def test_replayed_command_is_not_normalized_twice(self):
        with patch("raspberry.motion.CAMERA_INVERTED", True), patch(
            "raspberry.motion.CURVE_CORRECTION", 1.5
        ):
            command = normalize_motor_command("MOVE,100,0,20")
            app = SimpleNamespace(context=SimpleNamespace(last_command=command))
            app._is_last_command_valid = lambda: True
            self.assertEqual(RobotApp._resolve_command(app, None), command)


if __name__ == "__main__":
    unittest.main()
