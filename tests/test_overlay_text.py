import tkinter as tk
import unittest

from wesnap.capture import grab_virtual_screen
from wesnap.overlay import ScreenshotOverlay


class RecordingActions:
    def __init__(self):
        self.images = []

    def finish(self, image, rect):
        self.images.append(image)
        return False

    def save_as(self, image):
        self.images.append(image)
        return False

    def pin(self, image):
        self.images.append(image)
        return False


class OverlayTextTest(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.capture = grab_virtual_screen()
        self.actions = RecordingActions()
        self.overlay = ScreenshotOverlay(self.root, self.capture, self.actions)
        self.addCleanup(self.overlay.close)
        controller = self.overlay._controller
        controller.press(100, 100)
        controller.drag(400, 300)
        controller.release()
        self.overlay._render()

    def test_composite_commits_pending_text(self):
        self.overlay._open_text_entry(20, 20, (120, 120), self.overlay.rect)
        self.overlay._text_entry.insert(0, "中文")
        composed = self.overlay._composite()
        self.assertIsNone(self.overlay._text_entry)
        base = self.capture.image.crop((100, 100, 400, 300))
        self.assertNotEqual(composed.tobytes(), base.tobytes())

    def test_clicking_done_commits_pending_text(self):
        self.overlay._open_text_entry(20, 20, (120, 120), self.overlay.rect)
        self.overlay._text_entry.insert(0, "hello")
        done = self.overlay._toolbar["done"]
        event = type("Event", (), {
            "x": done.x - self.overlay.active.x + 2,
            "y": done.y - self.overlay.active.y + 2,
        })()
        self.overlay._on_press(event, self.overlay.active)
        self.assertIsNone(self.overlay._text_entry)
        self.assertEqual(len(self.actions.images), 1)


if __name__ == "__main__":
    unittest.main()
