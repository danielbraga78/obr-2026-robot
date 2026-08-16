"""Detecta as zonas seguras pela cor da parede: verde e vermelha.

São duas zonas, com paredes de 6 cm: a bola preta vai para o canto **vermelho** e
a prateada para o **verde**. O detector antigo só procurava verde, então metade
das entregas não tinha alvo.

Com a câmera inclinada a parede aparece como uma faixa fina no topo do quadro —
39 px a 45 cm, 13 px a 63,6 cm, na escala do quadro processado. Por isso este
detector analisa o perfil "upper": procurar no quadro inteiro só adiciona ruído,
já que a parede nunca aparece na parte de baixo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from ..config import (
    GREEN_ZONE_MAX,
    GREEN_ZONE_MIN,
    RED_ZONE_HIGH_MAX,
    RED_ZONE_HIGH_MIN,
    RED_ZONE_LOW_MAX,
    RED_ZONE_LOW_MIN,
    ZONE_MIN_AREA_RATIO,
)

GREEN = "green"
RED = "red"


@dataclass
class ZoneDetection:
    color: str  # "green" ou "red": a zona dominante no quadro
    area_ratio: float
    x_norm: float  # -1 (esquerda) a +1 (direita): rumo aproximado da parede
    green_ratio: float = 0.0
    red_ratio: float = 0.0


class SafeZoneDetector:
    """Encontra a parede colorida da zona segura.

    Mantém o debouncing de N quadros consecutivos para não reagir a um reflexo
    isolado, e mede área como **fração** da região analisada. Os limiares antigos
    eram soma bruta da máscara: `> 5000` equivalia a 20 pixels em 76.800.
    """

    roi_profile = "upper"

    def __init__(self, debounce_frames: int = 2, min_area_ratio: float = ZONE_MIN_AREA_RATIO):
        self.debounce_frames = debounce_frames
        self.min_area_ratio = min_area_ratio
        self._positive_count = 0

    def detect(self, frame: np.ndarray) -> Optional[ZoneDetection]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return self.detect_from_hsv(hsv, frame=frame)

    def detect_from_hsv(self, hsv: np.ndarray, frame: Optional[np.ndarray] = None, source_frame: Optional[np.ndarray] = None, view=None) -> Optional[ZoneDetection]:
        green_mask = cv2.inRange(hsv, np.array(GREEN_ZONE_MIN), np.array(GREEN_ZONE_MAX))
        red_mask = self._red_mask(hsv)

        total = float(green_mask.size) or 1.0
        green_ratio = float(cv2.countNonZero(green_mask)) / total
        red_ratio = float(cv2.countNonZero(red_mask)) / total

        if max(green_ratio, red_ratio) < self.min_area_ratio:
            self._positive_count = 0
            return None

        self._positive_count += 1
        if self._positive_count < self.debounce_frames:
            return None

        color = GREEN if green_ratio >= red_ratio else RED
        mask = green_mask if color == GREEN else red_mask
        return ZoneDetection(
            color=color,
            area_ratio=max(green_ratio, red_ratio),
            x_norm=self._horizontal_bearing(mask, view),
            green_ratio=green_ratio,
            red_ratio=red_ratio,
        )

    @staticmethod
    def _red_mask(hsv: np.ndarray) -> np.ndarray:
        """O vermelho fica na dobra do matiz, perto de 0 e de 180: duas faixas."""
        low = cv2.inRange(hsv, np.array(RED_ZONE_LOW_MIN), np.array(RED_ZONE_LOW_MAX))
        high = cv2.inRange(hsv, np.array(RED_ZONE_HIGH_MIN), np.array(RED_ZONE_HIGH_MAX))
        return cv2.bitwise_or(low, high)

    @staticmethod
    def _horizontal_bearing(mask: np.ndarray, view) -> float:
        moments = cv2.moments(mask, binaryImage=True)
        if not moments["m00"]:
            return 0.0
        center_x = moments["m10"] / moments["m00"]
        if view is not None:
            return view.source_x_norm(center_x)
        return (center_x / mask.shape[1]) * 2.0 - 1.0

    def reset(self) -> None:
        """Reseta o contador de debouncing."""
        self._positive_count = 0
