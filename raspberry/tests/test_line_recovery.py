import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from raspberry.config import (
    LINE_RECOVERY_CONFIRM_OBSERVATIONS,
    LINE_SEARCH_MAX_PULSES,
    LINE_SEARCH_PAUSE_SECONDS,
    LINE_SEARCH_PULSE_SECONDS,
    LINE_SEARCH_TIMEOUT_SECONDS,
    RobotContext,
)
from raspberry.state_machine import RobotStateMachine
from raspberry.states.follow_line import FollowLineState
from raspberry.states.search_line import SearchLineState
from raspberry.vision.line_detector import LineDetection


def build_machine():
    return RobotStateMachine({
        "FOLLOW_LINE": FollowLineState(),
        "SEARCH_LINE": SearchLineState(),
    })


def observe(context, detection, now):
    context.control_time = now
    context.line_observation_sequence += 1
    context.line_observation_at = now
    context.last_detections = {"line": detection}


def tick(machine, context, now):
    context.control_time = now
    result = machine.run_once(context, None, {})
    context.current_state = machine.current_state
    return result


class LineRecoveryTests(unittest.TestCase):
    def _lose_line_after_corner(self, side):
        machine = build_machine()
        context = RobotContext(current_state="FOLLOW_LINE")
        machine.current_state = "FOLLOW_LINE"
        observe(
            context,
            LineDetection(error=0.0, frame_width=320, confidence=0.8,
                          heading=0.6 * side, corner=True, corner_side=side),
            0.0,
        )
        tick(machine, context, 0.0)

        invalid = LineDetection(error=None, frame_width=320, confidence=0.0)
        for index in range(1, 5):
            observe(context, invalid, index * 0.05)
            result = tick(machine, context, index * 0.05)
        self.assertEqual(machine.current_state, "SEARCH_LINE")
        self.assertEqual(result.command, "STOP")

        result = tick(machine, context, 0.25)
        self.assertTrue(result.command.startswith("MOVE,0,0,"))
        self.assertEqual(int(result.command.split(",")[3]) * side, abs(int(result.command.split(",")[3])))
        return machine, context

    def test_loss_during_left_and_right_curves_searches_toward_last_corner(self):
        for side in (-1, 1):
            with self.subTest(side=side):
                machine, context = self._lose_line_after_corner(side)
                result = tick(machine, context, 0.30)
                self.assertEqual(int(result.command.split(",")[3]) * side, abs(int(result.command.split(",")[3])))

    def test_straight_loss_uses_calibratable_default_direction(self):
        machine = build_machine()
        context = RobotContext(current_state="FOLLOW_LINE")
        machine.current_state = "FOLLOW_LINE"
        observe(context, LineDetection(error=0, frame_width=320, confidence=1), 0.0)
        tick(machine, context, 0.0)
        invalid = LineDetection(error=None, frame_width=320)
        for index in range(1, 5):
            observe(context, invalid, index * 0.05)
            result = tick(machine, context, index * 0.05)
        self.assertEqual(machine.current_state, "SEARCH_LINE")
        result = tick(machine, context, 0.25)
        self.assertEqual(int(result.command.split(",")[3]), 110)

    def test_recovery_requires_new_stable_observations_then_resets_pid(self):
        machine, context = self._lose_line_after_corner(1)
        line = LineDetection(error=4.0, frame_width=320, confidence=0.8)
        for index in range(1, LINE_RECOVERY_CONFIRM_OBSERVATIONS):
            observe(context, line, 0.30 + index * 0.05)
            result = tick(machine, context, 0.30 + index * 0.05)
            self.assertEqual(machine.current_state, "SEARCH_LINE")
            self.assertEqual(result.command, "STOP")

        observe(context, line, 0.50)
        result = tick(machine, context, 0.50)
        self.assertEqual(machine.current_state, "FOLLOW_LINE")
        self.assertEqual(result.command, "STOP")
        self.assertTrue(context.line_controller_reset)

        result = tick(machine, context, 0.55)
        self.assertTrue(result.command.startswith("MOVE,"))
        self.assertFalse(context.line_controller_reset)
        self.assertEqual(machine.states["FOLLOW_LINE"].pid.integral, 0.0)

    def test_false_or_expired_observations_do_not_accumulate_recovery(self):
        machine, context = self._lose_line_after_corner(-1)
        valid = LineDetection(error=0.0, frame_width=320, confidence=0.8)
        observe(context, valid, 0.30)
        tick(machine, context, 0.30)
        observe(context, LineDetection(error=None, frame_width=320), 0.35)
        tick(machine, context, 0.35)
        context.line_observation_sequence += 1
        context.line_observation_at = 0.0
        context.last_detections = {"line": valid}
        result = tick(machine, context, 0.40)
        self.assertEqual(machine.current_state, "SEARCH_LINE")
        self.assertNotEqual(result.next_state, "FOLLOW_LINE")

    def test_search_pulses_are_bounded_and_timeout_holds_stop(self):
        search = SearchLineState()
        context = RobotContext()
        context.control_time = 0.0
        context.line_recovery_direction = -1
        active_seconds = 0.0
        period = LINE_SEARCH_PULSE_SECONDS + LINE_SEARCH_PAUSE_SECONDS
        for pulse in range(LINE_SEARCH_MAX_PULSES):
            start = pulse * period
            context.control_time = start
            active = search.execute(context, None, {})
            expected_direction = -1 if pulse < 2 or pulse >= 4 else 1
            self.assertEqual(
                int(active.command.split(",")[3]) * expected_direction,
                abs(int(active.command.split(",")[3])),
            )
            active_seconds += LINE_SEARCH_PULSE_SECONDS
            context.control_time = start + LINE_SEARCH_PULSE_SECONDS
            self.assertEqual(search.execute(context, None, {}).command, "STOP")
        self.assertEqual(active_seconds, LINE_SEARCH_MAX_PULSES * LINE_SEARCH_PULSE_SECONDS)

        context.control_time = LINE_SEARCH_TIMEOUT_SECONDS + 0.01
        context.line_observation_sequence += 1
        context.line_observation_at = context.control_time
        context.last_detections = {
            "line": LineDetection(error=0.0, frame_width=320, confidence=0.8)
        }
        result = search.execute(context, None, {})
        self.assertEqual(result.command, "STOP")
        self.assertIsNone(result.next_state)
        context.control_time += 0.1
        self.assertEqual(search.execute(context, None, {}).command, "STOP")


if __name__ == "__main__":
    unittest.main()
