import tkinter as tk
import unittest

from wesnap.capture import grab_virtual_screen
from wesnap.overlay import ScreenshotOverlay


class FakeActions:
    def finish(self, image, rect):
        return True

    def save_as(self, image):
        return False

    def pin(self, image):
        return False


class OverlaySmokeTest(unittest.TestCase):
    def test_overlay_constructs_and_closes(self):
        root = tk.Tk()
        root.withdraw()
        self.addCleanup(root.destroy)
        cap = grab_virtual_screen()
        overlay = ScreenshotOverlay(root, cap, FakeActions())
        root.update()
        self.assertIsNone(overlay.rect)
        overlay.close()
        root.update()


if __name__ == "__main__":
    unittest.main()
