"""Janela de preview exibida na tela do Raspberry Pi.

Mostra o que a câmera está vendo agora, com o que a visão detectou desenhado
por cima (ROI, linha, bola, estado e comando enviado ao Arduino).

Fica separado de CameraManager de propósito: o HighGUI do OpenCV só pode ser
usado na thread principal, enquanto a captura roda na thread de visão.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Optional

import cv2
import numpy as np

from .config import (
    PREVIEW_FPS,
    PREVIEW_MODE,
    PREVIEW_SHOW_OVERLAY,
    PREVIEW_WINDOW_NAME,
    VISION_PROCESS_HEIGHT,
    VISION_PROCESS_WIDTH,
    VISION_ROI,
)

logger = logging.getLogger(__name__)

_COLOR_ROI = (255, 180, 0)
_COLOR_CENTER = (140, 140, 140)
_COLOR_LINE = (0, 220, 0)
_COLOR_BALL = (0, 200, 255)
_COLOR_TEXT = (255, 255, 255)
_COLOR_ALERT = (0, 0, 255)
_FONT = cv2.FONT_HERSHEY_SIMPLEX


class PreviewWindow:
    """Renderiza o frame atual numa janela, com throttle próprio."""

    def __init__(self, mode: str = PREVIEW_MODE, target_fps: int = PREVIEW_FPS, window_name: str = PREVIEW_WINDOW_NAME, show_overlay: bool = PREVIEW_SHOW_OVERLAY) -> None:
        self.mode = (os.environ.get("ROBOT_PREVIEW") or mode or "auto").strip().lower()
        self.window_name = window_name
        self.show_overlay = show_overlay
        self.min_interval = 1.0 / max(target_fps, 1)
        self.quit_requested = False
        self.show_mask = False  # Alternado pela tecla 'm'
        self._state = "idle"  # idle | open | disabled
        self._last_render = 0.0

    # ------------------------------------------------------------------
    # Disponibilidade
    # ------------------------------------------------------------------
    @staticmethod
    def has_display() -> bool:
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

    def is_enabled(self) -> bool:
        if self.mode == "off":
            return False
        if self.mode == "on":
            return True
        return self.has_display()

    def describe_status(self) -> str:
        if self.mode == "off":
            return "preview desligado (PREVIEW_MODE=off)"
        if not self.is_enabled():
            return (
                "preview indisponível: nenhum display detectado (DISPLAY/WAYLAND_DISPLAY vazios). "
                "Abra um terminal na área de trabalho do Raspberry Pi, ou force com ROBOT_PREVIEW=on"
            )
        return f"preview ativo em modo '{self.mode}'"

    # ------------------------------------------------------------------
    # Renderização
    # ------------------------------------------------------------------
    def render(self, frame: Optional[np.ndarray], context=None, command: Optional[str] = None, stats: Optional[str] = None, mask: Optional[np.ndarray] = None) -> None:
        if frame is None or self._state == "disabled" or not self.is_enabled():
            return
        if threading.current_thread() is not threading.main_thread():
            # HighGUI do OpenCV não é thread-safe.
            return

        now = time.monotonic()
        if now - self._last_render < self.min_interval:
            return
        self._last_render = now

        try:
            canvas = self._build_canvas(frame, context, command, stats, mask)
            if self._state == "idle":
                cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(self.window_name, 640, 480)
                self._state = "open"
                logger.info("Preview aberto ('q' encerra, 'm' alterna a máscara da visão)")
            cv2.imshow(self.window_name, canvas)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                self.quit_requested = True
            elif key == ord("m"):
                self.show_mask = not self.show_mask
                logger.info("Máscara da visão: %s", "visível" if self.show_mask else "oculta")
        except Exception as exc:
            # Build headless não tem GUI: desliga de vez em vez de tentar a cada frame.
            logger.warning(
                "Preview desativado: %s. Instale 'opencv-python' (o pacote headless não tem janelas) "
                "ou defina ROBOT_PREVIEW=off para silenciar.",
                exc,
            )
            self._state = "disabled"

    def _build_canvas(self, frame: np.ndarray, context, command: Optional[str], stats: Optional[str], mask: Optional[np.ndarray] = None) -> np.ndarray:
        canvas = self._to_bgr(frame)
        if not self.show_overlay:
            return canvas
        canvas = canvas.copy()
        roi = self._roi_pixels(canvas.shape[1], canvas.shape[0])
        if self.show_mask:
            self._draw_mask(canvas, roi, mask)
        self._draw_roi(canvas, roi)
        detections = dict(getattr(context, "last_detections", None) or {})
        self._draw_line(canvas, roi, detections.get("line"))
        self._draw_ball(canvas, roi, detections.get("ball"))
        self._draw_status(canvas, context, command, stats, detections)
        return canvas

    @staticmethod
    def _to_bgr(frame: np.ndarray) -> np.ndarray:
        if frame.ndim == 2:
            return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        if frame.shape[2] == 4:
            return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        return frame

    @staticmethod
    def _roi_pixels(width: int, height: int) -> tuple[int, int, int, int]:
        x0, y0, x1, y1 = VISION_ROI
        return (int(x0 * width), int(y0 * height), int(x1 * width), int(y1 * height))

    def _draw_roi(self, canvas: np.ndarray, roi: tuple[int, int, int, int]) -> None:
        x0, y0, x1, y1 = roi
        cv2.rectangle(canvas, (x0, y0), (x1, y1), _COLOR_ROI, 2)
        cv2.putText(canvas, "ROI", (x0 + 6, y0 + 20), _FONT, 0.5, _COLOR_ROI, 1, cv2.LINE_AA)
        center = (x0 + x1) // 2
        cv2.line(canvas, (center, y0), (center, y1), _COLOR_CENTER, 1)

    def _draw_mask(self, canvas: np.ndarray, roi: tuple[int, int, int, int], mask: Optional[np.ndarray]) -> None:
        """Pinta de magenta o que o detector considerou linha.

        É o que mostra a diferença entre o que você vê e o que a visão vê.
        """
        if mask is None or mask.size == 0:
            return
        x0, y0, x1, y1 = roi
        if x1 <= x0 or y1 <= y0:
            return
        resized = cv2.resize(mask, (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST)
        region = canvas[y0:y1, x0:x1]
        tint = np.zeros_like(region)
        tint[:, :] = (255, 0, 255)
        selected = resized > 0
        region[selected] = cv2.addWeighted(region, 0.35, tint, 0.65, 0)[selected]

    def _to_source_x(self, value: float, roi: tuple[int, int, int, int], processed_width: Optional[int]) -> int:
        """Converte coordenada do quadro processado de volta para o frame original."""
        x0, _, x1, _ = roi
        scale = (x1 - x0) / max(processed_width or VISION_PROCESS_WIDTH, 1)
        return int(x0 + value * scale)

    def _draw_line(self, canvas: np.ndarray, roi: tuple[int, int, int, int], line) -> None:
        if line is None or getattr(line, "center_x", None) is None:
            return
        _, y0, _, y1 = roi
        px = self._to_source_x(line.center_x, roi, getattr(line, "frame_width", None))
        cv2.line(canvas, (px, y0), (px, y1), _COLOR_LINE, 2)
        cv2.circle(canvas, (px, (y0 + y1) // 2), 7, _COLOR_LINE, -1)

    def _draw_ball(self, canvas: np.ndarray, roi: tuple[int, int, int, int], ball) -> None:
        if ball is None or not hasattr(ball, "x"):
            return
        x0, y0, x1, y1 = roi
        scale_x = (x1 - x0) / max(VISION_PROCESS_WIDTH, 1)
        scale_y = (y1 - y0) / max(VISION_PROCESS_HEIGHT, 1)
        px = self._to_source_x(ball.x, roi, VISION_PROCESS_WIDTH)
        py = int(min(max(y0 + ball.y * scale_y, y0), y1))
        radius = max(4, int(ball.radius * scale_x))
        cv2.circle(canvas, (px, py), radius, _COLOR_BALL, 2)
        cv2.putText(canvas, f"bola {ball.distance:.0f}cm", (px + radius + 4, py), _FONT, 0.5, _COLOR_BALL, 1, cv2.LINE_AA)

    def _draw_status(self, canvas: np.ndarray, context, command: Optional[str], stats: Optional[str], detections: dict) -> None:
        line = detections.get("line")
        error = getattr(line, "error", None)
        rows = [
            f"estado: {getattr(context, 'current_state', '?')}",
            f"comando: {command or '-'}",
        ]
        if isinstance(error, (int, float)):
            threshold = getattr(line, "threshold", None)
            detail = f" | limiar {threshold:.0f}" if isinstance(threshold, (int, float)) else ""
            rows.append(f"erro linha: {error:.1f} px | cobertura {getattr(line, 'coverage', 0.0):.1%}{detail}")
        else:
            rows.append(f"sem linha: {getattr(line, 'reason', None) or 'nenhuma deteccao'}")
        if stats:
            rows.append(stats)
        if self.show_mask:
            rows.append("mascara visivel (magenta = considerado linha) - 'm' alterna")

        overlay = canvas.copy()
        cv2.rectangle(overlay, (0, 0), (canvas.shape[1], 22 * len(rows) + 12), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.45, canvas, 0.55, 0, canvas)
        for index, text in enumerate(rows):
            color = _COLOR_ALERT if index == 2 and error is None else _COLOR_TEXT
            cv2.putText(canvas, text, (10, 22 + index * 22), _FONT, 0.55, color, 1, cv2.LINE_AA)

    # ------------------------------------------------------------------
    def close(self) -> None:
        if self._state != "open":
            return
        try:
            cv2.destroyWindow(self.window_name)
            cv2.waitKey(1)
        except Exception:
            pass
        self._state = "idle"
