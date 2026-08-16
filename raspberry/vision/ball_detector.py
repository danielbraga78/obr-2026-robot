"""Detecta as vítimas: 2 bolas prateadas e 1 preta.

O detector antigo procurava amarelo (`BALL_MIN=(20,80,80)`), cor que não existe
na arena. Preta e prateada são as duas acromáticas, então nenhuma faixa HSV as
encontra: a detecção é por **forma**, sobre máscaras de brilho relativo ao piso,
e a classificação olha o interior do blob.

A prateada é a mais difícil — ela reflete o ambiente, então não tem cor nem
brilho próprios. Os limiares aqui são ponto de partida e precisam ser ajustados
com frames da arena real, com as duas bolas em posições e iluminações diferentes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np

from ..config import (
    BALL_BLACK_MAX_V_STD,
    BALL_BRIGHT_MARGIN,
    BALL_DARK_MARGIN,
    BALL_MAX_ASPECT,
    BALL_MAX_SATURATION,
    BALL_MIN_AREA,
    BALL_MIN_CIRCULARITY,
    BALL_SILVER_MIN_V_STD,
)
from .geometry import ground_distance_cm
from .shapes import ShapeMetrics, clean_mask, contour_metrics, looks_like_ball

BLACK = "black"
SILVER = "silver"


@dataclass
class Ball:
    x: float  # Coluna na view analisada
    y: float  # Linha do centro na view analisada
    radius: float
    distance: Optional[float]  # cm, pela projeção no chão; None acima do horizonte
    confidence: float
    color: str = BLACK
    x_norm: float = 0.0  # -1 (esquerda) a +1 (direita): independe da escala da view
    y_norm: float = 0.0  # -1 (topo) a +1 (base), no quadro original: onde toca o chão
    circularity: float = 0.0
    aspect: float = 0.0


class BallDetector:
    """Encontra a bola mais próxima e a classifica em preta ou prateada."""

    roi_profile = "full"

    def detect(self, frame: np.ndarray) -> Optional[Ball]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return self.detect_from_hsv(hsv, frame=frame)

    def detect_from_hsv(self, hsv: np.ndarray, frame: Optional[np.ndarray] = None, source_frame: Optional[np.ndarray] = None, view=None) -> Optional[Ball]:
        if frame is None:
            frame = source_frame if source_frame is not None else hsv
        height, width = hsv.shape[:2]

        saturation = hsv[:, :, 1]
        value = hsv[:, :, 2]
        floor_value = float(np.median(value))

        candidates = self._find_candidates(saturation, value, floor_value)
        if not candidates:
            return None

        # A mais próxima é a que toca o chão mais abaixo no quadro.
        metrics, hint = max(candidates, key=lambda item: item[0].base_y)

        color = self._classify(value, metrics, hint, floor_value)
        y_norm = view.source_y_norm(metrics.base_y) if view is not None else (metrics.base_y / height) * 2.0 - 1.0
        x_norm = view.source_x_norm(metrics.center_x) if view is not None else (metrics.center_x / width) * 2.0 - 1.0

        return Ball(
            x=metrics.center_x,
            y=metrics.center_y,
            radius=float(np.sqrt(metrics.area / np.pi)),
            distance=ground_distance_cm(y_norm),
            confidence=min(1.0, metrics.area / max(1.0, 0.01 * width * height)),
            color=color,
            x_norm=x_norm,
            y_norm=y_norm,
            circularity=metrics.circularity,
            aspect=metrics.aspect,
        )

    def _find_candidates(self, saturation: np.ndarray, value: np.ndarray, floor_value: float) -> List[Tuple[ShapeMetrics, str]]:
        """Blobs acromáticos, claros ou escuros, com forma de bola.

        Duas máscaras em vez de uma: preta e prateada estão em lados opostos do
        brilho do piso, e uni-las num só limiar traria o piso inteiro junto.
        """
        achromatic = saturation <= BALL_MAX_SATURATION
        masks = (
            (achromatic & (value <= floor_value - BALL_DARK_MARGIN), BLACK),
            (achromatic & (value >= floor_value + BALL_BRIGHT_MARGIN), SILVER),
        )

        candidates: List[Tuple[ShapeMetrics, str]] = []
        for mask, hint in masks:
            binary = clean_mask((mask.astype(np.uint8)) * 255)
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                metrics = contour_metrics(contour)
                if looks_like_ball(metrics, BALL_MIN_AREA, BALL_MIN_CIRCULARITY, BALL_MAX_ASPECT):
                    candidates.append((metrics, hint))
        return candidates

    def _classify(self, value: np.ndarray, metrics: ShapeMetrics, hint: str, floor_value: float) -> str:
        """Preta ou prateada, pelo interior do blob.

        A preta é escura por igual; a prateada tem reflexo especular, o que
        aparece como desvio alto de V e algum pixel quase saturado. Quando o
        interior não decide, fica a máscara que encontrou o blob.
        """
        mask = np.zeros(value.shape, dtype=np.uint8)
        cv2.circle(mask, (int(metrics.center_x), int(metrics.center_y)), max(1, int(np.sqrt(metrics.area / np.pi) * 0.7)), 255, thickness=-1)
        pixels = value[mask > 0]
        if pixels.size == 0:
            return hint

        mean = float(pixels.mean())
        std = float(pixels.std())
        brightest = float(pixels.max())

        if mean <= floor_value - BALL_DARK_MARGIN and std <= BALL_BLACK_MAX_V_STD:
            return BLACK
        if mean >= floor_value and (std >= BALL_SILVER_MIN_V_STD or brightest >= 240):
            return SILVER
        return hint
