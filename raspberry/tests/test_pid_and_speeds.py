import unittest
from unittest.mock import patch

from raspberry.config import (
    ALIGNMENT_SPEED,
    ALIGNMENT_TOLERANCE,
    MAX_FRAME_AGE,
    PID_INTEGRAL_LIMIT,
    LINE_SEARCH_TURN_PWM,
    SEARCH_BALL_SPEED,
    SEARCH_LINE_SPEED,
    SEARCH_SAFE_ZONE_SPEED,
)
from raspberry.pid import PIDController
from raspberry.config import RobotContext
from raspberry.states.alignment import AlignBallState
from raspberry.states.search_ball import SearchBallState
from raspberry.states.search_line import SearchLineState
from raspberry.states.search_safe_zone import SearchSafeZoneState


class PIDAndSpeedTests(unittest.TestCase):
    def test_search_commands_use_arduino_minimum(self):
        search_context = RobotContext()
        search_context.control_time = 0.0
        self.assertEqual(
            SearchLineState().execute(search_context, None, {}).command,
            f"MOVE,0,0,{LINE_SEARCH_TURN_PWM}",
        )
        self.assertEqual(SearchBallState().execute(None, None, {}).command, "MOVE,110,0,1")
        self.assertEqual(SearchSafeZoneState().execute(None, None, {}).command, "MOVE,110,0,1")
        self.assertEqual((SEARCH_LINE_SPEED, SEARCH_BALL_SPEED, SEARCH_SAFE_ZONE_SPEED), (110, 110, 110))

    def test_pid_integral_and_derivative_use_real_dt(self):
        controller = PIDController(0.0, 1.0, 1.0)
        controller.update(2.0, now=0.0)
        output = controller.update(4.0, now=0.5)
        self.assertAlmostEqual(controller.integral, 2.0)
        self.assertAlmostEqual(output, 3.0)

    def test_pid_derivative_filter_uses_explicit_new_sample_weight(self):
        with patch("raspberry.pid.PID_DERIVATIVE_FILTER_ALPHA", 0.25):
            controller = PIDController(0.0, 0.0, 1.0)
            controller.update(0.0, now=0.0)
            self.assertAlmostEqual(controller.update(1.0, now=0.1), 2.5)
            self.assertAlmostEqual(controller.update(1.0, now=0.2), 1.875)

    def test_pid_derivative_accounts_for_variable_observation_intervals(self):
        with patch("raspberry.pid.PID_DERIVATIVE_FILTER_ALPHA", 1.0):
            short = PIDController(0.0, 0.0, 1.0)
            long = PIDController(0.0, 0.0, 1.0)
            short.update(0.0, now=0.0)
            long.update(0.0, now=0.0)
            self.assertAlmostEqual(short.update(1.0, now=0.1), 10.0)
            self.assertAlmostEqual(long.update(2.0, now=0.2), 10.0)

    def test_pid_anti_windup_rejects_integral_that_drives_saturation(self):
        controller = PIDController(100.0, 10.0, 0.0, max_output=10.0)
        controller.update(1.0, now=0.0)
        output = controller.update(1.0, now=1.0)
        self.assertEqual(output, 10.0)
        self.assertEqual(controller.integral, 0.0)

    def test_pid_reset_clears_derivative_history_after_interruption(self):
        controller = PIDController(0.0, 0.0, 1.0)
        controller.update(1.0, now=0.0)
        controller.update(2.0, now=0.1)
        controller.reset()
        self.assertEqual(controller.update(-1.0, now=3.0), 0.0)

    def test_pid_integral_is_bounded(self):
        controller = PIDController(0.0, 1.0, 0.0)
        controller.update(1000.0, now=0.0)
        controller.update(1000.0, now=10.0)
        self.assertEqual(controller.integral, PID_INTEGRAL_LIMIT)

    def test_centralized_defaults_are_present(self):
        self.assertEqual(MAX_FRAME_AGE, 0.25)
        self.assertEqual(ALIGNMENT_SPEED, 110)
        self.assertEqual(ALIGNMENT_TOLERANCE, 0.15)


if __name__ == "__main__":
    unittest.main()
