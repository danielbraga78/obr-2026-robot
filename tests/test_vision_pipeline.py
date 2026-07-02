import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.vision.pipeline import VisionPipeline


class DummyDetector:
    def detect(self, frame):
        raise AssertionError("detect() should not be used by the new pipeline")

    def detect_from_hsv(self, hsv, frame=None):
        return {"ok": True}


class VisionPipelineTests(unittest.TestCase):
    def test_pipeline_process_frame_uses_shared_hsv_path(self):
        frame = np.zeros((80, 80, 3), dtype=np.uint8)
        pipeline = VisionPipeline(camera_manager=None, detectors={"dummy": DummyDetector()})

        result = pipeline.process_frame(frame)

        self.assertIsNotNone(result)
        self.assertEqual(result.detections["dummy"]["ok"], True)


if __name__ == "__main__":
    unittest.main()
