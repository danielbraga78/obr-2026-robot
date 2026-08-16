from __future__ import annotations

import inspect
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

from ..config import (
    VISION_DEFAULT_ROI_PROFILE,
    VISION_PROCESS_HEIGHT,
    VISION_PROCESS_WIDTH,
    VISION_ROI,
    VISION_ROI_PROFILES,
)

logger = logging.getLogger(__name__)


@dataclass
class FrameView:
    """Um recorte do quadro, já redimensionado e convertido, com o mapa de volta.

    O mapa importa: com ROI por detector, um mesmo y significa distâncias
    diferentes em views diferentes. Quem estima distância precisa da posição no
    quadro original, não na view.
    """

    name: str
    frame: np.ndarray  # BGR, recortado e redimensionado
    hsv: np.ndarray
    roi: Tuple[float, float, float, float]  # Normalizada, no quadro original

    def source_y_norm(self, y: float) -> float:
        """Converte y da view para -1 (topo) a +1 (base) do quadro original."""
        height = self.frame.shape[0]
        if height <= 0:
            return 0.0
        _, y0, _, y1 = self.roi
        return (y0 + (y / height) * (y1 - y0)) * 2.0 - 1.0

    def source_x_norm(self, x: float) -> float:
        """Converte x da view para -1 (esquerda) a +1 (direita) do quadro original."""
        width = self.frame.shape[1]
        if width <= 0:
            return 0.0
        x0, _, x1, _ = self.roi
        return (x0 + (x / width) * (x1 - x0)) * 2.0 - 1.0


@dataclass
class VisionResult:
    detections: Dict[str, object] = field(default_factory=dict)
    processed_frame_shape: Optional[tuple[int, int]] = None
    # Momento (time.monotonic) em que o frame foi capturado. É o que permite ao
    # loop principal medir a idade real do resultado.
    captured_at: float = field(default_factory=time.monotonic)
    views: Dict[str, FrameView] = field(default_factory=dict)


class VisionPipeline:
    """Executa o pipeline visual uma vez por frame.

    Cada detector declara em `roi_profile` a região que quer analisar. As views
    são construídas sob demanda e compartilhadas entre os detectores que pedem o
    mesmo perfil, então o custo é uma conversão HSV por perfil em uso — não uma
    por detector.
    """

    def __init__(self, camera_manager=None, detectors=None, process_width: Optional[int] = None, process_height: Optional[int] = None, roi: Optional[tuple[float, float, float, float]] = None) -> None:
        self.camera_manager = camera_manager
        self.detectors = detectors or {}
        self.process_width = process_width or VISION_PROCESS_WIDTH
        self.process_height = process_height or VISION_PROCESS_HEIGHT
        # ROI explícita sobrepõe os perfis: usada por testes e por chamadas que
        # querem uma região específica para todos os detectores.
        self.roi = roi
        self._signature_cache: Dict[int, set] = {}

    def process_frame(self, frame: Optional[np.ndarray], captured_at: Optional[float] = None) -> Optional[VisionResult]:
        if frame is None:
            return None

        captured_at = captured_at if captured_at is not None else time.monotonic()
        views: Dict[str, FrameView] = {}
        detections: Dict[str, object] = {}

        for name, detector in self.detectors.items():
            profile = self._profile_for(detector)
            view = views.get(profile)
            if view is None:
                view = self._build_view(profile, frame)
                if view is None:
                    detections[name] = None
                    continue
                views[profile] = view
            try:
                detections[name] = self._call_detector(detector, view, frame)
            except Exception as exc:
                # Mostrar warnings para facilitar debug, não silenciar erros
                logger.warning("Falha no detector %s: %s", name, exc)
                detections[name] = None

        if not views:
            return None

        reference = views.get(VISION_DEFAULT_ROI_PROFILE) or next(iter(views.values()))
        return VisionResult(
            detections=detections,
            processed_frame_shape=reference.frame.shape[:2],
            captured_at=captured_at,
            views=views,
        )

    def _profile_for(self, detector) -> str:
        if self.roi is not None:
            return "custom"
        return getattr(detector, "roi_profile", VISION_DEFAULT_ROI_PROFILE)

    def _roi_for_profile(self, profile: str) -> Tuple[float, float, float, float]:
        if profile == "custom" and self.roi is not None:
            return self.roi
        return VISION_ROI_PROFILES.get(profile, VISION_ROI)

    def _build_view(self, profile: str, frame: np.ndarray) -> Optional[FrameView]:
        roi = self._roi_for_profile(profile)
        working_frame = self._prepare_frame(frame, roi)
        if working_frame is None:
            return None
        hsv = cv2.cvtColor(working_frame, cv2.COLOR_BGR2HSV)
        return FrameView(name=profile, frame=working_frame, hsv=hsv, roi=roi)

    def _call_detector(self, detector, view: FrameView, source_frame: Optional[np.ndarray]) -> object:
        if not hasattr(detector, "detect_from_hsv"):
            return detector.detect(view.frame)

        parameters = self._parameters_of(detector.detect_from_hsv)
        kwargs = {}
        if "frame" in parameters:
            kwargs["frame"] = view.frame
        if "source_frame" in parameters:
            kwargs["source_frame"] = source_frame
        if "view" in parameters:
            kwargs["view"] = view
        return detector.detect_from_hsv(view.hsv, **kwargs)

    def _parameters_of(self, method) -> set:
        key = id(method.__func__ if hasattr(method, "__func__") else method)
        cached = self._signature_cache.get(key)
        if cached is None:
            cached = set(inspect.signature(method).parameters)
            self._signature_cache[key] = cached
        return cached

    def _prepare_frame(self, frame: np.ndarray, roi: Optional[tuple[float, float, float, float]] = None) -> Optional[np.ndarray]:
        if frame is None:
            return None
        height, width = frame.shape[:2]
        roi = roi if roi is not None else (self.roi or VISION_ROI)
        if roi:
            x0, y0, x1, y1 = self._normalize_roi(width, height, roi)
            if x1 <= x0 or y1 <= y0:
                return None
            frame = frame[y0:y1, x0:x1]
        return self._fit(frame)

    def _fit(self, frame: np.ndarray) -> np.ndarray:
        """Reduz o recorte cabendo na caixa de processamento, **sem deformar**.

        O redimensionamento antigo forçava toda ROI para 320x240. Um recorte de
        640x216 esticava 2,2x na vertical e uma bola redonda virava elipse com
        aspecto 2,2 — reprovada pelo filtro de forma que distingue bola de linha.
        Com ROI por detector isso deixou de ser detalhe: cada perfil tem uma
        proporção diferente. Só reduzimos: ampliar não acrescenta informação e
        mudaria a escala dos limiares de área.
        """
        if not (self.process_width and self.process_height):
            return frame
        height, width = frame.shape[:2]
        if not (height and width):
            return frame
        scale = min(self.process_width / width, self.process_height / height, 1.0)
        if scale >= 1.0:
            return frame
        target = (max(1, int(round(width * scale))), max(1, int(round(height * scale))))
        return cv2.resize(frame, target, interpolation=cv2.INTER_AREA)

    def _normalize_roi(self, width: int, height: int, roi: Optional[tuple[float, float, float, float]] = None) -> tuple[int, int, int, int]:
        x0, y0, x1, y1 = roi if roi is not None else (self.roi or VISION_ROI)
        return (
            int(x0 * width),
            int(y0 * height),
            int(x1 * width),
            int(y1 * height),
        )
