import sys
import time
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.runtime import ExecutionLoopController
from raspberry.vision.pipeline import VisionPipeline


class DummyDetector:
    def detect_from_hsv(self, hsv, frame=None, source_frame=None):
        return {"ok": True}


class VisionResultFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.frame = np.zeros((240, 320, 3), dtype=np.uint8)
        self.pipeline = VisionPipeline(detectors={"dummy": DummyDetector()})

    def test_result_carries_capture_timestamp(self):
        captured_at = time.monotonic() - 5.0
        result = self.pipeline.process_frame(self.frame, captured_at=captured_at)

        self.assertEqual(result.captured_at, captured_at)

    def test_capture_timestamp_defaults_to_now(self):
        result = self.pipeline.process_frame(self.frame)

        self.assertAlmostEqual(result.captured_at, time.monotonic(), delta=1.0)

    def test_old_frame_is_stale_and_fresh_frame_is_not(self):
        """Uma pausa longa não pode envenenar os resultados seguintes.

        No bookkeeping anterior, um único ciclo acima de max_frame_age fazia todo
        resultado posterior ser considerado velho para sempre.
        """
        controller = ExecutionLoopController(target_hz=20.0, max_frame_age=0.25)

        stale = self.pipeline.process_frame(self.frame, captured_at=time.monotonic() - 3.0)
        self.assertTrue(controller.is_result_stale(stale.captured_at))

        fresh = self.pipeline.process_frame(self.frame)
        self.assertFalse(controller.is_result_stale(fresh.captured_at))


if __name__ == "__main__":
    unittest.main()
