import tkinter as tk
import unittest

from wesnap.capture import grab_virtual_screen
from wesnap.geometry import Rect
from wesnap.overlay import ScreenshotOverlay, badge_text


class FakeActions:
    def __init__(self):
        self.hits = 0

    def finish(self, image, rect):
        self.hits += 1
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


class OverlayBehaviorTest(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.capture = grab_virtual_screen()
        self.actions = FakeActions()
        self.overlay = ScreenshotOverlay(self.root, self.capture, self.actions,
                                         on_longshot=lambda rect: None)
        self.addCleanup(self.overlay.close)
        controller = self.overlay._controller
        controller.press(100, 100)
        controller.drag(400, 300)
        controller.release()
        self.overlay._render()

    def test_canvas_uses_crosshair(self):
        self.assertEqual(self.overlay._active_view()[1].cget("cursor"),
                         "crosshair")

    def test_badge_text_shows_coordinates(self):
        self.assertEqual(badge_text(Rect(100, 140, 300, 200)),
                         "300 × 200  (100, 140)")

    def test_longshot_enabled_for_small_selection(self):
        self.assertTrue(self.overlay._longshot_enabled)

    def test_longshot_disabled_when_no_panel_space(self):
        controller = self.overlay._controller
        bounds = self.overlay.active
        controller.reset()
        controller.press(bounds.x, bounds.y)
        controller.drag(bounds.right, bounds.bottom)
        controller.release()
        self.overlay._render()
        self.assertFalse(self.overlay._longshot_enabled)

    def test_double_click_finishes(self):
        event = type("Event", (), {"x": 150, "y": 150})()
        self.overlay._on_press(event, self.overlay.active)
        self.overlay._on_press(event, self.overlay.active)
        self.assertEqual(self.actions.hits, 1)

    def test_press_on_empty_canvas_starts_selection(self):
        self.overlay._controller.reset()
        press = type("Event", (), {"x": 20, "y": 20})()
        move = type("Event", (), {"x": 220, "y": 160})()
        self.overlay._on_press(press, self.overlay.active)
        self.overlay._on_motion(move, self.overlay.active)
        self.overlay._on_release(move, self.overlay.active)
        self.assertIsNotNone(self.overlay.rect)
        self.assertEqual(self.overlay.rect.w, 200)


if __name__ == "__main__":
    unittest.main()
