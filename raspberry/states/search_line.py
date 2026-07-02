from ..state_machine import StateResult


class SearchLineState:
    def execute(self, context, frame, detectors) -> StateResult:
        return StateResult(command="MOVE,10,0,1", next_state="FOLLOW_LINE", log_message="Procurando linha")
