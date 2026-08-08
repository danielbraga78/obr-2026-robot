from ..state_machine import StateResult


class AvoidObstacleState:
    def execute(self, context, frame, detectors) -> StateResult:
        # Consome o evento: sem isso a Strategy voltaria a forçar AVOID_OBSTACLE
        # em todo ciclo e o robô nunca sairia do desvio.
        context.obstacle_detected = False
        return StateResult(command="MOVE,10,-10,0", next_state="FOLLOW_LINE", log_message="Desviando obstáculo")
