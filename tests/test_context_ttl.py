import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.config import RobotContext


class RobotContextTTLTests(unittest.TestCase):
    def test_temporal_detection_is_kept_while_fresh(self) -> None:
        context = RobotContext()

        context.set_temporal_flag("obstacle_detected", True, now=10.0)

        self.assertTrue(context.has_recent_temporal_flag("obstacle_detected", ttl=0.25, now=10.0))
        self.assertTrue(context.obstacle_detected)

    def test_temporal_detection_expires_after_ttl(self) -> None:
        context = RobotContext()

        context.set_temporal_flag("obstacle_detected", True, now=10.0)
        context.expire_temporal_signals(now=10.3)

        self.assertFalse(context.obstacle_detected)
        self.assertFalse(context.has_recent_temporal_flag("obstacle_detected", ttl=0.25, now=10.3))

    def test_delayed_message_is_ignored_after_event_ttl(self) -> None:
        context = RobotContext()

        context.set_last_event("BALL_CAPTURED", now=10.0)
        context.expire_temporal_signals(now=11.1)

        self.assertFalse(context.has_recent_event("BALL_CAPTURED", ttl=1.0, now=11.1))
        self.assertIsNone(context.last_event)


if __name__ == "__main__":
    unittest.main()
