import time

from ..config import (
    LINE_RECOVERY_CONFIRM_OBSERVATIONS,
    LINE_RECOVERY_MAX_ERROR_DELTA,
    LINE_SEARCH_INITIAL_DIRECTION,
    LINE_SEARCH_MAX_PULSES,
    LINE_SEARCH_PAUSE_SECONDS,
    LINE_SEARCH_PULSE_SECONDS,
    LINE_SEARCH_TIMEOUT_SECONDS,
    LINE_SEARCH_TURN_PWM,
    MAX_FRAME_AGE,
    VISION_PROCESS_WIDTH,
)
from ..state_machine import StateResult


class SearchLineState:
    """Busca curta em pulsos alternados; só retoma após observações novas e estáveis."""

    def __init__(self, now_fn=None) -> None:
        self._now = now_fn or time.monotonic
        self._started_at = None
        self._last_observation_sequence = 0
        self._stable_count = 0
        self._previous_error = None
        self._direction = LINE_SEARCH_INITIAL_DIRECTION

    def _start(self, context, now: float) -> None:
        self._started_at = now
        self._last_observation_sequence = getattr(context, "line_search_after_sequence", 0)
        direction = getattr(context, "line_recovery_direction", 0)
        self._direction = direction if direction in (-1, 1) else LINE_SEARCH_INITIAL_DIRECTION
        self._stable_count = 0
        self._previous_error = None
        context.line_search_started = True

    def execute(self, context, frame, detectors) -> StateResult:
        now = getattr(context, "control_time", None)
        if now is None:
            now = self._now()
        if not getattr(context, "line_search_started", False) or self._started_at is None:
            self._start(context, now)

        elapsed = now - self._started_at
        if elapsed >= LINE_SEARCH_TIMEOUT_SECONDS:
            return StateResult(command="STOP", log_message="Busca de linha expirou; mantendo parada")

        sequence = getattr(context, "line_observation_sequence", 0)
        new_observation = sequence > self._last_observation_sequence
        if new_observation:
            self._last_observation_sequence = sequence
            detection = context.last_detections.get("line")
            captured_at = getattr(context, "line_observation_at", None)
            age = None if captured_at is None else now - captured_at
            if (
                detection is not None
                and getattr(detection, "error", None) is not None
                and getattr(detection, "confidence", 0.0) > 0.0
                and age is not None
                and 0.0 <= age <= MAX_FRAME_AGE
            ):
                width = getattr(detection, "frame_width", None) or VISION_PROCESS_WIDTH
                error = max(-1.0, min(1.0, float(detection.error) / max(width / 2.0, 1.0)))
                if (
                    self._previous_error is not None
                    and abs(error - self._previous_error) <= LINE_RECOVERY_MAX_ERROR_DELTA
                ):
                    self._stable_count += 1
                else:
                    self._stable_count = 1
                self._previous_error = error
                if self._stable_count >= LINE_RECOVERY_CONFIRM_OBSERVATIONS:
                    context.line_controller_reset = True
                    context.line_search_started = False
                    self._started_at = None
                    return StateResult(
                        command="STOP",
                        next_state="FOLLOW_LINE",
                        log_message="Linha reencontrada em observações estáveis",
                    )
            else:
                self._stable_count = 0
                self._previous_error = None

        if self._stable_count:
            return StateResult(command="STOP", log_message="Confirmando linha reencontrada")

        phase_duration = LINE_SEARCH_PULSE_SECONDS + LINE_SEARCH_PAUSE_SECONDS
        pulse_index = int(elapsed / phase_duration)
        pulse_elapsed = elapsed - pulse_index * phase_duration
        if pulse_index >= LINE_SEARCH_MAX_PULSES:
            return StateResult(command="STOP", log_message="Limite de movimento da busca atingido")
        if pulse_elapsed >= LINE_SEARCH_PULSE_SECONDS:
            return StateResult(command="STOP", log_message="Pausa entre pulsos de busca")

        direction = self._direction if pulse_index < 2 or pulse_index >= 4 else -self._direction
        return StateResult(
            command=f"MOVE,0,0,{direction * LINE_SEARCH_TURN_PWM}",
            log_message="Busca de linha em pulso angular limitado",
        )
