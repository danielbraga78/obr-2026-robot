from ..state_machine import StateResult


class EnterRescueState:
    def execute(self, context, frame, detectors) -> StateResult:
        return StateResult(command="STOP", next_state="SEARCH_BALL", log_message="Entrando em modo resgate")
