"""Detecta a entrada da área de resgate: a faixa prateada no chão.

O detector antigo procurava amarelo (`RESCUE_MIN=(20,80,120)`), cor que não
existe na arena, com limiar de soma bruta que disparava com 39 pixels — qualquer
reflexo amarelado levava o robô a abandonar a pista, porque a `Strategy` trata
resgate como prioridade acima do seguidor de linha.

A entrada é marcada por uma faixa prateada: clara, sem saturação e **alongada**.
A forma é o que a separa da bola prateada, que é compacta e tem a mesma cor.
"""

from __future__ import annotations

from typing import Optional

import cv2
import numpy as np

from ..config import (
    SILVER_LINE_BRIGHT_MARGIN,
    SILVER_LINE_MAX_SATURATION,
    SILVER_LINE_MIN_AREA_RATIO,
    SILVER_LINE_MIN_ASPECT,
)
from .shapes import clean_mask, contour_metrics, looks_like_line


class RescueDetector:
    """Reporta True quando a faixa prateada da entrada está logo à frente.

    Analisa o perfil "near": a faixa importa quando o robô está prestes a
    cruzá-la, não quando aparece no fundo do quadro.
    """

    roi_profile = "near"

    def __init__(self, debounce_frames: int = 2, min_area_ratio: float = SILVER_LINE_MIN_AREA_RATIO):
        self.debounce_frames = debounce_frames
        self.min_area_ratio = min_area_ratio
        self._positive_count = 0

    def detect(self, frame: np.ndarray) -> bool:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return self.detect_from_hsv(hsv, frame=frame)

    def detect_from_hsv(self, hsv: np.ndarray, frame: Optional[np.ndarray] = None, source_frame: Optional[np.ndarray] = None, view=None) -> bool:
        detected = self._has_silver_band(hsv)

        if detected:
            self._positive_count += 1
        else:
            self._positive_count = 0

        return self._positive_count >= self.debounce_frames

    def _has_silver_band(self, hsv: np.ndarray) -> bool:
        saturation = hsv[:, :, 1]
        value = hsv[:, :, 2]
        floor_value = float(np.median(value))

        bright = (saturation <= SILVER_LINE_MAX_SATURATION) & (value >= floor_value + SILVER_LINE_BRIGHT_MARGIN)
        mask = clean_mask((bright.astype(np.uint8)) * 255)

        min_area = self.min_area_ratio * mask.size
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            metrics = contour_metrics(contour)
            if looks_like_line(metrics, min_area, SILVER_LINE_MIN_ASPECT):
                return True
        return False

    def reset(self) -> None:
        """Reseta o contador de debouncing."""
        self._positive_count = 0
