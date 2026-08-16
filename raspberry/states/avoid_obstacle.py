from ..state_machine import StateResult


class AvoidObstacleState:
    def execute(self, context, frame, detectors) -> StateResult:
        # Consome o evento (todas as fontes, senão a agregada volta a ser
        # recalculada como verdadeira) e gera um comando de fuga para o Arduino.
        context.clear_obstacle_sources()
        return StateResult(command="MOVE,0,-60,0", next_state="FOLLOW_LINE", log_message="Desviando obstáculo")
