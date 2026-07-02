from ..state_machine import StateResult


class AvoidObstacleState:
    def execute(self, context, frame, detectors) -> StateResult:
        return StateResult(command="MOVE,10,-10,0", next_state="FOLLOW_LINE", log_message="Desviando obstáculo")
