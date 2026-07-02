from ..state_machine import StateResult


class SearchBallState:
    def execute(self, context, frame, detectors) -> StateResult:
        return StateResult(command="MOVE,15,0,1", next_state="SEARCH_BALL", log_message="Procurando bola")
