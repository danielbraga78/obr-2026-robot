import logging
import sys
import time
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Optional, Sequence

import cv2
import numpy as np

from .config import (
    CAMERA_BACKEND,
    CAMERA_BACKEND_PREFERENCE,
    CAMERA_FPS,
    CAMERA_HEIGHT,
    CAMERA_READ_FAILURE_LIMIT,
    CAMERA_RECONNECT_DELAY,
    CAMERA_WARMUP_FRAMES,
    CAMERA_WIDTH,
)

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def opencv_has_gstreamer() -> bool:
    """Indica se este build do OpenCV consegue abrir pipelines GStreamer.

    Os wheels do pip (opencv-python / opencv-python-headless) não têm GStreamer,
    então tentar rpicamsrc/libcamerasrc neles falha sempre.
    """
    try:
        for line in cv2.getBuildInformation().splitlines():
            stripped = line.strip()
            if stripped.startswith("GStreamer:"):
                return "YES" in stripped.upper()
    except Exception:  # pragma: no cover - getBuildInformation não deve falhar
        return False
    return False


class CameraInterface(ABC):
    """Interface única para captura de vídeo independente do backend."""

    @abstractmethod
    def read_frame(self) -> Optional[np.ndarray]:
        raise NotImplementedError

    @abstractmethod
    def is_ready(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def release(self) -> None:
        raise NotImplementedError


class CameraManager(CameraInterface):
    """Seleciona e alterna entre backends de câmera de forma robusta."""

    def __init__(self, width: int = CAMERA_WIDTH, height: int = CAMERA_HEIGHT, fps: int = CAMERA_FPS, backend: str = CAMERA_BACKEND) -> None:
        self.width = width
        self.height = height
        self.fps = fps
        self.backend = backend
        self.capture = None
        self.picam = None
        self._read_failures = 0
        self._last_init_attempt = 0.0
        self._last_error: Optional[str] = None
        self._initialize()

    # ------------------------------------------------------------------
    # Inicialização
    # ------------------------------------------------------------------
    def _initialize(self) -> None:
        self._teardown()
        self._last_init_attempt = time.monotonic()
        for candidate in self._resolve_backends(self.backend):
            if self._try_backend(candidate):
                self.backend = candidate
                self._read_failures = 0
                logger.info("Câmera inicializada com backend %s (%sx%s @ %s fps)", candidate, self.width, self.height, self.fps)
                return
        logger.warning("Nenhum backend de câmera disponível")

    def _reinitialize_if_due(self) -> bool:
        """Reabre o backend respeitando CAMERA_RECONNECT_DELAY.

        Sem esse limite, uma câmera ausente faria a thread de visão tentar
        reabrir a cada iteração e travar o loop de controle.
        """
        if time.monotonic() - self._last_init_attempt < CAMERA_RECONNECT_DELAY:
            return False
        self._initialize()
        return self.is_ready()

    def _resolve_backends(self, backend: str) -> Sequence[str]:
        if backend and backend != "auto":
            return (backend,)
        return CAMERA_BACKEND_PREFERENCE

    def _try_backend(self, backend: str) -> bool:
        if backend == "picamera2":
            return self._try_picamera2()
        if backend == "opencv":
            return self._try_opencv_backends()
        return self._try_gstreamer_backend(backend)

    def _try_picamera2(self) -> bool:
        """Backend nativo da câmera CSI no Raspberry Pi OS Bookworm."""
        try:
            from picamera2 import Picamera2
        except Exception as exc:
            logger.debug("Backend picamera2 indisponível: %s", exc)
            return False

        picam = None
        try:
            picam = Picamera2()
            frame_duration = int(1_000_000 / max(self.fps, 1))
            config = picam.create_video_configuration(
                # "RGB888" no picamera2 entrega o array já na ordem BGR do OpenCV.
                main={"size": (self.width, self.height), "format": "RGB888"},
                controls={"FrameDurationLimits": (frame_duration, frame_duration)},
                buffer_count=2,
            )
            picam.configure(config)
            picam.start()
            for _ in range(CAMERA_WARMUP_FRAMES):
                picam.capture_array()
            self.picam = picam
            return True
        except Exception as exc:
            logger.debug("Falha ao inicializar picamera2: %s", exc)
            if picam is not None:
                try:
                    picam.close()
                except Exception:
                    pass
            self.picam = None
            return False

    def _try_opencv_backends(self) -> bool:
        for index in (0, 1, 2, -1):
            capture = self._open_index(index)
            if capture is None:
                continue
            self._configure_capture(capture)
            if self._prime_capture(capture):
                self.capture = capture
                return True
            logger.debug("Câmera OpenCV no índice %s abriu mas não entregou frame", index)
            capture.release()
        return False

    def _open_index(self, index: int):
        apis = [cv2.CAP_V4L2, cv2.CAP_ANY] if sys.platform.startswith("linux") else [cv2.CAP_ANY]
        for api in apis:
            try:
                capture = cv2.VideoCapture(index, api)
            except Exception as exc:
                logger.debug("Falha ao abrir câmera OpenCV no índice %s (api %s): %s", index, api, exc)
                continue
            if capture is not None and capture.isOpened():
                return capture
            if capture is not None:
                capture.release()
        return None

    def _configure_capture(self, capture) -> None:
        """Aplica resolução, taxa e fila de captura mínima."""
        props = (
            (cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG")),  # YUYV limita a ~5 fps em muitas webcams
            (cv2.CAP_PROP_FRAME_WIDTH, self.width),
            (cv2.CAP_PROP_FRAME_HEIGHT, self.height),
            (cv2.CAP_PROP_FPS, self.fps),
            (cv2.CAP_PROP_BUFFERSIZE, 1),  # sem isso a fila acumula e o PID atua sobre imagem velha
        )
        for prop, value in props:
            try:
                capture.set(prop, value)
            except Exception as exc:
                logger.debug("Câmera não aceitou a propriedade %s: %s", prop, exc)

    def _prime_capture(self, capture) -> bool:
        """Confirma que o dispositivo entrega frames de verdade, não só abre."""
        frame = None
        for _ in range(max(CAMERA_WARMUP_FRAMES, 1)):
            try:
                ok, frame = capture.read()
            except Exception as exc:
                logger.debug("Falha ao ler frame de aquecimento: %s", exc)
                return False
            if not ok or frame is None:
                return False
        return frame is not None and getattr(frame, "size", 0) > 0

    def _try_gstreamer_backend(self, backend: str) -> bool:
        pipeline = self._build_pipeline(backend)
        if not pipeline:
            return False
        if not opencv_has_gstreamer():
            logger.debug("OpenCV sem suporte a GStreamer; backend %s indisponível", backend)
            return False

        try:
            capture = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        except Exception as exc:
            logger.debug("Falha ao abrir backend %s: %s", backend, exc)
            return False

        if capture.isOpened() and self._prime_capture(capture):
            self.capture = capture
            return True
        capture.release()
        return False

    def _build_pipeline(self, backend: str) -> Optional[str]:
        caps = f"width={self.width},height={self.height},framerate={self.fps}/1"
        if backend == "rpicam":
            return f"rpicamsrc ! video/x-raw,{caps} ! videoconvert ! appsink drop=true max-buffers=1"
        if backend == "libcamera":
            return f"libcamerasrc ! video/x-raw,{caps},format=YUY2 ! videoconvert ! appsink drop=true max-buffers=1"
        return None

    # ------------------------------------------------------------------
    # Captura
    # ------------------------------------------------------------------
    def read_frame(self) -> Optional[np.ndarray]:
        if not self.is_ready() and not self._reinitialize_if_due():
            return None

        frame = self._grab_frame()
        if frame is None:
            self._read_failures += 1
            self._last_error = "Falha ao ler frame"
            if self._read_failures >= CAMERA_READ_FAILURE_LIMIT:
                logger.warning("Câmera sem frames válidos (%s falhas); reabrindo backend %s", self._read_failures, self.backend)
                self._teardown()
            return None

        self._read_failures = 0
        return frame

    def _grab_frame(self) -> Optional[np.ndarray]:
        if self.picam is not None:
            try:
                frame = self.picam.capture_array()
            except Exception as exc:
                logger.debug("Falha ao capturar frame do picamera2: %s", exc)
                return None
            return frame if frame is not None and frame.size > 0 else None

        if self.capture is None:
            return None
        try:
            ok, frame = self.capture.read()
        except Exception as exc:
            logger.debug("Falha ao ler frame: %s", exc)
            return None
        if not ok or frame is None:
            return None
        return frame

    def is_ready(self) -> bool:
        if self.picam is not None:
            return True
        return self.capture is not None and self.capture.isOpened()

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    # ------------------------------------------------------------------
    # Encerramento
    # ------------------------------------------------------------------
    def _teardown(self) -> None:
        if self.capture is not None:
            try:
                self.capture.release()
            except Exception:
                pass
            self.capture = None
        if self.picam is not None:
            try:
                self.picam.stop()
                self.picam.close()
            except Exception:
                pass
            self.picam = None

    def release(self) -> None:
        self._teardown()
