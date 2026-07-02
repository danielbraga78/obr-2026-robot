from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from ..config import BALL_MAX, BALL_MIN


@dataclass
class Ball:
    x: float
    y: float
    radius: float
    distance: float
    confidence: float


class BallDetector:
    """Detecta uma bola usando máscara HSV e Hough Circles."""

    def detect(self, frame: np.ndarray) -> Optional[Ball]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return self.detect_from_hsv(hsv, frame=frame)

    def detect_from_hsv(self, hsv: np.ndarray, frame: Optional[np.ndarray] = None, source_frame: Optional[np.ndarray] = None) -> Optional[Ball]:
        if frame is None:
            frame = source_frame
        if frame is None:
            return None
        mask = cv2.inRange(hsv, np.array(BALL_MIN), np.array(BALL_MAX))
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) < 100:
            return None
        moments = cv2.moments(largest)
        if moments["m00"] == 0:
            return None
        x = moments["m10"] / moments["m00"]
        y = moments["m01"] / moments["m00"]
        radius = max(5.0, np.sqrt(cv2.contourArea(largest) / np.pi))
        distance = max(5.0, 100.0 / (radius + 1.0))
        confidence = min(1.0, cv2.contourArea(largest) / 5000.0)
        return Ball(x=x, y=y, radius=radius, distance=distance, confidence=confidence)
