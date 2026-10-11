from __future__ import annotations

import cv2
import numpy as np

from ..world_model import WorldModel
from .base_detector import Detector


class LineDetector(Detector):
    def __init__(self, world_model: WorldModel) -> None:
        super().__init__(world_model)

    def update(self, frame) -> None:
        if frame is None:
            return
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 150, 80]))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        self.world_model.line_visible = bool(contours)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            moments = cv2.moments(largest)
            if moments["m00"]:
                center_x = moments["m10"] / moments["m00"]
                self.world_model.line_offset = center_x - frame.shape[1] / 2
