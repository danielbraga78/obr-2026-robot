from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np

from ..config import (
    LINE_BAND_MIN_PIXELS,
    LINE_CORNER_HEADING,
    LINE_FAR_BAND,
    LINE_MAX,
    LINE_MAX_COVERAGE,
    LINE_MIN,
    LINE_MIN_AREA,
    LINE_MIN_CONTRAST,
    LINE_NEAR_BAND,
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
    near_x: Optional[float] = None  # Centro da linha na faixa inferior (onde o robô está)
    far_x: Optional[float] = None  # Centro na faixa superior (para onde a linha vai)
    heading: float = 0.0  # (far_x - near_x) normalizado: rumo da pista adiante
    corner: bool = False  # Curva fechada à frente
    corner_side: int = 0  # -1 esquerda, +1 direita, 0 indefinido


class LineDetector:
    """Detecta a linha principal, por limiar adaptativo ou por faixa HSV fixa."""

    # A faixa logo à frente do robô. Usar o quadro inteiro misturaria a linha
    # próxima com curvas distantes e distorceria o erro do PID.
    roi_profile = "near"

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

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return LineDetection(frame_width=width, threshold=threshold, coverage=coverage, reason="nenhum contorno")

        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        frame_area = float(mask.shape[0] * mask.shape[1])
        contour_coverage = area / frame_area
        hull_area = cv2.contourArea(cv2.convexHull(largest))
        solidity = area / hull_area if hull_area > 0 else 1.0
        if coverage > LINE_MAX_COVERAGE and contour_coverage > LINE_MAX_COVERAGE and solidity > 0.9:
            return LineDetection(frame_width=width, threshold=threshold, coverage=coverage, reason=f"mascara cobre {coverage:.0%} do quadro")
        if area < LINE_MIN_AREA:
            return LineDetection(frame_width=width, threshold=threshold, coverage=coverage, reason=f"area {area:.0f} < {LINE_MIN_AREA}")

        moments = cv2.moments(largest)
        if moments["m00"] == 0:
            return LineDetection(frame_width=width, threshold=threshold, coverage=coverage, reason="momento nulo")

        line_mask = np.zeros(mask.shape, dtype=np.uint8)
        cv2.drawContours(line_mask, [largest], -1, 255, thickness=cv2.FILLED)

        near_x = self._band_center(line_mask, 1.0 - LINE_NEAR_BAND, 1.0)
        far_x = self._band_center(line_mask, 0.0, LINE_FAR_BAND)

        # A posição que interessa ao controle é a mais próxima do robô. O
        # centroide do contorno inteiro é puxado pelo trecho distante e, numa
        # curva de 90 graus, aponta para o meio do "L" — um lugar onde a linha
        # não está.
        center_x = near_x if near_x is not None else moments["m10"] / moments["m00"]
        error = center_x - (width / 2)
        half_width = max(1.0, width / 2.0)

        heading = 0.0
        if near_x is not None and far_x is not None:
            heading = max(-1.0, min(1.0, (far_x - near_x) / half_width))
        corner = abs(heading) >= LINE_CORNER_HEADING

        confidence = min(1.0, area / 10000.0)
        return LineDetection(
            center_x=center_x,
            error=error,
            confidence=confidence,
            frame_width=width,
            threshold=threshold,
            coverage=coverage,
            near_x=near_x,
            far_x=far_x,
            heading=heading,
            corner=corner,
            corner_side=(0 if not corner else (1 if heading > 0 else -1)),
        )

    @staticmethod
    def _band_center(line_mask: np.ndarray, top_fraction: float, bottom_fraction: float) -> Optional[float]:
        """Centro horizontal da linha numa faixa horizontal da máscara."""
        height = line_mask.shape[0]
        y0 = int(top_fraction * height)
        y1 = max(y0 + 1, int(bottom_fraction * height))
        band = line_mask[y0:y1]
        if int(np.count_nonzero(band)) < LINE_BAND_MIN_PIXELS:
            return None
        columns = band.sum(axis=0, dtype=np.float64)
        total = columns.sum()
        if total <= 0:
            return None
        return float((columns * np.arange(band.shape[1])).sum() / total)

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
