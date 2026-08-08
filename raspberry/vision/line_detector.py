from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np

from ..config import (
    LINE_MAX,
    LINE_MAX_COVERAGE,
    LINE_MIN,
    LINE_MIN_AREA,
    LINE_MIN_CONTRAST,
    LINE_THRESHOLD_MODE,
)


@dataclass
class LineDetection:
    center_x: Optional[float] = None
    error: Optional[float] = None  # Pixels a partir do centro do quadro processado
    confidence: float = 0.0
    frame_width: Optional[int] = None  # Largura do quadro em que o erro foi medido
    threshold: Optional[float] = None  # Limiar usado (modo adaptativo)
    coverage: float = 0.0  # Fração do quadro ocupada pela máscara
    reason: Optional[str] = None  # Por que não detectou, quando não detectou


class LineDetector:
    """Detecta a linha principal, por limiar adaptativo ou por faixa HSV fixa."""

    def __init__(self, mode: str = LINE_THRESHOLD_MODE) -> None:
        self.mode = mode
        self.last_mask: Optional[np.ndarray] = None  # Exposto para o preview

    def detect(self, frame: np.ndarray) -> LineDetection:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return self.detect_from_hsv(hsv, frame=frame)

    def detect_from_hsv(self, hsv: np.ndarray, frame: Optional[np.ndarray] = None, source_frame: Optional[np.ndarray] = None) -> LineDetection:
        if frame is None:
            frame = source_frame
        if frame is None:
            self.last_mask = None
            return LineDetection(reason="sem quadro")

        mask, threshold, reason = self._build_mask(hsv)
        self.last_mask = mask
        width = frame.shape[1]
        if mask is None:
            return LineDetection(frame_width=width, threshold=threshold, reason=reason)

        coverage = float(np.count_nonzero(mask)) / float(mask.size)
        if coverage > LINE_MAX_COVERAGE:
            return LineDetection(frame_width=width, threshold=threshold, coverage=coverage, reason=f"mascara cobre {coverage:.0%} do quadro")

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return LineDetection(frame_width=width, threshold=threshold, coverage=coverage, reason="nenhum contorno")

        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        if area < LINE_MIN_AREA:
            return LineDetection(frame_width=width, threshold=threshold, coverage=coverage, reason=f"area {area:.0f} < {LINE_MIN_AREA}")

        moments = cv2.moments(largest)
        if moments["m00"] == 0:
            return LineDetection(frame_width=width, threshold=threshold, coverage=coverage, reason="momento nulo")

        center_x = moments["m10"] / moments["m00"]
        error = center_x - (width / 2)
        confidence = min(1.0, area / 10000.0)
        return LineDetection(
            center_x=center_x,
            error=error,
            confidence=confidence,
            frame_width=width,
            threshold=threshold,
            coverage=coverage,
        )

    def _build_mask(self, hsv: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[float], Optional[str]]:
        if self.mode == "hsv":
            mask = cv2.inRange(hsv, np.array(LINE_MIN), np.array(LINE_MAX))
            return self._clean(mask), None, None
        return self._adaptive_mask(hsv)

    def _adaptive_mask(self, hsv: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[float], Optional[str]]:
        """Otsu no canal V: separa linha e piso sem depender da iluminação.

        Otsu sempre divide a imagem em dois grupos, inclusive numa parede lisa.
        Por isso exigimos contraste real entre os dois grupos antes de aceitar.
        """
        value = hsv[:, :, 2]
        threshold, mask = cv2.threshold(value, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

        dark = value[mask > 0]
        light = value[mask == 0]
        if dark.size == 0 or light.size == 0:
            return None, float(threshold), "quadro uniforme"

        contrast = float(light.mean()) - float(dark.mean())
        if contrast < LINE_MIN_CONTRAST:
            return None, float(threshold), f"contraste {contrast:.0f} < {LINE_MIN_CONTRAST}"

        return self._clean(mask), float(threshold), None

    @staticmethod
    def _clean(mask: np.ndarray) -> np.ndarray:
        kernel = np.ones((3, 3), np.uint8)
        return cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
