"""Projeção da imagem no plano do chão.

A bola está apoiada no chão e a altura e a inclinação da câmera são conhecidas,
então a linha da imagem onde a bola toca o chão dá a distância diretamente. Isso
substitui a estimativa por raio aparente, que dependia de iluminação, de oclusão
parcial e — principalmente — da escala do redimensionamento, que muda conforme a
ROI de cada detector.
"""

from __future__ import annotations

import math
from typing import Optional

from ..config import CAMERA_HEIGHT_CM, CAMERA_TILT_DEG, CAMERA_VFOV_DEG, GROUND_MAX_DISTANCE_CM

# Abaixo deste ângulo a linha de visada é praticamente paralela ao chão e a
# distância explode; tratamos como "acima do horizonte", sem medida.
_MIN_ANGLE_DEG = 1.5


def ground_distance_cm(
    y_norm: float,
    height_cm: float = CAMERA_HEIGHT_CM,
    tilt_deg: float = CAMERA_TILT_DEG,
    vfov_deg: float = CAMERA_VFOV_DEG,
) -> Optional[float]:
    """Distância no chão do ponto que aparece em `y_norm`.

    `y_norm` vai de -1 (topo do quadro original) a +1 (base). Devolve None para
    pontos acima do horizonte, onde não existe interseção com o chão.
    """
    half_fov = math.radians(vfov_deg / 2.0)
    angle = math.radians(tilt_deg) + math.atan(y_norm * math.tan(half_fov))
    if angle <= math.radians(_MIN_ANGLE_DEG):
        return None
    return min(height_cm / math.tan(angle), GROUND_MAX_DISTANCE_CM)
