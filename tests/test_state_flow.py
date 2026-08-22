"""Fluxo de estados de ponta a ponta, como o loop principal executa.

Reproduz a sequência Strategy -> máquina -> comando sem câmera nem serial.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.config import LINE_LOST_GRACE_CYCLES, RobotContext
from raspberry.state_machine import RobotStateMachine
from raspberry.states.alignment import AlignBallState
from raspberry.states.avoid_obstacle import AvoidObstacleState
from raspberry.states.calibration import CalibrationState
from raspberry.states.capture_ball import CaptureBallState
from raspberry.states.drop_ball import DropBallState
from raspberry.states.enter_rescue import EnterRescueState
from raspberry.states.finish import FinishState
from raspberry.states.follow_line import FollowLineState
from raspberry.states.search_ball import SearchBallState
from raspberry.states.search_line import SearchLineState
from raspberry.states.search_safe_zone import SearchSafeZoneState
from raspberry.strategy import Strategy
from raspberry.vision.ball_detector import Ball
from raspberry.vision.line_detector import LineDetection


def build_machine():
    return RobotStateMachine({
        "BOOT": CalibrationState(),
        "CALIBRATION": CalibrationState(),
        "FOLLOW_LINE": FollowLineState(),
        "SEARCH_LINE": SearchLineState(),
        "AVOID_OBSTACLE": AvoidObstacleState(),
        "ENTER_RESCUE": EnterRescueState(),
        "SEARCH_BALL": SearchBallState(),
        "ALIGN_BALL": AlignBallState(),
        "CAPTURE_BALL": CaptureBallState(),
        "SEARCH_SAFE_ZONE": SearchSafeZoneState(),
        "DROP_BALL": DropBallState(),
        "FINISH": FinishState(),
    })


class Robot:
    """Mesma sequência de raspberry/main.py, sem I/O."""

    def __init__(self):
        self.machine = build_machine()
        self.strategy = Strategy()
        self.context = RobotContext()
        self.commands = []
        self.executed_states = []

    def tick(self, line=None, ball=None):
        detections = {}
        if line is not None:
            detections["line"] = line
        if ball is not None:
            detections["ball"] = ball
        self.context.last_detections = detections
        # Mesma derivação de _update_context_from_result.
        self.context.ball_detected = ball is not None
        if ball is not None:
            self.context.ball_distance = ball.distance
        self.context.current_state = self.machine.current_state
        decision = self.strategy.evaluate(self.context)
        if decision.next_state:
            self.machine.transition_to(decision.next_state)
            self.context.current_state = self.machine.current_state
        self.executed_states.append(self.machine.current_state)
        result = self.machine.run_once(self.context, None, {})
        if result.command:
            self.commands.append(result.command)
        return result


ON_LINE = LineDetection(center_x=170.0, error=10.0, confidence=1.0, frame_width=320)
NO_LINE = LineDetection(reason="nenhum contorno", frame_width=320)
CENTERED_BALL = Ball(x=160.0, y=120.0, radius=20.0, distance=10.0, confidence=0.9)
FAR_BALL = Ball(x=160.0, y=120.0, radius=6.0, distance=45.0, confidence=0.6)


class StateFlowTests(unittest.TestCase):
    def test_boot_reaches_follow_line_and_moves(self):
        """Antes ficava preso em BOOT mandando STOP para sempre."""
        robot = Robot()

        for _ in range(4):
            robot.tick(ON_LINE)

        self.assertEqual(robot.executed_states[0], "BOOT")
        self.assertIn("FOLLOW_LINE", robot.executed_states)
        self.assertTrue(any(c.startswith("MOVE,") for c in robot.commands), robot.commands)

    def test_never_stays_in_boot(self):
        robot = Robot()

        for _ in range(10):
            robot.tick(ON_LINE)

        self.assertEqual(robot.executed_states.count("BOOT"), 1)

    def test_lost_line_actually_runs_search_line(self):
        """SEARCH_LINE nunca executava: a Strategy forçava FOLLOW_LINE de volta."""
        robot = Robot()
        for _ in range(3):
            robot.tick(ON_LINE)

        for _ in range(LINE_LOST_GRACE_CYCLES + 2):
            robot.tick(NO_LINE)

        self.assertIn("SEARCH_LINE", robot.executed_states)

    def test_recovers_to_follow_line_after_finding_the_line(self):
        robot = Robot()
        for _ in range(3):
            robot.tick(ON_LINE)
        robot.tick(NO_LINE)
        robot.tick(NO_LINE)

        robot.tick(ON_LINE)
        result = robot.tick(ON_LINE)

        self.assertEqual(robot.machine.current_state, "FOLLOW_LINE")
        self.assertTrue(result.command.startswith("MOVE,"))

    def test_obstacle_is_handled_once_and_released(self):
        """O latch de obstáculo prendia o robô em AVOID_OBSTACLE para sempre."""
        robot = Robot()
        for _ in range(3):
            robot.tick(ON_LINE)

        robot.context.obstacle_detected = True
        robot.tick(ON_LINE)  # entra no desvio e consome o evento
        self.assertEqual(robot.executed_states[-1], "AVOID_OBSTACLE")
        self.assertFalse(robot.context.obstacle_detected)

        for _ in range(3):
            robot.tick(ON_LINE)
        self.assertEqual(robot.machine.current_state, "FOLLOW_LINE")

    def test_ball_alignment_advances_to_capture(self):
        """Com a bola visível, ALIGN_BALL era forçado em todo ciclo e CAPTURE_BALL
        ficava inalcançável, porque a regra da bola vinha antes na Strategy."""
        robot = Robot()
        for _ in range(3):
            robot.tick(ON_LINE)

        robot.tick(ON_LINE, ball=CENTERED_BALL)
        self.assertEqual(robot.executed_states[-1], "ALIGN_BALL")

        robot.tick(ON_LINE, ball=CENTERED_BALL)
        self.assertEqual(robot.executed_states[-1], "CAPTURE_BALL")

    def test_far_ball_keeps_aligning(self):
        robot = Robot()
        for _ in range(3):
            robot.tick(ON_LINE)

        for _ in range(3):
            robot.tick(ON_LINE, ball=FAR_BALL)

        self.assertEqual(robot.executed_states[-1], "ALIGN_BALL")


if __name__ == "__main__":
    unittest.main()
