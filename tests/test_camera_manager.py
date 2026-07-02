import subprocess
import unittest
from unittest.mock import patch

import numpy as np

from raspberry.camera import CameraManager


class DummyCapture:
    def __init__(self, opened: bool = True) -> None:
        self.opened = opened

    def isOpened(self) -> bool:
        return self.opened

    def read(self):
        return True, np.zeros((10, 10, 3), dtype=np.uint8)

    def release(self) -> None:
        self.opened = False


class CameraManagerTests(unittest.TestCase):
    @patch("raspberry.camera.subprocess.run")
    @patch("raspberry.camera.cv2.VideoCapture")
    def test_camera_manager_falls_back_to_opencv_when_primary_backend_fails(self, mock_video_capture, mock_run) -> None:
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout='{"opened": true}', stderr="")
        mock_video_capture.return_value = DummyCapture(True)

        manager = CameraManager(backend="auto")

        self.assertTrue(manager.is_ready())
        self.assertEqual(manager.backend, "opencv")

    @patch("raspberry.camera.subprocess.run")
    def test_camera_manager_uses_subprocess_probe_for_opencv(self, mock_run) -> None:
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=139, stdout="", stderr="segfault")

        manager = CameraManager(backend="opencv")

        self.assertFalse(manager.is_ready())
        self.assertIsNone(manager.capture)


if __name__ == "__main__":
    unittest.main()
