"""Estado de alinhamento com a bola.

Responsabilidades:
- Detectar a bola na imagem
- Alinhamento horizontal (esquerda/direita) antes da captura
- Ajusta apenas a rotação, não a velocidade linear

Transições:
- SEARCH_BALL: se bola é perdida
- CAPTURE_BALL: se bola está alinhada

Pre-condições:
- Bola detectada na imagem
"""

from ..state_machine import StateResult


class AlignBallState:
    """Alinha o robô com a bola antes de capturar."""

    # Tolerância em erro normalizado (-1 a +1). O erro em pixels não serve mais:
    # cada detector analisa uma ROI própria, com escala própria, e comparar
    # `ball.x` (coordenada da view) com a largura do quadro original dava o
    # centro errado — o robô girava para sempre achando a bola à esquerda.
    ALIGNMENT_TOLERANCE = 0.15

    def execute(self, context, frame, detectors) -> StateResult:
        ball = context.last_detections.get("ball") if getattr(context, "last_detections", None) else None
        if ball is None and frame is not None:
            ball = detectors["ball"].detect(frame)
        if ball is None:
            return StateResult(command="MOVE,10,0,1", next_state="SEARCH_BALL", log_message="Bola não encontrada")

        error = getattr(ball, "x_norm", 0.0)
        if error < -self.ALIGNMENT_TOLERANCE:
            command = "MOVE,10,0,-1"  # Virar esquerda
        elif error > self.ALIGNMENT_TOLERANCE:
            command = "MOVE,10,0,1"   # Virar direita
        else:
            command = "STOP"  # Alinhado!

        context.ball_detected = True
        context.ball_distance = getattr(ball, "distance", None)
        context.ball_color = getattr(ball, "color", None)
        return StateResult(command=command, next_state="ALIGN_BALL", log_message="Alinhando com a bola")
