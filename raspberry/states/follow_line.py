from ..config import MAX_STEER, PID_KD, PID_KI, PID_KP
from ..pid import PIDController
from ..state_machine import StateResult


class FollowLineState:
    def __init__(self) -> None:
        self.pid = PIDController(PID_KP, PID_KI, PID_KD, max_output=MAX_STEER)

    def execute(self, context, frame, detectors) -> StateResult:
        detection = context.last_detections.get("line") if getattr(context, "last_detections", None) else None
        if detection is None and frame is not None:
            detection = detectors["line"].detect(frame)
        if detection is None or detection.error is None:
            return StateResult(command="STOP", next_state="SEARCH_LINE", log_message="Linha perdida")
        steering = self.pid.update(float(detection.error) / 320.0)
        if steering > 10:
            command = "MOVE,20,0,1"
        elif steering < -10:
            command = "MOVE,20,0,-1"
        else:
            command = "MOVE,25,0,0"
        context.line_center = detection.center_x
        return StateResult(command=command, next_state="FOLLOW_LINE", log_message="Seguindo linha")
