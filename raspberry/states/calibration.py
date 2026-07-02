from ..state_machine import StateResult


class CalibrationState:
    def execute(self, context, frame, detectors) -> StateResult:
        return StateResult(command="STOP", next_state="FOLLOW_LINE", log_message="Calibração concluída")
