import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.vision.line_detector import LineDetector


def scene(background: int, line_value: int, line_x: int = 160, line_width: int = 40, width: int = 320, height: int = 240):
    """Cena BGR: piso uniforme com uma faixa vertical mais escura."""
    frame = np.full((height, width, 3), background, dtype=np.uint8)
    frame[:, line_x - line_width // 2: line_x + line_width // 2] = line_value
    return frame


class AdaptiveLineDetectorTests(unittest.TestCase):
    def test_detects_line_too_claro_para_o_limiar_hsv_fixo(self):
        """Linha com V=120: acima do LINE_MAX fixo (V<=80), que a rejeitava."""
        frame = scene(background=230, line_value=120, line_x=200)

        adaptive = LineDetector(mode="adaptive").detect(frame)
        fixed = LineDetector(mode="hsv").detect(frame)

        self.assertIsNotNone(adaptive.error, f"adaptativo falhou: {adaptive.reason}")
        self.assertAlmostEqual(adaptive.center_x, 200, delta=6)
        self.assertIsNone(fixed.error)  # o modo antigo perde essa linha

    def test_detects_dark_line_under_dim_light(self):
        frame = scene(background=90, line_value=20, line_x=100)

        detection = LineDetector(mode="adaptive").detect(frame)

        self.assertIsNotNone(detection.error, f"falhou: {detection.reason}")
        self.assertAlmostEqual(detection.center_x, 100, delta=6)

    def test_error_sign_matches_line_position(self):
        detector = LineDetector(mode="adaptive")

        left = detector.detect(scene(230, 60, line_x=80))
        right = detector.detect(scene(230, 60, line_x=240))

        self.assertLess(left.error, 0)
        self.assertGreater(right.error, 0)

    def test_uniform_frame_is_rejected_with_reason(self):
        frame = np.full((240, 320, 3), 200, dtype=np.uint8)

        detection = LineDetector(mode="adaptive").detect(frame)

        self.assertIsNone(detection.error)
        self.assertIsNotNone(detection.reason)

    def test_low_contrast_frame_is_rejected(self):
        frame = scene(background=200, line_value=190)

        detection = LineDetector(mode="adaptive").detect(frame)

        self.assertIsNone(detection.error)
        self.assertIn("contraste", detection.reason)

    def test_mostly_dark_frame_is_rejected_by_coverage(self):
        frame = scene(background=230, line_value=30, line_x=160, line_width=300)

        detection = LineDetector(mode="adaptive").detect(frame)

        self.assertIsNone(detection.error)
        self.assertIn("cobre", detection.reason)

    def test_mask_is_exposed_for_the_preview(self):
        detector = LineDetector(mode="adaptive")

        detector.detect(scene(230, 40, line_x=160))

        self.assertIsNotNone(detector.last_mask)
        self.assertEqual(detector.last_mask.shape, (240, 320))
        self.assertGreater(int(np.count_nonzero(detector.last_mask)), 0)

    def test_detection_reports_threshold_and_coverage(self):
        detection = LineDetector(mode="adaptive").detect(scene(230, 40))

        self.assertIsNotNone(detection.threshold)
        self.assertGreater(detection.coverage, 0.0)
        self.assertLess(detection.coverage, 0.6)

    def test_hsv_mode_still_works_for_very_dark_lines(self):
        detection = LineDetector(mode="hsv").detect(scene(230, 20))

        self.assertIsNotNone(detection.error)


if __name__ == "__main__":
    unittest.main()
