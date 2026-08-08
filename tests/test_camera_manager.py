import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.camera import CameraManager


class DummyCapture:
    """Simula cv2.VideoCapture, incluindo dispositivos que abrem sem entregar frame."""

    def __init__(self, opened: bool = True, delivers_frames: bool = True) -> None:
        self.opened = opened
        self.delivers_frames = delivers_frames
        self.props = {}

    def isOpened(self) -> bool:
        return self.opened

    def set(self, prop, value) -> bool:
        self.props[prop] = value
        return True

    def read(self):
        if not self.delivers_frames:
            return False, None
        return True, np.zeros((10, 10, 3), dtype=np.uint8)

    def release(self) -> None:
        self.opened = False


class CameraManagerTests(unittest.TestCase):
    @patch("raspberry.camera.cv2.VideoCapture")
    def test_falls_back_to_opencv_when_primary_backends_fail(self, mock_video_capture) -> None:
        mock_video_capture.return_value = DummyCapture(True)

        manager = CameraManager(backend="auto")

        self.assertTrue(manager.is_ready())
        self.assertEqual(manager.active_backend, "opencv")

    @patch("raspberry.camera.cv2.VideoCapture")
    def test_device_that_opens_without_frames_is_rejected(self, mock_video_capture) -> None:
        mock_video_capture.return_value = DummyCapture(True, delivers_frames=False)

        manager = CameraManager(backend="opencv")

        self.assertFalse(manager.is_ready())
        self.assertIsNone(manager.capture)

    @patch("raspberry.camera.cv2.VideoCapture")
    def test_capture_properties_are_applied(self, mock_video_capture) -> None:
        import cv2

        capture = DummyCapture(True)
        mock_video_capture.return_value = capture

        manager = CameraManager(width=800, height=600, fps=25, backend="opencv")

        self.assertTrue(manager.is_ready())
        self.assertEqual(capture.props[cv2.CAP_PROP_FRAME_WIDTH], 800)
        self.assertEqual(capture.props[cv2.CAP_PROP_FRAME_HEIGHT], 600)
        self.assertEqual(capture.props[cv2.CAP_PROP_FPS], 25)
        self.assertEqual(capture.props[cv2.CAP_PROP_BUFFERSIZE], 1)

    @patch("raspberry.camera.opencv_has_gstreamer", return_value=False)
    @patch("raspberry.camera.cv2.VideoCapture")
    def test_gstreamer_backend_skipped_without_gstreamer_support(self, mock_video_capture, _mock_support) -> None:
        manager = CameraManager(backend="rpicam")

        self.assertFalse(manager.is_ready())
        mock_video_capture.assert_not_called()

    @patch("raspberry.camera.cv2.VideoCapture")
    def test_read_frame_only_reopens_after_reconnect_delay(self, mock_video_capture) -> None:
        mock_video_capture.return_value = DummyCapture(True)
        manager = CameraManager(backend="opencv")
        manager._teardown()

        with patch.object(manager, "_initialize") as mock_initialize:
            self.assertIsNone(manager.read_frame())
            mock_initialize.assert_not_called()  # dentro do CAMERA_RECONNECT_DELAY

            manager._last_init_attempt -= 10.0
            manager.read_frame()
            mock_initialize.assert_called_once()

    @patch("raspberry.camera.cv2.VideoCapture")
    def test_read_frame_reopens_only_after_repeated_failures(self, mock_video_capture) -> None:
        from raspberry.config import CAMERA_READ_FAILURE_LIMIT

        capture = DummyCapture(True)
        mock_video_capture.return_value = capture
        manager = CameraManager(backend="opencv")
        capture.delivers_frames = False

        for _ in range(CAMERA_READ_FAILURE_LIMIT - 1):
            self.assertIsNone(manager.read_frame())
            self.assertIsNotNone(manager.capture)

        self.assertIsNone(manager.read_frame())
        self.assertIsNone(manager.capture)


class CameraDiagnosticTests(unittest.TestCase):
    @patch("raspberry.camera.cv2.VideoCapture", return_value=DummyCapture(False))
    def test_failure_reasons_are_reported_per_backend(self, _mock_video_capture) -> None:
        manager = CameraManager(backend="auto")

        self.assertFalse(manager.is_ready())
        self.assertIsNone(manager.active_backend)
        # picamera2 não existe no ambiente de teste: a dica de instalação precisa aparecer.
        self.assertIn("picamera2", manager._backend_errors)
        self.assertIn("system-site-packages", manager._backend_errors["picamera2"])
        self.assertIn("opencv", manager._backend_errors)

    @patch("raspberry.camera.opencv_has_gstreamer", return_value=False)
    @patch("raspberry.camera.cv2.VideoCapture", return_value=DummyCapture(False))
    def test_gstreamer_reason_mentions_missing_support(self, _mock_capture, _mock_support) -> None:
        manager = CameraManager(backend="rpicam")

        self.assertIn("GStreamer", manager._backend_errors["rpicam"])

    @patch("raspberry.camera.cv2.VideoCapture", return_value=DummyCapture(False))
    def test_reconnect_delay_backs_off_after_repeated_failures(self, _mock_video_capture) -> None:
        from raspberry.config import CAMERA_MAX_RECONNECT_DELAY, CAMERA_RECONNECT_DELAY

        manager = CameraManager(backend="opencv")
        first = manager._reconnect_delay()

        for _ in range(5):
            manager._initialize()

        self.assertGreaterEqual(first, CAMERA_RECONNECT_DELAY)
        self.assertGreater(manager._reconnect_delay(), first)
        self.assertLessEqual(manager._reconnect_delay(), CAMERA_MAX_RECONNECT_DELAY)

    @patch("raspberry.camera.cv2.VideoCapture")
    def test_describe_reports_active_backend(self, mock_video_capture) -> None:
        mock_video_capture.return_value = DummyCapture(True)
        self.assertIn("opencv", CameraManager(backend="opencv").describe())

        mock_video_capture.return_value = DummyCapture(False)
        self.assertIn("nenhuma", CameraManager(backend="opencv").describe())


if __name__ == "__main__":
    unittest.main()
