"""ROI por detector: cada um analisa a região que interessa a ele."""

import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.config import VISION_ROI_PROFILES
from raspberry.vision.ball_detector import BallDetector
from raspberry.vision.line_detector import LineDetector
from raspberry.vision.pipeline import FrameView, VisionPipeline
from raspberry.vision.safe_zone_detector import SafeZoneDetector


class RecordingDetector:
    def __init__(self, profile: str) -> None:
        self.roi_profile = profile
        self.views = []

    def detect_from_hsv(self, hsv, frame=None, source_frame=None, view=None):
        self.views.append(view)
        return {"profile": view.name if view else None}


class LegacyDetector:
    """Detector antigo: assinatura sem `view`, e sem declarar perfil."""

    def detect_from_hsv(self, hsv, frame=None):
        return {"width": frame.shape[1]}


class PerDetectorRoiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def test_each_detector_gets_its_own_profile(self):
        near = RecordingDetector("near")
        upper = RecordingDetector("upper")
        pipeline = VisionPipeline(detectors={"near": near, "upper": upper})

        pipeline.process_frame(self.frame)

        self.assertEqual(near.views[0].roi, VISION_ROI_PROFILES["near"])
        self.assertEqual(upper.views[0].roi, VISION_ROI_PROFILES["upper"])

    def test_views_are_shared_between_detectors_of_the_same_profile(self):
        first = RecordingDetector("full")
        second = RecordingDetector("full")
        pipeline = VisionPipeline(detectors={"a": first, "b": second})

        result = pipeline.process_frame(self.frame)

        self.assertIs(first.views[0], second.views[0])
        self.assertEqual(len(result.views), 1)

    def test_detector_without_view_parameter_still_runs(self):
        pipeline = VisionPipeline(detectors={"legacy": LegacyDetector()})

        result = pipeline.process_frame(self.frame)

        self.assertEqual(result.detections["legacy"]["width"], pipeline.process_width)

    def test_explicit_roi_overrides_the_profiles(self):
        detector = RecordingDetector("upper")
        pipeline = VisionPipeline(detectors={"d": detector}, roi=(0.0, 0.0, 1.0, 1.0))

        pipeline.process_frame(self.frame)

        self.assertEqual(detector.views[0].roi, (0.0, 0.0, 1.0, 1.0))

    def test_real_detectors_declare_the_expected_profiles(self):
        self.assertEqual(LineDetector().roi_profile, "near")
        self.assertEqual(BallDetector().roi_profile, "full")
        self.assertEqual(SafeZoneDetector().roi_profile, "upper")


class FrameViewMappingTests(unittest.TestCase):
    def _view(self, roi):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        return FrameView(name="test", frame=frame, hsv=frame, roi=roi)

    def test_full_view_maps_to_the_whole_frame(self):
        view = self._view((0.0, 0.0, 1.0, 1.0))

        self.assertAlmostEqual(view.source_y_norm(0), -1.0)
        self.assertAlmostEqual(view.source_y_norm(240), 1.0)
        self.assertAlmostEqual(view.source_x_norm(160), 0.0)

    def test_cropped_view_maps_back_to_the_original_frame(self):
        # A faixa inferior: o topo da view é 55% da altura do quadro original.
        view = self._view((0.0, 0.55, 1.0, 1.0))

        self.assertAlmostEqual(view.source_y_norm(0), 0.1)
        self.assertAlmostEqual(view.source_y_norm(240), 1.0)

    def test_same_view_row_means_different_distances_per_profile(self):
        near = self._view((0.0, 0.55, 1.0, 1.0))
        full = self._view((0.0, 0.0, 1.0, 1.0))

        # Esta é a razão de FrameView existir: sem o mapa, a mesma linha da
        # imagem seria lida como a mesma distância nos dois perfis.
        self.assertNotAlmostEqual(near.source_y_norm(120), full.source_y_norm(120))


class BallDistanceUsesTheViewTests(unittest.TestCase):
    def test_distance_accounts_for_the_crop(self):
        detector = BallDetector()
        frame = np.full((480, 640, 3), 200, dtype=np.uint8)
        cv2.circle(frame, (320, 400), 30, (25, 25, 25), thickness=-1)

        full = VisionPipeline(detectors={"ball": detector}, roi=(0.0, 0.0, 1.0, 1.0)).process_frame(frame)
        cropped = VisionPipeline(detectors={"ball": detector}, roi=(0.0, 0.55, 1.0, 1.0)).process_frame(frame)

        # A bola é a mesma e está no mesmo lugar do mundo: a distância estimada
        # não pode depender de qual recorte a enxergou.
        self.assertAlmostEqual(
            full.detections["ball"].distance,
            cropped.detections["ball"].distance,
            delta=1.5,
        )


if __name__ == "__main__":
    unittest.main()
