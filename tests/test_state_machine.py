import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.config import RobotContext
from raspberry.state_machine import RobotStateMachine, StateResult


class DummyState:
    def execute(self, context, frame, detectors):
        return StateResult(command="STOP", next_state="FINISH")


class RobotStateMachineTests(unittest.TestCase):
    def test_transition(self):
        machine = RobotStateMachine({"BOOT": DummyState(), "FINISH": DummyState()})
        machine.transition_to("BOOT")
        result = machine.run_once(RobotContext(), None, {})
        self.assertEqual(result.command, "STOP")
        self.assertEqual(machine.current_state, "FINISH")


if __name__ == "__main__":
    unittest.main()
