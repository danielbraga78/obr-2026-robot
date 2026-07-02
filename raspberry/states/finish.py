from ..state_machine import StateResult


class FinishState:
    def execute(self, context, frame, detectors) -> StateResult:
        return StateResult(command="STOP", next_state="FINISH", log_message="Fim do ciclo")
