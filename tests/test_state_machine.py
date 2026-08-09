import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.config import RobotContext
from raspberry.state_machine import RobotStateMachine, StateResult


class DummyState:
    def __init__(self, result: StateResult):
        self._result = result

    def execute(self, context, frame, detectors):
        return self._result


class RobotStateMachineTests(unittest.TestCase):
    def test_transition(self):
        machine = RobotStateMachine({"BOOT": DummyState(StateResult(command="STOP", next_state="FINISH")), "FINISH": DummyState(StateResult(command="STOP"))})
        machine.transition_to("BOOT")
        result = machine.run_once(RobotContext(), None, {})
        self.assertEqual(result.command, "STOP")
        self.assertEqual(machine.current_state, "FINISH")

    def test_state_without_transition_keeps_current_state(self):
        machine = RobotStateMachine({"BOOT": DummyState(StateResult(command="STOP", next_state=None))})
        machine.transition_to("BOOT")

        result = machine.run_once(RobotContext(), None, {})

        self.assertEqual(result.command, "STOP")
        self.assertEqual(machine.current_state, "BOOT")

    def test_state_requested_transition_is_applied(self):
        machine = RobotStateMachine({"BOOT": DummyState(StateResult(command="STOP", next_state="FINISH")), "FINISH": DummyState(StateResult(command="STOP"))})
        machine.transition_to("BOOT")

        result = machine.run_once(RobotContext(), None, {}, strategy_next_state=None)

        self.assertEqual(result.next_state, "FINISH")
        self.assertEqual(machine.current_state, "FINISH")

    def test_strategy_priority_overrides_state_transition(self):
        machine = RobotStateMachine({
            "BOOT": DummyState(StateResult(command="STOP", next_state="FOLLOW_LINE")),
            "FOLLOW_LINE": DummyState(StateResult(command="STOP")),
            "FINISH": DummyState(StateResult(command="STOP")),
        })
        machine.transition_to("BOOT")

        result = machine.run_once(RobotContext(), None, {}, strategy_next_state="FINISH")

        self.assertEqual(machine.current_state, "FINISH")
        self.assertEqual(result.next_state, "FOLLOW_LINE")

    def test_invalid_transitions_are_ignored(self):
        machine = RobotStateMachine({"BOOT": DummyState(StateResult(command="STOP", next_state="INVALID"))})
        machine.transition_to("BOOT")

        result = machine.run_once(RobotContext(), None, {}, strategy_next_state="INVALID")

        self.assertEqual(machine.current_state, "BOOT")
        self.assertEqual(result.next_state, "INVALID")


if __name__ == "__main__":
    unittest.main()
