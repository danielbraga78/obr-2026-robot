from ..state_machine import StateResult
from ..config import SEARCH_BALL_SPEED


class SearchBallState:
    def execute(self, context, frame, detectors) -> StateResult:
        return StateResult(command=f"MOVE,{SEARCH_BALL_SPEED},0,1", next_state="SEARCH_BALL", log_message="Procurando bola")
