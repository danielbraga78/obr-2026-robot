import sys
from pathlib import Path

import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.config import RobotContext
from raspberry.main import update_context_from_serial_message


class UltrasonicObstacleTests(unittest.TestCase):
    def test_close_ultrasonic_distance_triggers_obstacle_flag(self) -> None:
        context = RobotContext()

        update_context_from_serial_message(context, "DIST,12.0")

        self.assertAlmostEqual(context.obstacle_distance, 12.0)
        self.assertTrue(context.has_recent_temporal_flag("obstacle_detected", ttl=0.25))


if __name__ == "__main__":
    unittest.main()
