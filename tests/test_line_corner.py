"""Curvas de 90 graus: a linha some do centro e o robô precisa atacá-la.

O sintoma que motivou estes testes: nas curvas de 90 graus o robô perdia a
linha e passava reto.
"""

import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.config import BASE_SPEED, LINE_LOST_GRACE_CYCLES, MAX_STEER, MIN_SPEED, RobotContext
from raspberry.states.follow_line import FollowLineState
from raspberry.vision.line_detector import LineDetection, LineDetector


def path_scene(points, line_width: int = 40, background: int = 230, line_value: int = 30):
    frame = np.full((240, 320, 3), background, dtype=np.uint8)
    cv2.polylines(frame, [np.array(points, dtype=np.int32)], False, (line_value,) * 3, line_width)
    return frame


def parse_move(command: str):
    parts = command.split(",")
    assert parts[0] == "MOVE", command
    return int(parts[1]), int(parts[2]), int(parts[3])


class LineBandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.detector = LineDetector(mode="adaptive")

    def test_straight_line_has_no_heading(self):
        detection = self.detector.detect(path_scene([(160, 240), (160, 0)]))

        self.assertAlmostEqual(detection.heading, 0.0, delta=0.05)
        self.assertFalse(detection.corner)

    def test_error_comes_from_the_band_nearest_the_robot(self):
        # A linha entra pela base em x=160 e sobe indo para a direita. O erro
        # deve refletir onde o robô está, não a média do caminho todo.
        detection = self.detector.detect(path_scene([(160, 240), (300, 0)]))

        # O centroide do caminho todo fica perto de 230; a faixa próxima fica
        # bem abaixo disso, porque mede onde a linha está agora.
        self.assertLess(detection.near_x, 200)
        self.assertGreater(detection.far_x, 250)
        self.assertGreater(detection.far_x, detection.near_x)

    def test_ninety_degree_corner_to_the_right_is_flagged(self):
        detection = self.detector.detect(path_scene([(160, 240), (160, 60), (320, 60)]))

        self.assertTrue(detection.corner, f"heading={detection.heading:.2f}")
        self.assertEqual(detection.corner_side, 1)
        self.assertGreater(detection.heading, 0)

    def test_ninety_degree_corner_to_the_left_is_flagged(self):
        detection = self.detector.detect(path_scene([(160, 240), (160, 60), (0, 60)]))

        self.assertTrue(detection.corner, f"heading={detection.heading:.2f}")
        self.assertEqual(detection.corner_side, -1)
        self.assertLess(detection.heading, 0)

    def test_corner_is_seen_while_the_line_is_still_centered(self):
        """O ponto do exercício: reagir antes de a linha sair do centro."""
        detection = self.detector.detect(path_scene([(160, 240), (160, 60), (320, 60)]))

        self.assertLess(abs(detection.error), 30)  # ainda centrada
        self.assertTrue(detection.corner)  # e já sabemos que a curva vem


class CornerSteeringTests(unittest.TestCase):
    def test_heading_adds_steering_before_the_error_grows(self):
        centered = LineDetection(center_x=160.0, error=0.0, frame_width=320)
        with_corner = LineDetection(center_x=160.0, error=0.0, frame_width=320, heading=0.8, corner=True, corner_side=1)

        straight = FollowLineState().execute(_context(centered), None, {})
        turning = FollowLineState().execute(_context(with_corner), None, {})

        _, _, straight_wz = parse_move(straight.command)
        _, _, corner_wz = parse_move(turning.command)

        self.assertEqual(straight_wz, 0)
        self.assertGreater(corner_wz, 0)

    def test_corner_slows_the_robot_down(self):
        detection = LineDetection(center_x=160.0, error=0.0, frame_width=320, heading=0.9, corner=True, corner_side=1)

        speed, _, _ = parse_move(FollowLineState().execute(_context(detection), None, {}).command)

        self.assertEqual(speed, MIN_SPEED)

    def test_line_lost_right_after_a_corner_turns_instead_of_going_straight(self):
        """Era exatamente aqui que o robô passava reto."""
        state = FollowLineState()
        corner = LineDetection(center_x=200.0, error=40.0, frame_width=320, heading=0.7, corner=True, corner_side=1)
        state.execute(_context(corner), None, {})

        result = state.execute(_context(LineDetection()), None, {})

        speed, _, steering = parse_move(result.command)
        self.assertEqual(result.next_state, "FOLLOW_LINE")
        self.assertEqual(speed, 0)  # pivô: não avança para longe da linha
        self.assertEqual(steering, MAX_STEER)  # para o lado da curva

    def test_corner_memory_is_forgotten_after_giving_up(self):
        state = FollowLineState()
        corner = LineDetection(center_x=200.0, error=40.0, frame_width=320, heading=0.7, corner=True, corner_side=1)
        state.execute(_context(corner), None, {})

        for _ in range(LINE_LOST_GRACE_CYCLES + 1):
            result = state.execute(_context(LineDetection()), None, {})

        self.assertEqual(result.command, "STOP")
        self.assertEqual(state._last_corner_side, 0)


def _context(detection):
    context = RobotContext()
    context.last_detections = {"line": detection}
    return context


if __name__ == "__main__":
    unittest.main()
