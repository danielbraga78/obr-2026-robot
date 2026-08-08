import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.telemetry import format_arduino_payload


class TelemetryTests(unittest.TestCase):
    def test_format_arduino_payload_includes_detections_and_command(self):
        class DummyDetection:
            def __init__(self, error=None, confidence=0.9, distance=None):
                self.error = error
                self.confidence = confidence
                self.distance = distance

        context = type("Context", (), {})()
        context.current_state = "FOLLOW_LINE"
        context.ball_detected = True
        context.ball_distance = 12.5
        context.rescue_detected = False
        context.safe_zone_detected = True
        context.obstacle_detected = True
        context.last_detections = {
            "line": DummyDetection(error=-3.2, confidence=0.8),
            "ball": DummyDetection(distance=12.5),
        }

        message = format_arduino_payload(context, "FORWARD")

        self.assertIn("FORWARD", message)
        self.assertIn("FOLLOW_LINE", message)
        self.assertIn("line", message)
        self.assertIn("ball", message)
        self.assertIn("obstacle=True", message)


if __name__ == "__main__":
    unittest.main()
