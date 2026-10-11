import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from raspberry.config import RobotContext


class FakeClock:
    def __init__(self, now: float = 10.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


class RobotContextTTLTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.monotonic = patch("raspberry.config.time.monotonic", self.clock)
        self.monotonic.start()

    def tearDown(self) -> None:
        self.monotonic.stop()

    def test_temporal_signal_expiration_table(self) -> None:
        for age, expected_recent in ((0.0, True), (0.25, True), (0.251, False)):
            with self.subTest(age=age):
                self.clock.now = 10.0
                context = RobotContext()
                context.set_temporal_flag("obstacle_detected", True)

                self.clock.now += age
                context.expire_temporal_signals()

                self.assertEqual(
                    context.has_recent_temporal_flag("obstacle_detected", ttl=0.25),
                    expected_recent,
                )
                self.assertEqual(context.obstacle_detected, expected_recent)

    def test_event_expiration_table(self) -> None:
        for age, expected_recent in ((0.0, True), (1.0, True), (1.001, False)):
            with self.subTest(age=age):
                self.clock.now = 10.0
                context = RobotContext()
                context.set_last_event("BALL_CAPTURED")

                self.clock.now += age
                context.expire_temporal_signals()

                self.assertEqual(
                    context.has_recent_event("BALL_CAPTURED", ttl=1.0),
                    expected_recent,
                )
                self.assertEqual(context.last_event, "BALL_CAPTURED" if expected_recent else None)


if __name__ == "__main__":
    unittest.main()
