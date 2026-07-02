from ..state_machine import StateResult


class CaptureBallState:
    def execute(self, context, frame, detectors) -> StateResult:
        return StateResult(command="GRAB", next_state="SEARCH_SAFE_ZONE", log_message="Capturando bola")
