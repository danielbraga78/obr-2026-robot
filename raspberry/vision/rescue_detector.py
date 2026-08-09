import cv2
import numpy as np

from ..config import RESCUE_MAX, RESCUE_MIN


class RescueDetector:
    """Detector independente para a área de resgate, baseado em cor.
    
    Implementa debouncing para evitar false positives: requer confirmação
    em 2 frames consecutivos antes de reportar detecção.
    """

    def __init__(self, debounce_frames: int = 2):
        self.debounce_frames = debounce_frames
        self._positive_count = 0  # Contador de frames positivos consecutivos

    def detect(self, frame: np.ndarray) -> bool:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return self.detect_from_hsv(hsv)

    def detect_from_hsv(self, hsv: np.ndarray, frame: np.ndarray | None = None, source_frame: np.ndarray | None = None) -> bool:
        mask = cv2.inRange(hsv, np.array(RESCUE_MIN), np.array(RESCUE_MAX))
        non_zero_pixels = int(cv2.countNonZero(mask))
        area_ratio = non_zero_pixels / float(mask.size) if mask.size else 0.0
        detected = non_zero_pixels >= max(16, int(mask.size * 0.001)) and area_ratio >= 0.001

        # Debouncing simples: requer N frames positivos para confirmar
        if detected:
            self._positive_count += 1
        else:
            self._positive_count = 0

        return self._positive_count >= self.debounce_frames
    
    def reset(self) -> None:
        """Reseta o contador de debouncing."""
        self._positive_count = 0
