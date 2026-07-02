from ..state_machine import StateResult


class DropBallState:
    def execute(self, context, frame, detectors) -> StateResult:
        return StateResult(command="RELEASE", next_state="FINISH", log_message="Liberando bola")
