import unittest

from raspberry.config import (
    ALIGNMENT_SPEED,
    ALIGNMENT_TOLERANCE,
    MAX_FRAME_AGE,
    PID_INTEGRAL_LIMIT,
    SEARCH_BALL_SPEED,
    SEARCH_LINE_SPEED,
    SEARCH_SAFE_ZONE_SPEED,
)
from raspberry.pid import PIDController
from raspberry.states.alignment import AlignBallState
from raspberry.states.search_ball import SearchBallState
from raspberry.states.search_line import SearchLineState
from raspberry.states.search_safe_zone import SearchSafeZoneState


class PIDAndSpeedTests(unittest.TestCase):
    def test_search_commands_use_arduino_minimum(self):
        self.assertEqual(SearchLineState().execute(None, None, {}).command, "MOVE,110,0,1")
        self.assertEqual(SearchBallState().execute(None, None, {}).command, "MOVE,110,0,1")
        self.assertEqual(SearchSafeZoneState().execute(None, None, {}).command, "MOVE,110,0,1")
        self.assertEqual((SEARCH_LINE_SPEED, SEARCH_BALL_SPEED, SEARCH_SAFE_ZONE_SPEED), (110, 110, 110))

    def test_pid_integral_and_derivative_use_real_dt(self):
        controller = PIDController(0.0, 1.0, 1.0)
        controller.update(2.0, now=0.0)
        output = controller.update(4.0, now=0.5)
        self.assertAlmostEqual(controller.integral, 2.0)
        self.assertAlmostEqual(output, 6.0)

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
