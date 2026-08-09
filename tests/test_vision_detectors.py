import unittest
from unittest.mock import patch

import cv2
import numpy as np

from raspberry.main import build_vision_detectors
from raspberry.vision.ball_detector import BallDetector
from raspberry.vision.obstacle_detector import VisionBasedObstacleDetector
from raspberry.vision.rescue_detector import RescueDetector
from raspberry.vision.safe_zone_detector import SafeZoneDetector


class ColorDetectorThresholdTests(unittest.TestCase):
    def _make_hsv_frame(self, height=120, width=160, patch_size=0, hue=30):
        hsv = np.zeros((height, width, 3), dtype=np.uint8)
        if patch_size > 0:
            y0 = (height - patch_size) // 2
            x0 = (width - patch_size) // 2
            hsv[y0:y0 + patch_size, x0:x0 + patch_size, 0] = hue
            hsv[y0:y0 + patch_size, x0:x0 + patch_size, 1] = 255
            hsv[y0:y0 + patch_size, x0:x0 + patch_size, 2] = 255
        return hsv

    def test_rescue_detector_rejects_empty_mask(self):
        detector = RescueDetector(debounce_frames=1)
        hsv = self._make_hsv_frame()
        self.assertFalse(detector.detect_from_hsv(hsv, frame=np.zeros((120, 160, 3), dtype=np.uint8)))

    def test_rescue_detector_rejects_tiny_area(self):
        detector = RescueDetector(debounce_frames=1)
        hsv = self._make_hsv_frame(patch_size=3)
        self.assertFalse(detector.detect_from_hsv(hsv, frame=np.zeros((120, 160, 3), dtype=np.uint8)))

    def test_rescue_detector_accepts_intermediate_area(self):
        detector = RescueDetector(debounce_frames=1)
        hsv = self._make_hsv_frame(patch_size=20)
        self.assertTrue(detector.detect_from_hsv(hsv, frame=np.zeros((120, 160, 3), dtype=np.uint8)))

    def test_rescue_detector_accepts_sufficient_area(self):
        detector = RescueDetector(debounce_frames=1)
        hsv = self._make_hsv_frame(patch_size=80)
        self.assertTrue(detector.detect_from_hsv(hsv, frame=np.zeros((120, 160, 3), dtype=np.uint8)))

    def test_safe_zone_detector_matches_across_resolutions(self):
        detector = SafeZoneDetector(debounce_frames=1)
        for height, width in ((120, 160), (240, 320), (480, 640)):
            with self.subTest(height=height, width=width):
                hsv = self._make_hsv_frame(height=height, width=width, patch_size=min(40, height // 2), hue=40)
                self.assertTrue(detector.detect_from_hsv(hsv, frame=np.zeros((height, width, 3), dtype=np.uint8)))


class BallDetectorTests(unittest.TestCase):
    def _make_ball_frame(self, radius: int):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        hsv = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.circle(hsv, (160, 120), radius, (30, 255, 255), thickness=-1)
        frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        return frame, hsv

    def test_ball_detector_distance_is_smaller_for_bigger_ball(self):
        detector = BallDetector()
        small_frame, small_hsv = self._make_ball_frame(6)
        large_frame, large_hsv = self._make_ball_frame(24)

        small_ball = detector.detect_from_hsv(small_hsv, frame=small_frame, source_frame=small_frame, roi=(0.0, 0.0, 1.0, 1.0))
        large_ball = detector.detect_from_hsv(large_hsv, frame=large_frame, source_frame=large_frame, roi=(0.0, 0.0, 1.0, 1.0))

        self.assertIsNotNone(small_ball)
        self.assertIsNotNone(large_ball)
        self.assertGreater(small_ball.distance, large_ball.distance)
        self.assertGreater(large_ball.confidence, small_ball.confidence)


class ObstacleDetectorTests(unittest.TestCase):
    def test_build_vision_detectors_respects_configuration(self):
        with patch("raspberry.main.OBSTACLE_DETECTION_ENABLED", True), patch("raspberry.main.SENSORS_ENABLED", {"vision_obstacle_detection": True}):
            detectors_enabled = build_vision_detectors()
            self.assertIn("obstacle", detectors_enabled)

        with patch("raspberry.main.OBSTACLE_DETECTION_ENABLED", False), patch("raspberry.main.SENSORS_ENABLED", {"vision_obstacle_detection": True}):
            detectors_disabled = build_vision_detectors()
            self.assertNotIn("obstacle", detectors_disabled)

    def test_obstacle_detector_detects_dark_region(self):
        detector = VisionBasedObstacleDetector(confidence_threshold=0.0, min_obstacle_area=10)
        frame = np.full((120, 160, 3), 200, dtype=np.uint8)
        cv2.rectangle(frame, (40, 60), (110, 100), (0, 0, 0), thickness=-1)
        detector.set_frame(frame)
        result = detector.detect()
        self.assertTrue(result.obstacle_detected)
        self.assertGreaterEqual(result.confidence, 0.0)

    def test_obstacle_detector_rejects_empty_frame(self):
        detector = VisionBasedObstacleDetector(confidence_threshold=0.0)
        detector.set_frame(np.zeros((120, 160, 3), dtype=np.uint8))
        result = detector.detect()
        self.assertFalse(result.obstacle_detected)


if __name__ == "__main__":
    unittest.main()
