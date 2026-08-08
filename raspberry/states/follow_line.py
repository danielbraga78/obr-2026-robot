from ..config import BASE_SPEED, MAX_STEER, MIN_SPEED, PID_KD, PID_KI, PID_KP, STEER_SIGN, VISION_PROCESS_WIDTH
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
            self.pid.reset()
            return StateResult(command="STOP", next_state="SEARCH_LINE", log_message="Linha perdida")

        steering = STEER_SIGN * self.pid.update(self._normalized_error(detection))
        speed = self._speed_for(steering)
        command = f"MOVE,{speed},0,{int(round(steering))}"
        context.line_center = detection.center_x
        return StateResult(command=command, next_state="FOLLOW_LINE", log_message="Seguindo linha")

    def _normalized_error(self, detection) -> float:
        """Converte o erro em pixels para -1.0..1.0 (borda esquerda a borda direita)."""
        width = detection.frame_width or VISION_PROCESS_WIDTH
        half_width = max(1.0, width / 2.0)
        return max(-1.0, min(1.0, float(detection.error) / half_width))

    def _speed_for(self, steering: float) -> int:
        """Reduz a velocidade proporcionalmente ao esforço de curva."""
        effort = min(1.0, abs(steering) / max(MAX_STEER, 1.0))
        return int(round(BASE_SPEED - (BASE_SPEED - MIN_SPEED) * effort))
