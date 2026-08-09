from dataclasses import dataclass
from typing import Optional

from .config import ALIGN_BALL, AVOID_OBSTACLE, CAPTURE_BALL, DROP_BALL, ENTER_RESCUE, SEARCH_BALL, SEARCH_SAFE_ZONE


@dataclass
class StrategyDecision:
    next_state: Optional[str] = None
    command: Optional[str] = None


# Estados em que já estamos tratando a bola: ver a bola de novo não deve
# reiniciar o alinhamento nem impedir a captura de avançar.
_BALL_STATES = frozenset({ALIGN_BALL, CAPTURE_BALL, SEARCH_SAFE_ZONE, DROP_BALL})


class Strategy:
    """Decide transições reativas, que têm prioridade sobre o fluxo normal.

    Devolver next_state=None significa "sem interferência": a máquina de estados
    segue com a transição que o próprio estado pediu. Antes, o fallback devolvia
    o estado atual do contexto e sobrescrevia a transição da máquina, o que
    prendia o robô em BOOT e fazia SEARCH_LINE nunca executar.
    """

    def evaluate(self, context) -> StrategyDecision:
        context.expire_temporal_signals()
        if context.has_recent_temporal_flag("obstacle_detected", ttl=0.25):
            return StrategyDecision(next_state=AVOID_OBSTACLE, command="STOP")
        if context.rescue_detected:
            return StrategyDecision(next_state=ENTER_RESCUE, command="STOP")
        if context.ball_detected and context.current_state not in _BALL_STATES:
            return StrategyDecision(next_state=ALIGN_BALL, command="STOP")
        if context.current_state == ALIGN_BALL and context.ball_distance and context.ball_distance < 20:
            return StrategyDecision(next_state=CAPTURE_BALL, command="GRAB")
        if context.current_state == CAPTURE_BALL and context.has_recent_event("BALL_CAPTURED", ttl=1.0):
            return StrategyDecision(next_state=SEARCH_SAFE_ZONE, command="STOP")
        if context.current_state == SEARCH_SAFE_ZONE and context.safe_zone_detected:
            return StrategyDecision(next_state=DROP_BALL, command="RELEASE")
        if context.current_state == DROP_BALL and context.has_recent_event("BALL_DROPPED", ttl=1.0):
            return StrategyDecision(next_state=SEARCH_BALL, command="STOP")
        return StrategyDecision()
