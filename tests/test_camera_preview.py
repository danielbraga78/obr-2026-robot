import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.camera import CameraManager


class CameraPreviewTests(unittest.TestCase):
    def test_should_show_preview_depends_on_display_environment(self):
        manager = CameraManager.__new__(CameraManager)

        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(manager._should_show_preview())

        with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=True):
            self.assertTrue(manager._should_show_preview())


if __name__ == "__main__":
    unittest.main()
