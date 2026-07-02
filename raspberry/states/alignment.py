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
from ..config import VISION_PROCESS_WIDTH


class AlignBallState:
    """Alinha o robô com a bola antes de capturar."""
    
    # Tolerância de alinhamento (pixels from center)
    ALIGNMENT_TOLERANCE = 30
    
    def execute(self, context, frame, detectors) -> StateResult:
        ball = context.last_detections.get("ball") if getattr(context, "last_detections", None) else None
        if ball is None and frame is not None:
            ball = detectors["ball"].detect(frame)
        if ball is None:
            return StateResult(command="MOVE,10,0,1", next_state="SEARCH_BALL", log_message="Bola não encontrada")
        
        # Calcular centro da imagem dinamicamente
        frame_width = frame.shape[1] if frame is not None else VISION_PROCESS_WIDTH
        center_x = frame_width // 2
        
        # Alinhamento lateral (tolerância de ±30 pixels)
        if ball.x < center_x - self.ALIGNMENT_TOLERANCE:
            command = "MOVE,10,0,-1"  # Virar esquerda
        elif ball.x > center_x + self.ALIGNMENT_TOLERANCE:
            command = "MOVE,10,0,1"   # Virar direita
        else:
            command = "STOP"  # Alinhado!
        
        context.ball_detected = True
        context.ball_distance = getattr(ball, "distance", None)
        return StateResult(command=command, next_state="ALIGN_BALL", log_message="Alinhando com a bola")
