from ..state_machine import StateResult
from ..config import SEARCH_LINE_SPEED


class SearchLineState:
    def execute(self, context, frame, detectors) -> StateResult:
        return StateResult(command=f"MOVE,{SEARCH_LINE_SPEED},0,1", next_state="FOLLOW_LINE", log_message="Procurando linha")
