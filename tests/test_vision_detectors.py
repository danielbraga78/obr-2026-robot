"""Detectores sobre cenas sintéticas com as cores reais da arena.

As cenas antigas usavam manchas amarelas, cor que não existe na prova: as bolas
são prateada e preta, as zonas seguras têm parede verde e vermelha, e a entrada
da área de resgate é uma faixa prateada.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.main import build_vision_detectors
from raspberry.vision.ball_detector import BLACK, SILVER, BallDetector
from raspberry.vision.obstacle_detector import VisionBasedObstacleDetector
from raspberry.vision.rescue_detector import RescueDetector
from raspberry.vision.safe_zone_detector import GREEN, RED, SafeZoneDetector

FLOOR = (200, 200, 200)  # Piso claro da arena, em BGR
BLACK_BGR = (25, 25, 25)
SILVER_BGR = (235, 235, 235)
GREEN_BGR = (60, 170, 60)
RED_BGR = (50, 50, 190)


def floor_frame(height=240, width=320):
    return np.full((height, width, 3), FLOOR, dtype=np.uint8)


def with_ball(frame, center, radius, color):
    cv2.circle(frame, center, radius, color, thickness=-1)
    return frame


def with_band(frame, y0, y1, color, x0=0, x1=None):
    x1 = frame.shape[1] if x1 is None else x1
    cv2.rectangle(frame, (x0, y0), (x1, y1), color, thickness=-1)
    return frame


class BallDetectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.detector = BallDetector()

    def test_detects_black_ball(self):
        frame = with_ball(floor_frame(), (160, 120), 20, BLACK_BGR)

        ball = self.detector.detect(frame)

        self.assertIsNotNone(ball)
        self.assertEqual(ball.color, BLACK)

    def test_detects_silver_ball(self):
        frame = with_ball(floor_frame(), (160, 120), 20, SILVER_BGR)
        # Reflexo especular: o que caracteriza a prateada
        cv2.circle(frame, (154, 114), 5, (255, 255, 255), thickness=-1)

        ball = self.detector.detect(frame)

        self.assertIsNotNone(ball)
        self.assertEqual(ball.color, SILVER)

    def test_black_line_is_not_a_ball(self):
        # Mesma cor da bola preta, forma alongada: só a forma distingue.
        frame = with_band(floor_frame(), 100, 116, BLACK_BGR)

        self.assertIsNone(self.detector.detect(frame))

    def test_silver_line_is_not_a_ball(self):
        frame = with_band(floor_frame(), 100, 112, SILVER_BGR)

        self.assertIsNone(self.detector.detect(frame))

    def test_colored_object_is_not_a_ball(self):
        frame = with_ball(floor_frame(), (160, 120), 20, (40, 40, 200))

        self.assertIsNone(self.detector.detect(frame))

    def test_tiny_blob_is_rejected(self):
        frame = with_ball(floor_frame(), (160, 120), 3, BLACK_BGR)

        self.assertIsNone(self.detector.detect(frame))

    def test_lower_ball_is_closer(self):
        near = self.detector.detect(with_ball(floor_frame(), (160, 200), 20, BLACK_BGR))
        far = self.detector.detect(with_ball(floor_frame(), (160, 60), 20, BLACK_BGR))

        self.assertIsNotNone(near)
        self.assertIsNotNone(far)
        self.assertLess(near.distance, far.distance)

    def test_horizontal_position_is_normalized(self):
        left = self.detector.detect(with_ball(floor_frame(), (60, 120), 20, BLACK_BGR))
        right = self.detector.detect(with_ball(floor_frame(), (260, 120), 20, BLACK_BGR))

        self.assertLess(left.x_norm, -0.2)
        self.assertGreater(right.x_norm, 0.2)

    def test_picks_the_closest_of_two_balls(self):
        frame = with_ball(floor_frame(), (80, 60), 20, BLACK_BGR)
        with_ball(frame, (240, 200), 20, BLACK_BGR)

        ball = self.detector.detect(frame)

        self.assertGreater(ball.x_norm, 0.0)


class SafeZoneDetectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.detector = SafeZoneDetector(debounce_frames=1)

    def test_detects_green_wall(self):
        frame = with_band(floor_frame(), 0, 40, GREEN_BGR)

        zone = self.detector.detect(frame)

        self.assertIsNotNone(zone)
        self.assertEqual(zone.color, GREEN)

    def test_detects_red_wall(self):
        # Vermelho fica na dobra do matiz: sem as duas faixas, não é detectado.
        frame = with_band(floor_frame(), 0, 40, RED_BGR)

        zone = self.detector.detect(frame)

        self.assertIsNotNone(zone)
        self.assertEqual(zone.color, RED)

    def test_empty_scene_is_not_a_zone(self):
        self.assertIsNone(self.detector.detect(floor_frame()))

    def test_tiny_reflection_is_rejected(self):
        frame = with_band(floor_frame(), 0, 4, GREEN_BGR, x0=0, x1=10)

        self.assertIsNone(self.detector.detect(frame))

    def test_debounce_requires_consecutive_frames(self):
        detector = SafeZoneDetector(debounce_frames=2)
        frame = with_band(floor_frame(), 0, 40, GREEN_BGR)

        self.assertIsNone(detector.detect(frame))
        self.assertIsNotNone(detector.detect(frame))

    def test_bearing_points_to_the_wall_side(self):
        frame = with_band(floor_frame(), 0, 40, GREEN_BGR, x0=0, x1=90)

        zone = self.detector.detect(frame)

        self.assertLess(zone.x_norm, 0.0)


class RescueDetectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.detector = RescueDetector(debounce_frames=1)

    def test_detects_silver_entrance_band(self):
        frame = with_band(floor_frame(), 150, 162, SILVER_BGR)

        self.assertTrue(self.detector.detect(frame))

    def test_empty_floor_is_not_the_entrance(self):
        self.assertFalse(self.detector.detect(floor_frame()))

    def test_silver_ball_is_not_the_entrance(self):
        # Mesma cor da faixa, forma compacta: não é a entrada.
        frame = with_ball(floor_frame(), (160, 120), 22, SILVER_BGR)

        self.assertFalse(self.detector.detect(frame))

    def test_black_line_is_not_the_entrance(self):
        frame = with_band(floor_frame(), 150, 162, BLACK_BGR)

        self.assertFalse(self.detector.detect(frame))

    def test_debounce_requires_consecutive_frames(self):
        detector = RescueDetector(debounce_frames=2)
        frame = with_band(floor_frame(), 150, 162, SILVER_BGR)

        self.assertFalse(detector.detect(frame))
        self.assertTrue(detector.detect(frame))


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

    def test_black_line_is_not_an_obstacle(self):
        # A linha é escura e grande na faixa próxima: passava por obstáculo em
        # todo quadro do seguidor de linha.
        detector = VisionBasedObstacleDetector(confidence_threshold=0.0, min_obstacle_area=10)
        frame = np.full((120, 160, 3), 200, dtype=np.uint8)
        cv2.rectangle(frame, (70, 40), (86, 119), (0, 0, 0), thickness=-1)
        detector.set_frame(frame)

        self.assertFalse(detector.detect().obstacle_detected)


if __name__ == "__main__":
    unittest.main()
