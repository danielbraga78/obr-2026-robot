import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.runtime import ExecutionLoopController


class RuntimeControllerTests(unittest.TestCase):
    def test_stale_result_is_rejected_after_timeout(self):
        controller = ExecutionLoopController(target_hz=10.0, max_frame_age=0.01, now_fn=lambda: 0.0)
        self.assertTrue(controller.is_result_stale(0.0, now=0.02))

    def test_average_latency_tracks_recent_samples(self):
        controller = ExecutionLoopController(target_hz=10.0, now_fn=lambda: 0.0)
        controller.record_latency(5.0)
        controller.record_latency(15.0)
        self.assertEqual(controller.average_latency_ms, 10.0)


if __name__ == "__main__":
    unittest.main()
