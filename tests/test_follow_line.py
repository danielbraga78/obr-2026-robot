import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.config import BASE_SPEED, LINE_LOST_GRACE_CYCLES, MAX_STEER, MIN_SPEED, RobotContext
from raspberry.motion import _wheel_speeds, normalize_motor_command
from raspberry.states.follow_line import FollowLineState
from raspberry.vision.line_detector import LineDetection


def run_state(detection, cycles: int = 1):
    state = FollowLineState()
    context = RobotContext()
    context.last_detections = {"line": detection}
    result = None
    for _ in range(cycles):
        result = state.execute(context, None, {})
    return result


def parse_move(command: str):
    parts = command.split(",")
    assert parts[0] == "MOVE", command
    return float(parts[1]), float(parts[2]), float(parts[3])


class FollowLineTests(unittest.TestCase):
    def test_centered_line_goes_straight_at_base_speed(self):
        result = run_state(LineDetection(center_x=160.0, error=0.0, confidence=0.9, frame_width=320))
        speed, vy, wz = parse_move(result.command)

        self.assertEqual(wz, 0)
        self.assertEqual(vy, 0)
        self.assertEqual(speed, BASE_SPEED)

    def test_steering_is_proportional_to_error(self):
        small = run_state(LineDetection(center_x=180.0, error=20.0, confidence=0.9, frame_width=320))
        large = run_state(LineDetection(center_x=300.0, error=140.0, confidence=0.9, frame_width=320))

        _, _, small_wz = parse_move(small.command)
        _, _, large_wz = parse_move(large.command)

        self.assertGreater(small_wz, 0)
        self.assertGreater(large_wz, small_wz)

    def test_error_sign_defines_turn_direction(self):
        left = run_state(LineDetection(center_x=40.0, error=-120.0, confidence=0.9, frame_width=320))
        right = run_state(LineDetection(center_x=280.0, error=120.0, confidence=0.9, frame_width=320))

        _, _, left_wz = parse_move(left.command)
        _, _, right_wz = parse_move(right.command)

        self.assertLess(left_wz, 0)
        self.assertGreater(right_wz, 0)

    def test_extreme_errors_keep_expected_motor_differential(self):
        left = run_state(LineDetection(center_x=0.0, error=-160.0, confidence=0.9, frame_width=320))
        right = run_state(LineDetection(center_x=320.0, error=160.0, confidence=0.9, frame_width=320))

        left_wheels = _wheel_speeds(*map(float, parse_move(normalize_motor_command(left.command))))
        right_wheels = _wheel_speeds(*map(float, parse_move(normalize_motor_command(right.command))))

        self.assertLess(left_wheels[0], left_wheels[1])
        self.assertLess(left_wheels[2], left_wheels[3])
        self.assertGreater(right_wheels[0], right_wheels[1])
        self.assertGreater(right_wheels[2], right_wheels[3])

    def test_rapidly_alternating_error_reverses_steering_without_stale_command(self):
        state = FollowLineState()
        context = RobotContext()
        commands = []
        for error in (-100.0, 100.0, -100.0, 100.0):
            context.last_detections = {
                "line": LineDetection(center_x=160.0 + error, error=error, confidence=0.9, frame_width=320)
            }
            commands.append(parse_move(state.execute(context, None, {}).command)[2])

        self.assertLess(commands[0], 0)
        self.assertGreater(commands[1], 0)
        self.assertLess(commands[2], 0)
        self.assertGreater(commands[3], 0)

    def test_steering_never_exceeds_max_steer(self):
        result = run_state(LineDetection(center_x=320.0, error=160.0, confidence=0.9, frame_width=320), cycles=50)
        _, _, wz = parse_move(result.command)

        self.assertLessEqual(abs(wz), MAX_STEER)

    def test_speed_drops_on_sharp_curves(self):
        result = run_state(LineDetection(center_x=320.0, error=160.0, confidence=0.9, frame_width=320), cycles=50)
        speed, _, _ = parse_move(result.command)

        self.assertLess(speed, BASE_SPEED)
        self.assertGreaterEqual(speed, MIN_SPEED)

    def test_error_normalization_uses_detection_frame_width(self):
        narrow = run_state(LineDetection(center_x=120.0, error=40.0, confidence=0.9, frame_width=160))
        wide = run_state(LineDetection(center_x=200.0, error=40.0, confidence=0.9, frame_width=640))

        _, _, narrow_wz = parse_move(narrow.command)
        _, _, wide_wz = parse_move(wide.command)

        # Mesmo erro em pixels vale mais num quadro estreito.
        self.assertGreater(narrow_wz, wide_wz)

    def test_temporary_lost_line_keeps_reduced_motion(self):
        state = FollowLineState()
        context = RobotContext()
        context.last_detections = {"line": LineDetection(error=80.0, center_x=240.0, frame_width=320)}
        state.execute(context, None, {})
        context.last_detections = {"line": LineDetection()}

        result = state.execute(context, None, {})

        speed, _, steering = parse_move(result.command)
        self.assertEqual(result.next_state, "FOLLOW_LINE")
        self.assertLess(speed, BASE_SPEED)
        self.assertGreater(steering, 0)

    def test_lost_line_stops_after_grace_window(self):
        state = FollowLineState()
        context = RobotContext()
        context.last_detections = {"line": LineDetection()}

        result = None
        for _ in range(LINE_LOST_GRACE_CYCLES + 1):
            result = state.execute(context, None, {})

        self.assertEqual(result.command, "STOP")
        self.assertEqual(result.next_state, "SEARCH_LINE")


if __name__ == "__main__":
    unittest.main()
