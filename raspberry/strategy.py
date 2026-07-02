from dataclasses import dataclass
from typing import Optional

from .config import AVOID_OBSTACLE, CALIBRATION, CAPTURE_BALL, DROP_BALL, ENTER_RESCUE, FINISH, FOLLOW_LINE, SEARCH_BALL, SEARCH_LINE, SEARCH_SAFE_ZONE, ALIGN_BALL


@dataclass
class StrategyDecision:
    next_state: Optional[str] = None
    command: Optional[str] = None


class Strategy:
    """Decide a transição de estados com base nas informações do contexto."""

    def evaluate(self, context) -> StrategyDecision:
        if context.obstacle_detected:
            return StrategyDecision(next_state=AVOID_OBSTACLE, command="STOP")
        if context.rescue_detected:
            return StrategyDecision(next_state=ENTER_RESCUE, command="STOP")
        if context.ball_detected:
            return StrategyDecision(next_state=ALIGN_BALL, command="STOP")
        if context.current_state in {CALIBRATION, FOLLOW_LINE, SEARCH_LINE}:
            return StrategyDecision(next_state=FOLLOW_LINE, command=None)
        if context.current_state == ALIGN_BALL and context.ball_distance and context.ball_distance < 20:
            return StrategyDecision(next_state=CAPTURE_BALL, command="GRAB")
        if context.current_state == CAPTURE_BALL and context.last_event == "BALL_CAPTURED":
            return StrategyDecision(next_state=SEARCH_SAFE_ZONE, command="STOP")
        if context.current_state == SEARCH_SAFE_ZONE and context.safe_zone_detected:
            return StrategyDecision(next_state=DROP_BALL, command="RELEASE")
        if context.current_state == DROP_BALL and context.last_event == "BALL_DROPPED":
            return StrategyDecision(next_state=SEARCH_BALL, command="STOP")
        return StrategyDecision(next_state=context.current_state, command=None)
