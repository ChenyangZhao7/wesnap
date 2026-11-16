import logging
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from PIL import Image

from wesnap.app import App
from wesnap.clipboard import ClipboardError


class StoreTest(unittest.TestCase):
    def setUp(self):
        logging.getLogger("wesnap").addHandler(logging.NullHandler())
        logging.getLogger("wesnap-test").addHandler(logging.NullHandler())
    def bare_app(self, save_dir):
        app = object.__new__(App)
        app.settings = {"save_dir": save_dir, "auto_save": True, "auto_copy": True}
        app.log = logging.getLogger("wesnap-test")
        app.notices = []
        app.saved_as = []
        app.pins = []
        app.longshot = None
        app.tray = SimpleNamespace(
            notify=lambda title, message: app.notices.append(message))
        app.save_as = lambda image: (app.saved_as.append(image), False)[1]
        return app

    def test_clipboard_busy_still_saves(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = self.bare_app(tmp)
            image = Image.new("RGB", (10, 10), "red")
            with mock.patch("wesnap.app.copy_image",
                            side_effect=ClipboardError("busy")):
                ok = App._store(app, image, "save_copy")
            self.assertTrue(ok)
            files = list(Path(tmp).glob("Screenshot_*.png"))
            self.assertEqual(len(files), 1)
            self.assertTrue(any("复制到剪贴板失败" in note for note in app.notices))

    def test_copy_only_failure_falls_back_to_save_as(self):
        app = self.bare_app(tempfile.mkdtemp())
        image = Image.new("RGB", (10, 10), "red")
        with mock.patch("wesnap.app.copy_image",
                        side_effect=ClipboardError("busy")):
            ok = App._store(app, image, "copy")
        self.assertFalse(ok)
        self.assertEqual(len(app.saved_as), 1)

    def test_longshot_done_emergency_saves_when_store_fails(self):
        app = self.bare_app(tempfile.mkdtemp())
        image = Image.new("RGB", (10, 10), "red")
        calls = []
        app.longshot = object()
        app._store = lambda image, plan: False
        app._emergency_save = lambda image: (calls.append(image), "X")[1]
        app._show_pins = lambda: calls.append("pins")
        App._longshot_done(app, image)
        self.assertIn(image, calls)
        self.assertIn("pins", calls)
        self.assertIsNone(app.longshot)


if __name__ == "__main__":
    unittest.main()
