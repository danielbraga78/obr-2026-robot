from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from ..config import LINE_MAX, LINE_MIN


@dataclass
class LineDetection:
    center_x: Optional[float] = None
    error: Optional[float] = None
    confidence: float = 0.0


class LineDetector:
    """Detecta a linha principal a partir de uma máscara HSV."""

    def detect(self, frame: np.ndarray) -> LineDetection:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return self.detect_from_hsv(hsv, frame=frame)

    def detect_from_hsv(self, hsv: np.ndarray, frame: Optional[np.ndarray] = None, source_frame: Optional[np.ndarray] = None) -> LineDetection:
        if frame is None:
            frame = source_frame
        if frame is None:
            return LineDetection()
        mask = cv2.inRange(hsv, np.array(LINE_MIN), np.array(LINE_MAX))
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return LineDetection()
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        if area < 100:
            return LineDetection()
        moments = cv2.moments(largest)
        if moments["m00"] == 0:
            return LineDetection()
        center_x = moments["m10"] / moments["m00"]
        width = frame.shape[1]
        error = center_x - (width / 2)
        confidence = min(1.0, area / 10000.0)
        return LineDetection(center_x=center_x, error=error, confidence=confidence)
