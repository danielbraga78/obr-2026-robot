from ..config import (
    BASE_SPEED,
    LINE_CORNER_BYPASSES_FILTER,
    LINE_ERROR_FILTER_ALPHA,
    LINE_HEADING_GAIN,
    LINE_LOST_GRACE_CYCLES,
    MAX_STEER,
    MIN_SPEED,
    PID_KD,
    PID_KI,
    PID_KP,
    STEER_SIGN,
    VISION_PROCESS_WIDTH,
)
from ..pid import PIDController
from ..state_machine import StateResult


class FollowLineState:
    def __init__(self) -> None:
        self.pid = PIDController(PID_KP, PID_KI, PID_KD, max_output=MAX_STEER)
        self._last_error = 0.0
        self._last_steering = 0.0
        self._lost_cycles = 0
        self._last_corner_side = 0

    def execute(self, context, frame, detectors) -> StateResult:
        detection = context.last_detections.get("line") if getattr(context, "last_detections", None) else None
        if detection is None and frame is not None:
            detection = detectors["line"].detect(frame)
        if detection is None:
            self._lost_cycles = LINE_LOST_GRACE_CYCLES + 1
        elif detection.error is None:
            self._lost_cycles += 1
        else:
            self._lost_cycles = 0

        if self._lost_cycles:
            if self._lost_cycles <= LINE_LOST_GRACE_CYCLES:
                return StateResult(
                    command=self._recovery_command(),
                    next_state="FOLLOW_LINE",
                    log_message="Leitura de linha perdida temporariamente",
                )
            self._reset()
            return StateResult(command="STOP", next_state="SEARCH_LINE", log_message="Linha perdida")

        corner = bool(getattr(detection, "corner", False))
        error = self._normalized_error(detection)
        # A memória da curva serve para recuperar a linha logo depois dela. Uma
        # vez de volta ao centro e sem curva à vista, ela precisa ser esquecida:
        # senão uma falha de leitura minutos depois giraria para o lado errado.
        if corner:
            self._last_corner_side = detection.corner_side or self._last_corner_side
        elif abs(error) < 0.15:
            self._last_corner_side = 0


        # O filtro suaviza o ruído do centroide, mas atrasa a reação em cerca de
        # três quadros. Numa curva fechada esse atraso é o suficiente para o robô
        # passar reto, então ali o erro entra cru.
        if not (corner and LINE_CORNER_BYPASSES_FILTER):
            error = (LINE_ERROR_FILTER_ALPHA * error) + ((1.0 - LINE_ERROR_FILTER_ALPHA) * self._last_error)
        self._last_error = error

        steering = STEER_SIGN * self.pid.update(error)
        # Termo antecipativo: o rumo da linha adiante entra antes que ela saia do
        # centro. É a diferença entre reagir à curva e antecipá-la.
        steering += STEER_SIGN * LINE_HEADING_GAIN * getattr(detection, "heading", 0.0)
        steering = max(-MAX_STEER, min(MAX_STEER, steering))

        self._last_steering = steering
        speed = self._speed_for(steering, corner)
        command = f"MOVE,{speed},0,{int(round(steering))}"
        context.line_center = detection.center_x
        return StateResult(command=command, next_state="FOLLOW_LINE", log_message="Seguindo linha")

    def _recovery_command(self) -> str:
        """O que fazer nos quadros sem leitura válida.

        Se a linha sumiu logo depois de uma curva fechada, ela está do lado para
        onde a curva apontava — seguir reto é justamente o erro que faz o robô
        perder a curva de 90 graus. Aí o comando vira giro para aquele lado.
        """
        if self._last_corner_side:
            return f"MOVE,0,0,{int(round(MAX_STEER * self._last_corner_side))}"
        return f"MOVE,{MIN_SPEED},0,{int(round(self._last_steering))}"

    def _reset(self) -> None:
        self.pid.reset()
        self._last_error = 0.0
        self._last_steering = 0.0
        self._last_corner_side = 0

    def _normalized_error(self, detection) -> float:
        """Converte o erro em pixels para -1.0..1.0 (borda esquerda a borda direita)."""
        width = detection.frame_width or VISION_PROCESS_WIDTH
        half_width = max(1.0, width / 2.0)
        return max(-1.0, min(1.0, float(detection.error) / half_width))

    def _speed_for(self, steering: float, corner: bool = False) -> int:
        """Reduz a velocidade proporcionalmente ao esforço de curva.

        Numa curva fechada a redução não espera o esforço subir: o robô chega
        devagar, porque a curva vai exigir pivô e chegar rápido nela é o que
        fazia o robô passar reto.
        """
        effort = min(1.0, abs(steering) / max(MAX_STEER, 1.0))
        speed = BASE_SPEED - (BASE_SPEED - MIN_SPEED) * effort
        if corner:
            speed = min(speed, MIN_SPEED)
        return int(round(speed))
