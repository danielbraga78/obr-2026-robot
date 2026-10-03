import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.config import (
    ALIGN_BALL,
    AVOID_OBSTACLE,
    BOOT,
    CAPTURE_BALL,
    DROP_BALL,
    ENTER_RESCUE,
    FINISH,
    FOLLOW_LINE,
    SEARCH_BALL,
    SEARCH_SAFE_ZONE,
    RobotContext,
)
from raspberry.strategy import Strategy


class FakeClock:
    def __init__(self, now: float = 10.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


class StrategyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.monotonic = patch("raspberry.config.time.monotonic", self.clock)
        self.monotonic.start()
        self.strategy = Strategy()

    def tearDown(self) -> None:
        self.monotonic.stop()

    def test_decision_table(self) -> None:
        cases = (
            ("no signal", FOLLOW_LINE, {}, None, None),
            ("obstacle from boot", BOOT, {"obstacle_detected": True}, AVOID_OBSTACLE, "STOP"),
            ("obstacle while avoiding", AVOID_OBSTACLE, {"obstacle_detected": True}, AVOID_OBSTACLE, "STOP"),
            ("rescue precedes ball", FOLLOW_LINE, {"rescue_detected": True, "ball_detected": True}, ENTER_RESCUE, "STOP"),
            ("ball in line state", FOLLOW_LINE, {"ball_detected": True}, ALIGN_BALL, "STOP"),
            ("ball in finish", FINISH, {"ball_detected": True}, ALIGN_BALL, "STOP"),
            ("ball at capture distance", ALIGN_BALL, {"ball_detected": True, "ball_distance": 19.0}, CAPTURE_BALL, "GRAB"),
            ("ball at distance boundary", ALIGN_BALL, {"ball_detected": True, "ball_distance": 20.0}, None, None),
            ("capture event", CAPTURE_BALL, {"last_event": "BALL_CAPTURED"}, SEARCH_SAFE_ZONE, "STOP"),
            ("safe zone found", SEARCH_SAFE_ZONE, {"safe_zone_detected": True}, DROP_BALL, "RELEASE"),
            ("drop event", DROP_BALL, {"last_event": "BALL_DROPPED"}, SEARCH_BALL, "STOP"),
            (
                "obstacle precedes rescue and ball",
                FOLLOW_LINE,
                {"obstacle_detected": True, "rescue_detected": True, "ball_detected": True},
                AVOID_OBSTACLE,
                "STOP",
            ),
        )

        for name, state, signals, expected_state, expected_command in cases:
            with self.subTest(case=name):
                self.clock.now = 10.0
                context = RobotContext(current_state=state)
                for signal, value in signals.items():
                    setattr(context, signal, value)

                decision = self.strategy.evaluate(context)

                self.assertEqual(decision.next_state, expected_state)
                self.assertEqual(decision.command, expected_command)

    def test_expired_obstacle_and_capture_event_do_not_trigger_strategy(self) -> None:
        context = RobotContext(current_state=CAPTURE_BALL)
        context.obstacle_detected = True
        context.last_event = "BALL_CAPTURED"
        self.clock.now += 1.1

        decision = self.strategy.evaluate(context)

        self.assertIsNone(decision.next_state)
        self.assertIsNone(decision.command)
