from ..state_machine import StateResult


class AvoidObstacleState:
    def execute(self, context, frame, detectors) -> StateResult:
        # Consome o evento e gera um comando de fuga mais explícito para o Arduino.
        context.set_temporal_flag("obstacle_detected", False)
        return StateResult(command="MOVE,0,-60,0", next_state="FOLLOW_LINE", log_message="Desviando obstáculo")
