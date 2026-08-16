import sys
from pathlib import Path

import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.config import RobotContext
from raspberry.main import update_context_from_serial_message
from raspberry.states.avoid_obstacle import AvoidObstacleState
from raspberry.ultrasonic import UltrasonicMonitor


def feed(context, monitor, *distances) -> None:
    for distance in distances:
        update_context_from_serial_message(context, f"DIST,{distance}", monitor)


class UltrasonicFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.context = RobotContext()
        self.monitor = UltrasonicMonitor()

    def test_single_close_reading_does_not_trigger(self) -> None:
        feed(self.context, self.monitor, 12.0)

        self.assertAlmostEqual(self.context.obstacle_distance, 12.0)
        self.assertFalse(self.context.has_recent_temporal_flag("obstacle_detected", ttl=0.25))

    def test_two_consecutive_close_readings_trigger(self) -> None:
        feed(self.context, self.monitor, 12.0, 11.5)

        self.assertTrue(self.context.has_recent_temporal_flag("obstacle_detected", ttl=0.25))
        self.assertTrue(self.context.has_recent_temporal_flag("obstacle_detected_range", ttl=0.25))

    def test_far_reading_clears_the_obstacle(self) -> None:
        feed(self.context, self.monitor, 12.0, 11.5, 90.0)

        self.assertFalse(self.context.has_recent_temporal_flag("obstacle_detected", ttl=0.25))

    def test_erratic_readings_never_confirm(self) -> None:
        # Padrão típico do pino ECHO solto: valores válidos, porém sem coerência.
        feed(self.context, self.monitor, 5.0, 320.0, 8.0, 210.0, 3.0)

        self.assertFalse(self.context.has_recent_temporal_flag("obstacle_detected", ttl=0.25))

    def test_out_of_range_reading_is_ignored(self) -> None:
        feed(self.context, self.monitor, 900.0)

        self.assertIsNone(self.context.obstacle_distance)
        self.assertFalse(self.context.has_recent_temporal_flag("obstacle_detected", ttl=0.25))

    def test_dist_ignored_when_sensor_disabled(self) -> None:
        update_context_from_serial_message(self.context, "DIST,12.0", None)
        update_context_from_serial_message(self.context, "DIST,11.5", None)

        self.assertIsNone(self.context.obstacle_distance)
        self.assertFalse(self.context.has_recent_temporal_flag("obstacle_detected", ttl=0.25))

    def test_malformed_dist_is_ignored(self) -> None:
        update_context_from_serial_message(self.context, "DIST,abc", self.monitor)

        self.assertIsNone(self.context.obstacle_distance)


class ObstacleSourceTests(unittest.TestCase):
    """A visão e o ultrassônico não podem se apagar."""

    def setUp(self) -> None:
        self.context = RobotContext()
        self.monitor = UltrasonicMonitor()

    def test_vision_reporting_clear_does_not_erase_ultrasonic(self) -> None:
        feed(self.context, self.monitor, 12.0, 11.5)
        self.context.set_obstacle_source("vision", False)

        self.assertTrue(self.context.has_recent_temporal_flag("obstacle_detected", ttl=0.25))

    def test_ultrasonic_reporting_clear_does_not_erase_vision(self) -> None:
        self.context.set_obstacle_source("vision", True)
        feed(self.context, self.monitor, 90.0)

        self.assertTrue(self.context.has_recent_temporal_flag("obstacle_detected", ttl=0.25))

    def test_aggregate_falls_only_when_both_sources_are_clear(self) -> None:
        self.context.set_obstacle_source("vision", True)
        feed(self.context, self.monitor, 12.0, 11.5)

        self.context.set_obstacle_source("vision", False)
        feed(self.context, self.monitor, 90.0)

        self.assertFalse(self.context.has_recent_temporal_flag("obstacle_detected", ttl=0.25))

    def test_avoid_state_consumes_every_source(self) -> None:
        self.context.set_obstacle_source("vision", True)
        feed(self.context, self.monitor, 12.0, 11.5)

        AvoidObstacleState().execute(self.context, None, {})

        self.assertFalse(self.context.has_recent_temporal_flag("obstacle_detected", ttl=0.25))
        self.assertFalse(self.context.has_recent_temporal_flag("obstacle_detected_vision", ttl=0.25))
        self.assertFalse(self.context.has_recent_temporal_flag("obstacle_detected_range", ttl=0.25))

    def test_obstacle_event_still_triggers(self) -> None:
        update_context_from_serial_message(self.context, "OBSTACLE", self.monitor)

        self.assertTrue(self.context.has_recent_temporal_flag("obstacle_detected", ttl=0.25))


if __name__ == "__main__":
    unittest.main()
