import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from raspberry.camera import apply_camera_orientation
from raspberry.config import MOTOR_MAX_PWM, MOTOR_MIN_PWM
from raspberry.main import RobotApp
from raspberry.motion import _body_velocity_from_wheels, _firmware_wheel_pwms, normalize_motor_command


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
    def test_camera_orientation_does_not_invert_commands_twice(self):
        with patch("raspberry.motion.CAMERA_INVERTED", True):
            self.assertEqual(normalize_motor_command("MOVE,180,0,40"), "MOVE,180,0,40")
            self.assertEqual(normalize_motor_command("MOVE,0,150,0"), "MOVE,0,150,0")

    def test_curve_correction_is_symmetric_and_default_is_identity(self):
        with patch("raspberry.motion.CURVE_CORRECTION", 0.5):
            left = normalize_motor_command("MOVE,180,0,-40")
        with patch("raspberry.motion.CURVE_CORRECTION", 1.5):
            right = normalize_motor_command("MOVE,180,0,40")
        self.assertEqual(left, "MOVE,180,0,-20")
        self.assertEqual(right, "MOVE,180,0,60")

    def test_stops_and_non_move_protocol_commands_are_not_transformed(self):
        self.assertEqual(normalize_motor_command("STOP"), "STOP")
        self.assertEqual(normalize_motor_command("EMERGENCY STOP"), "EMERGENCY STOP")
        self.assertEqual(normalize_motor_command("HEARTBEAT"), "HEARTBEAT")

    def test_non_finite_motion_fails_safe(self):
        self.assertEqual(normalize_motor_command("MOVE,nan,0,0"), "STOP")
        self.assertEqual(normalize_motor_command("MOVE,inf,0,0"), "STOP")

    def test_replayed_command_is_not_normalized_twice(self):
        command = normalize_motor_command("MOVE,180,0,20")
        app = SimpleNamespace(context=SimpleNamespace(last_command=command))
        app._is_last_command_valid = lambda: True
        self.assertEqual(RobotApp._resolve_command(app, None), command)


class MotorDeadbandTests(unittest.TestCase):
    def _normalized_values(self, command, motor_min_pwm=MOTOR_MIN_PWM):
        normalized = normalize_motor_command(command, motor_min_pwm=motor_min_pwm)
        if normalized == "STOP":
            return normalized, (0.0, 0.0, 0.0)
        return normalized, tuple(float(value) for value in normalized.split(",")[1:])

    def _assert_realized_is_bounded(self, requested, motor_min_pwm=MOTOR_MIN_PWM):
        normalized, values = self._normalized_values(
            f"MOVE,{requested[0]},{requested[1]},{requested[2]}",
            motor_min_pwm,
        )
        wheels = _firmware_wheel_pwms(*values, motor_min_pwm=motor_min_pwm)
        realized = _body_velocity_from_wheels(wheels)
        for actual, goal in zip(realized, requested):
            if abs(goal) < 0.5:
                self.assertAlmostEqual(actual, 0.0, delta=0.51)
            else:
                self.assertGreaterEqual(actual * goal, -0.51, normalized)
                self.assertLessEqual(abs(actual), abs(goal) + 0.51, normalized)
        for pwm, threshold in zip(wheels, motor_min_pwm):
            self.assertTrue(pwm == 0 or abs(pwm) >= threshold)
            self.assertLessEqual(abs(pwm), MOTOR_MAX_PWM)
        return normalized, wheels, realized

    def test_audit_commands_reach_firmware_with_expected_outputs(self):
        cases = {
            "MOVE,150,0,0": (150, 150, 150, 150),
            "MOVE,150,0,50": (190, 190, 110, 110),
            "MOVE,110,0,80": (160, 160, 0, 0),
            "MOVE,0,0,110": (110, 110, -110, -110),
            "MOVE,0,0,-110": (-110, -110, 110, 110),
        }
        for command, expected_wheels in cases.items():
            with self.subTest(command=command):
                normalized = normalize_motor_command(command)
                values = tuple(float(value) for value in normalized.split(",")[1:])
                self.assertEqual(_firmware_wheel_pwms(*values), expected_wheels)

    def test_infeasible_low_speed_curve_stops_instead_of_becoming_straight(self):
        self.assertEqual(normalize_motor_command("MOVE,110,0,20"), "STOP")

    def test_straight_and_moderate_curves_preserve_translation_and_turn_sign(self):
        straight, wheels, _ = self._assert_realized_is_bounded((150, 0, 0))
        self.assertEqual(straight, "MOVE,150,0,0")
        self.assertEqual(wheels, (150, 150, 150, 150))
        for turn in (-50, 50):
            normalized, wheels, realized = self._assert_realized_is_bounded((150, 0, turn))
            self.assertTrue(normalized.startswith("MOVE,150,0,"))
            self.assertGreater(realized[2] * turn, 0)
            self.assertNotEqual(wheels, (0, 0, 0, 0))

    def test_closed_curves_rotation_lateral_and_signed_combinations(self):
        for command in (
            (110, 0, 80),
            (110, 0, -80),
            (0, 0, 110),
            (0, 0, -110),
            (0, 150, 0),
            (-150, 0, 40),
            (70, -60, -50),
        ):
            with self.subTest(command=command):
                self._assert_realized_is_bounded(command)

    def test_values_around_minimum_and_saturation_are_bounded(self):
        for command in (
            (109, 0, 0),
            (110, 0, 0),
            (111, 0, 0),
            (255, 0, 0),
            (255, 255, 255),
        ):
            with self.subTest(command=command):
                self._assert_realized_is_bounded(command)

    def test_per_motor_minima_are_used_in_the_projection(self):
        minima = (100, 120, 130, 110)
        normalized, wheels, _ = self._assert_realized_is_bounded((150, 0, 50), minima)
        self.assertNotEqual(normalized, "MOVE,150,0,50")
        self.assertEqual(wheels, _firmware_wheel_pwms(*map(float, normalized.split(",")[1:]), minima))

    def test_unrepresentable_small_commands_stop_instead_of_becoming_a_pivot(self):
        self.assertEqual(normalize_motor_command("MOVE,0,0,5"), "STOP")
        self.assertEqual(normalize_motor_command("MOVE,5,0,0"), "STOP")

    def test_sweeps_do_not_reverse_or_exceed_the_requested_twist(self):
        previous_turn = None
        for turn in range(-100, 101):
            normalized, values = self._normalized_values(f"MOVE,150,0,{turn}")
            realized = _body_velocity_from_wheels(_firmware_wheel_pwms(*values))
            self.assertGreaterEqual(realized[0], -0.51)
            self.assertLessEqual(realized[0], 150.51)
            self.assertGreaterEqual(realized[2] * turn, -0.51)
            self.assertLessEqual(abs(realized[2]), abs(turn) + 0.51)
            if previous_turn is not None:
                self.assertGreaterEqual(realized[2] + 0.51, previous_turn, normalized)
            previous_turn = realized[2]

        for vx in range(-180, 181, 30):
            for vy in range(-180, 181, 30):
                for wz in range(-120, 121, 30):
                    with self.subTest(vx=vx, vy=vy, wz=wz):
                        self._assert_realized_is_bounded((vx, vy, wz))


if __name__ == "__main__":
    unittest.main()
