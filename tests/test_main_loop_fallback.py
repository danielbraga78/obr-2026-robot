import queue
import sys
import threading
import types
import unittest
from pathlib import Path
from typing import Optional

# Allow tests to run even when OpenCV is not installed.
_cv2_module = types.ModuleType("cv2")
_cv2_module.FONT_HERSHEY_SIMPLEX = 0
_cv2_module.COLOR_BGR2HSV = 0
_cv2_module.COLOR_GRAY2BGR = 0
_cv2_module.COLOR_BGRA2BGR = 0
_cv2_module.WINDOW_NORMAL = 0
_cv2_module.utils = types.SimpleNamespace(
    logging=types.SimpleNamespace(setLogLevel=lambda *args, **kwargs: None, LOG_LEVEL_ERROR=0)
)
_cv2_module.namedWindow = lambda *args, **kwargs: None
_cv2_module.resizeWindow = lambda *args, **kwargs: None
_cv2_module.imshow = lambda *args, **kwargs: None
_cv2_module.waitKey = lambda *args, **kwargs: -1
_cv2_module.destroyWindow = lambda *args, **kwargs: None
_cv2_module.cvtColor = lambda frame, code: frame
_cv2_module.resize = lambda frame, size, interpolation=None: frame
_cv2_module.line = lambda *args, **kwargs: None
_cv2_module.circle = lambda *args, **kwargs: None
_cv2_module.putText = lambda *args, **kwargs: None
_cv2_module.rectangle = lambda *args, **kwargs: None
_cv2_module.addWeighted = lambda *args, **kwargs: args[0]

try:
    import numpy as np
except ImportError:
    np = types.ModuleType("numpy")
    np.uint8 = int
    np.ndarray = object
    np.zeros_like = lambda x: x
    np.uint8 = int
    np.empty = lambda shape, dtype=None: []
    np.where = lambda *args, **kwargs: []

sys.modules.setdefault("cv2", _cv2_module)
sys.modules.setdefault("numpy", np)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.config import RobotContext
from raspberry.main import RobotApp, build_vision_detectors
from raspberry.runtime import ExecutionLoopController
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
from raspberry.vision.line_detector import LineDetection
from raspberry.vision.pipeline import VisionResult


class DummySerial:
    def __init__(self):
        self.commands = []
        self._connected = True

    def connect(self):
        self._connected = True

    def is_connected(self):
        return self._connected

    def read_messages(self):
        return []

    def send_command(self, command: str):
        self.commands.append(command)

    def send_heartbeat(self):
        pass

    def close(self):
        pass


class DummyCamera:
    def __init__(self):
        self.active_backend = "dummy"

    def is_ready(self):
        return True

    def release(self):
        pass


class DummyPreview:
    def __init__(self):
        self.show_mask = False
        self.quit_requested = False

    def render(self, *args, **kwargs):
        pass

    def close(self):
        pass

    def describe_status(self):
        return "preview dummy"


class FakeTime:
    def __init__(self, start: float = 0.0):
        self._time = start

    def now(self) -> float:
        return self._time

    def advance(self, seconds: float) -> None:
        self._time += seconds


def build_main_machine() -> RobotStateMachine:
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


def make_robot_app(time_fn: Optional[callable] = None) -> RobotApp:
    if time_fn is None:
        time_fn = time.monotonic

    app = RobotApp.__new__(RobotApp)
    app.camera = DummyCamera()
    app.serial = DummySerial()
    app.context = RobotContext()
    app.strategy = Strategy()
    app.detectors = {"line": build_vision_detectors()["line"]}
    app.vision_pipeline = None
    app.machine = build_main_machine()
    app.frame_queue = queue.Queue(maxsize=2)
    app.result_queue = queue.Queue(maxsize=2)
    app._stop_event = threading.Event()
    app.last_frame = None
    app.last_frame_at = None
    app._last_vision_result_at = None
    app._last_command_sent_at = None
    app._now = time_fn
    app._frame_lock = threading.Lock()
    app._last_telemetry_log = 0.0
    app._vision_fps = 0.0
    app._last_capture_at = None
    app.preview = DummyPreview()
    app.loop_controller = ExecutionLoopController(target_hz=20.0, now_fn=time_fn)
    return app


class MainLoopFallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.time = FakeTime(start=0.0)
        self.app = make_robot_app(time_fn=self.time.now)
        self.app.loop_controller = ExecutionLoopController(target_hz=20.0, now_fn=self.time.now)

    def test_normal_result_sends_control_command(self):
        self.app.machine.current_state = "FOLLOW_LINE"
        self.app.context.current_state = "FOLLOW_LINE"
        line = LineDetection(center_x=160.0, error=0.0, confidence=1.0, frame_width=320)
        result = VisionResult(detections={"line": line}, captured_at=self.time.now())
        self.app.result_queue.put(result)

        self.app._process_cycle()

        self.assertTrue(self.app.serial.commands)
        self.assertTrue(self.app.serial.commands[0].startswith("MOVE,"))
        self.assertEqual(self.app.context.last_command, self.app.serial.commands[0])
        self.assertEqual(self.app._last_vision_result_at, 0.0)

    def test_temporary_absence_maintains_control(self):
        self.app.machine.current_state = "FOLLOW_LINE"
        self.app.context.current_state = "FOLLOW_LINE"
        line = LineDetection(center_x=160.0, error=0.0, confidence=1.0, frame_width=320)
        result = VisionResult(detections={"line": line}, captured_at=self.time.now())
        self.app.result_queue.put(result)

        self.app._process_cycle()
        self.time.advance(0.05)
        self.app._process_cycle()

        self.assertEqual(len(self.app.serial.commands), 2)
        self.assertTrue(all(cmd.startswith("MOVE,") for cmd in self.app.serial.commands))

    def test_timeout_clears_stale_vision_and_stops_safely(self):
        self.app.machine.current_state = "FOLLOW_LINE"
        self.app.context.current_state = "FOLLOW_LINE"
        line = LineDetection(center_x=160.0, error=0.0, confidence=1.0, frame_width=320)
        result = VisionResult(detections={"line": line}, captured_at=self.time.now())
        self.app.result_queue.put(result)

        self.app._process_cycle()
        self.time.advance(0.3)
        self.app._process_cycle()

        self.assertEqual(self.app.serial.commands[-1], "STOP")
        self.assertEqual(self.app.machine.current_state, "SEARCH_LINE")

    def test_recovery_after_vision_returns_to_motion(self):
        self.app.machine.current_state = "FOLLOW_LINE"
        self.app.context.current_state = "FOLLOW_LINE"
        line = LineDetection(center_x=160.0, error=0.0, confidence=1.0, frame_width=320)
        self.app.result_queue.put(result := VisionResult(detections={"line": line}, captured_at=self.time.now()))
        self.app._process_cycle()
        self.time.advance(0.3)
        self.app._process_cycle()

        self.assertEqual(self.app.serial.commands[-1], "STOP")
        self.assertEqual(self.app.machine.current_state, "SEARCH_LINE")

        self.time.advance(0.01)
        self.app.result_queue.put(VisionResult(detections={"line": line}, captured_at=self.time.now()))
        self.app._process_cycle()

        self.assertTrue(self.app.serial.commands[-1].startswith("MOVE,"))
        self.assertEqual(self.app.machine.current_state, "FOLLOW_LINE")

    def test_expired_last_command_falls_back_to_stop(self):
        self.app.context.last_command = "MOVE,10,0,1"
        self.app._last_command_sent_at = 0.0
        self.time.advance(1.0)

        fake_state_result = type("FakeStateResult", (), {"command": None})()
        self.assertEqual(self.app._resolve_command(fake_state_result), "STOP")

    def test_valid_last_command_can_be_reused_briefly(self):
        self.app.context.last_command = "MOVE,10,0,1"
        self.app._last_command_sent_at = 0.0
        self.time.advance(0.1)

        fake_state_result = type("FakeStateResult", (), {"command": None})()
        self.assertEqual(self.app._resolve_command(fake_state_result), "MOVE,10,0,1")


if __name__ == "__main__":
    unittest.main()
