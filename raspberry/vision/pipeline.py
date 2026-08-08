from __future__ import annotations

import inspect
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

import cv2
import numpy as np

from ..config import VISION_PROCESS_HEIGHT, VISION_PROCESS_WIDTH, VISION_ROI

logger = logging.getLogger(__name__)


@dataclass
class VisionResult:
    detections: Dict[str, object] = field(default_factory=dict)
    processed_frame_shape: Optional[tuple[int, int]] = None
    # Momento (time.monotonic) em que o frame foi capturado. É o que permite ao
    # loop principal medir a idade real do resultado.
    captured_at: float = field(default_factory=time.monotonic)


class VisionPipeline:
    """Executa o pipeline visual uma única vez por frame, compartilhando HSV entre detectores."""

    def __init__(self, camera_manager=None, detectors=None, process_width: Optional[int] = None, process_height: Optional[int] = None, roi: Optional[tuple[float, float, float, float]] = None) -> None:
        self.camera_manager = camera_manager
        self.detectors = detectors or {}
        self.process_width = process_width or VISION_PROCESS_WIDTH
        self.process_height = process_height or VISION_PROCESS_HEIGHT
        self.roi = roi or VISION_ROI

    def process_frame(self, frame: Optional[np.ndarray], captured_at: Optional[float] = None) -> Optional[VisionResult]:
        if frame is None:
            return None

        captured_at = captured_at if captured_at is not None else time.monotonic()
        working_frame = self._prepare_frame(frame)
        if working_frame is None:
            return None

        hsv = cv2.cvtColor(working_frame, cv2.COLOR_BGR2HSV)
        detections: Dict[str, object] = {}
        for name, detector in self.detectors.items():
            try:
                if hasattr(detector, "detect_from_hsv"):
                    detections[name] = self._call_detector(detector, hsv, working_frame, frame)
                else:
                    detections[name] = detector.detect(frame)
            except Exception as exc:
                # Mostrar warnings para facilitar debug, não silenciar erros
                logger.warning("Falha no detector %s: %s", name, exc)
                detections[name] = None

        return VisionResult(detections=detections, processed_frame_shape=working_frame.shape[:2], captured_at=captured_at)

    def _call_detector(self, detector, hsv: np.ndarray, working_frame: np.ndarray, source_frame: Optional[np.ndarray]) -> object:
        try:
            return detector.detect_from_hsv(hsv, frame=working_frame, source_frame=source_frame)
        except TypeError:
            params = inspect.signature(detector.detect_from_hsv).parameters
            if "source_frame" in params:
                return detector.detect_from_hsv(hsv, frame=working_frame, source_frame=source_frame)
            if "frame" in params:
                return detector.detect_from_hsv(hsv, working_frame)
            return detector.detect_from_hsv(hsv)

    def _prepare_frame(self, frame: np.ndarray) -> Optional[np.ndarray]:
        if frame is None:
            return None
        height, width = frame.shape[:2]
        if self.roi:
            x0, y0, x1, y1 = self._normalize_roi(width, height)
            if x1 <= x0 or y1 <= y0:
                return None
            frame = frame[y0:y1, x0:x1]
        if self.process_width and self.process_height:
            frame = cv2.resize(frame, (self.process_width, self.process_height), interpolation=cv2.INTER_AREA)
        return frame

    def _normalize_roi(self, width: int, height: int) -> tuple[int, int, int, int]:
        x0, y0, x1, y1 = self.roi
        return (
            int(x0 * width),
            int(y0 * height),
            int(x1 * width),
            int(y1 * height),
        )
