import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.config import RobotContext
from raspberry.preview import PreviewWindow
from raspberry.vision.ball_detector import Ball
from raspberry.vision.line_detector import LineDetection


def make_context():
    context = RobotContext()
    context.current_state = "FOLLOW_LINE"
    context.last_detections = {
        "line": LineDetection(center_x=200.0, error=40.0, confidence=0.8, frame_width=320),
        "ball": Ball(x=100.0, y=120.0, radius=15.0, distance=18.0, confidence=0.7),
    }
    return context


class PreviewEnablementTests(unittest.TestCase):
    def test_auto_mode_follows_display_environment(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(PreviewWindow(mode="auto").is_enabled())

        with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=True):
            self.assertTrue(PreviewWindow(mode="auto").is_enabled())

        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}, clear=True):
            self.assertTrue(PreviewWindow(mode="auto").is_enabled())

    def test_explicit_modes_ignore_display(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(PreviewWindow(mode="on").is_enabled())
        with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=True):
            self.assertFalse(PreviewWindow(mode="off").is_enabled())

    def test_environment_variable_overrides_config(self):
        with patch.dict(os.environ, {"ROBOT_PREVIEW": "off", "DISPLAY": ":0"}, clear=True):
            self.assertFalse(PreviewWindow(mode="auto").is_enabled())
        with patch.dict(os.environ, {"ROBOT_PREVIEW": "on"}, clear=True):
            self.assertTrue(PreviewWindow(mode="auto").is_enabled())


class PreviewRenderTests(unittest.TestCase):
    def setUp(self):
        self.frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.env = patch.dict(os.environ, {"DISPLAY": ":0"}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    @patch("raspberry.preview.cv2.waitKey", return_value=255)
    @patch("raspberry.preview.cv2.imshow")
    @patch("raspberry.preview.cv2.resizeWindow")
    @patch("raspberry.preview.cv2.namedWindow")
    def test_render_draws_and_shows_frame(self, mock_named, mock_resize, mock_imshow, mock_wait):
        preview = PreviewWindow(mode="on")

        preview.render(self.frame, make_context(), "MOVE,110,0,12", "cam: picamera2 30 fps")

        mock_named.assert_called_once()
        mock_imshow.assert_called_once()
        shown = mock_imshow.call_args[0][1]
        self.assertEqual(shown.shape, self.frame.shape)
        # O overlay precisa ter desenhado algo sobre o frame preto original.
        self.assertGreater(int(shown.sum()), 0)

    @patch("raspberry.preview.cv2.waitKey", return_value=255)
    @patch("raspberry.preview.cv2.imshow")
    @patch("raspberry.preview.cv2.resizeWindow")
    @patch("raspberry.preview.cv2.namedWindow")
    def test_render_is_throttled(self, mock_named, mock_resize, mock_imshow, mock_wait):
        preview = PreviewWindow(mode="on", target_fps=1)

        for _ in range(5):
            preview.render(self.frame, make_context(), "STOP", None)

        self.assertEqual(mock_imshow.call_count, 1)

    @patch("raspberry.preview.cv2.waitKey", return_value=ord("q"))
    @patch("raspberry.preview.cv2.imshow")
    @patch("raspberry.preview.cv2.resizeWindow")
    @patch("raspberry.preview.cv2.namedWindow")
    def test_q_key_requests_quit(self, mock_named, mock_resize, mock_imshow, mock_wait):
        preview = PreviewWindow(mode="on")

        preview.render(self.frame, make_context(), "STOP", None)

        self.assertTrue(preview.quit_requested)

    @patch("raspberry.preview.cv2.namedWindow", side_effect=RuntimeError("built without GUI support"))
    def test_headless_build_disables_preview_permanently(self, mock_named):
        preview = PreviewWindow(mode="on")

        preview.render(self.frame, make_context(), "STOP", None)
        preview._last_render = 0.0  # ignora o throttle
        preview.render(self.frame, make_context(), "STOP", None)

        self.assertEqual(mock_named.call_count, 1)

    @patch("raspberry.preview.cv2.waitKey", return_value=255)
    @patch("raspberry.preview.cv2.imshow")
    @patch("raspberry.preview.cv2.resizeWindow")
    @patch("raspberry.preview.cv2.namedWindow")
    def test_render_survives_missing_detections(self, mock_named, mock_resize, mock_imshow, mock_wait):
        context = RobotContext()
        preview = PreviewWindow(mode="on")

        preview.render(self.frame, context, None, None)

        mock_imshow.assert_called_once()

    @patch("raspberry.preview.cv2.waitKey", return_value=255)
    @patch("raspberry.preview.cv2.imshow")
    @patch("raspberry.preview.cv2.resizeWindow")
    @patch("raspberry.preview.cv2.namedWindow")
    def test_render_handles_bgra_frames(self, mock_named, mock_resize, mock_imshow, mock_wait):
        preview = PreviewWindow(mode="on")

        preview.render(np.zeros((480, 640, 4), dtype=np.uint8), make_context(), "STOP", None)

        shown = mock_imshow.call_args[0][1]
        self.assertEqual(shown.shape[2], 3)

    def test_render_does_nothing_without_frame(self):
        preview = PreviewWindow(mode="on")
        preview.render(None, make_context(), "STOP", None)  # não deve levantar


if __name__ == "__main__":
    unittest.main()
