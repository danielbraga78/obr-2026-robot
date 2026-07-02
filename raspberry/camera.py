import json
import logging
import subprocess
import sys
from abc import ABC, abstractmethod
from typing import List, Optional, Sequence

import cv2
import numpy as np

from .config import CAMERA_BACKEND, CAMERA_BACKEND_PREFERENCE, CAMERA_FPS, CAMERA_HEIGHT, CAMERA_WIDTH

logger = logging.getLogger(__name__)


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
        self._initialize()

    def _initialize(self) -> None:
        self.capture = None
        backends = self._resolve_backends(self.backend)
        for candidate in backends:
            if self._try_backend(candidate):
                self.backend = candidate
                logger.info("Câmera inicializada com backend %s", self.backend)
                return
        logger.warning("Nenhum backend de câmera disponível")

    def _resolve_backends(self, backend: str) -> Sequence[str]:
        if backend and backend != "auto":
            return (backend,)
        return CAMERA_BACKEND_PREFERENCE

    def _try_backend(self, backend: str) -> bool:
        if backend == "picamera2":
            try:
                import picamera2  # noqa: F401
            except Exception as exc:
                logger.debug("Backend picamera2 indisponível: %s", exc)
                return False
        elif backend == "libcamera":
            try:
                import libcamera  # noqa: F401
            except Exception as exc:
                logger.debug("Backend libcamera indisponível: %s", exc)
                return False

        if backend == "opencv":
            return self._try_opencv_backends()

        pipeline = self._build_pipeline(backend)
        if not pipeline:
            return False

        try:
            capture = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        except Exception as exc:
            logger.debug("Falha ao abrir backend %s: %s", backend, exc)
            return False

        if capture.isOpened():
            self.capture = capture
            return True
        capture.release()
        return False

    def _try_opencv_backends(self) -> bool:
        for index in (0, 1, 2, -1):
            if not self._probe_opencv_backend(index):
                continue
            try:
                capture = cv2.VideoCapture(index)
            except Exception as exc:
                logger.debug("Falha ao abrir câmera OpenCV no índice %s: %s", index, exc)
                continue
            if capture.isOpened():
                self.capture = capture
                return True
            capture.release()
        return False

    def _probe_opencv_backend(self, index: int) -> bool:
        probe_code = (
            "import json, sys; import cv2; "
            "cap = cv2.VideoCapture(int(sys.argv[1])); "
            "print(json.dumps({'opened': bool(cap.isOpened())}))"
        )
        try:
            completed = subprocess.run(
                [sys.executable, "-c", probe_code, str(index)],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError, ValueError) as exc:
            logger.debug("Falha na verificação da câmera OpenCV no índice %s: %s", index, exc)
            return False

        if completed.returncode != 0:
            logger.debug("Probe OpenCV para índice %s falhou com código %s: %s", index, completed.returncode, completed.stderr.strip())
            return False

        try:
            payload = json.loads(completed.stdout.strip() or "{}")
        except json.JSONDecodeError:
            logger.debug("Resposta inválida do probe OpenCV para índice %s: %s", index, completed.stdout.strip())
            return False

        return bool(payload.get("opened", False))

    def _build_pipeline(self, backend: str) -> Optional[str]:
        if backend == "rpicam":
            return (
                "rpicamsrc ! "
                "video/x-raw,width=640,height=480,framerate=30/1 ! "
                "videoconvert ! appsink"
            )
        if backend == "libcamera":
            return (
                "libcamerasrc ! "
                "video/x-raw,width=640,height=480,format=YUY2,framerate=30/1 ! "
                "videoconvert ! appsink"
            )
        return None

    def read_frame(self) -> Optional[np.ndarray]:
        if not self.is_ready():
            self._initialize()
            if not self.is_ready():
                return None
        ok, frame = self.capture.read()
        if not ok or frame is None:
            self._last_error = "Falha ao ler frame"
            self._initialize()
            return None
        return frame

    def is_ready(self) -> bool:
        return self.capture is not None and self.capture.isOpened()

    def release(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None
