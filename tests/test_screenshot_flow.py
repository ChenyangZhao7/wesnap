import os
import tkinter as tk
import unittest

from PIL import ImageChops

from wesnap.capture import grab_virtual_screen
from wesnap.geometry import Rect
from wesnap.overlay import ScreenshotOverlay


class Actions:
    def __init__(self):
        self.image = None
        self.rect = None
        self.hits = 0

    def finish(self, image, rect):
        self.image = image
        self.rect = rect
        self.hits += 1
        return True

    def save_as(self, image):
        return False

    def pin(self, image):
        return False


@unittest.skipUnless(os.environ.get("WESNAP_GUI_TESTS") == "1",
                     "set WESNAP_GUI_TESTS=1 to run GUI integration tests")
class ScreenshotFlowTest(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.capture = grab_virtual_screen()
        self.actions = Actions()
        self.overlay = ScreenshotOverlay(self.root, self.capture, self.actions)
        self.addCleanup(self.overlay.close)
        self.overlay.start()
        self.root.update()
        self.canvas = self.overlay._active_view()[1]
        self.top = self.overlay._active_view()[0]

    def _drag(self, x0, y0, x1, y1):
        self.canvas.event_generate("<ButtonPress-1>", x=x0, y=y0)
        self.canvas.event_generate("<B1-Motion>", x=x1, y=y1)
        self.canvas.event_generate("<ButtonRelease-1>", x=x1, y=y1)

    def _click_button(self, name):
        rect = self.overlay._toolbar[name]
        self.canvas.event_generate("<ButtonPress-1>",
                                   x=rect.x - self.overlay.active.x + rect.w // 2,
                                   y=rect.y - self.overlay.active.y + rect.h // 2)

    def test_selection_is_pixel_perfect(self):
        self._drag(100, 120, 500, 420)
        self.assertEqual(self.overlay.rect, Rect(100, 120, 400, 300))
        self._click_button("done")
        expected = self.capture.image.crop((100, 120, 500, 420))
        self.assertEqual(self.actions.image.size, (400, 300))
        self.assertEqual(self.actions.image.tobytes(), expected.tobytes())

    def test_annotation_undo_and_finish(self):
        self._drag(100, 120, 500, 420)
        self._click_button("rect")
        self._drag(150, 150, 250, 220)
        self.assertEqual(len(self.overlay._undo), 1)
        self.canvas.focus_force()
        self.root.update()
        self.canvas.event_generate("<Control-z>")
        self.assertEqual(len(self.overlay._undo), 0)
        self._drag(150, 150, 250, 220)
        self._click_button("done")
        expected = self.capture.image.crop((100, 120, 500, 420))
        diff = ImageChops.difference(self.actions.image, expected).getbbox()
        self.assertIsNotNone(diff)
        self.assertLessEqual(diff[0], 60)
        self.assertLessEqual(diff[1], 40)
        self.assertLessEqual(diff[2], 160)
        self.assertLessEqual(diff[3], 110)

    def test_enter_finishes(self):
        self._drag(100, 120, 500, 420)
        self.canvas.focus_force()
        self.root.update()
        self.canvas.event_generate("<Return>")
        self.assertEqual(self.actions.hits, 1)

    def test_escape_cancels(self):
        self._drag(100, 120, 500, 420)
        self.canvas.focus_force()
        self.root.update()
        self.canvas.event_generate("<Escape>")
        self.assertTrue(self.overlay._closed)


if __name__ == "__main__":
    unittest.main()
