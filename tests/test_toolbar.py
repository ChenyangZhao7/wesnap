import unittest

from wesnap.geometry import Rect
from wesnap.toolbar import BUTTONS, layout_toolbar

SCREEN = Rect(0, 0, 1000, 800)


class ToolbarTest(unittest.TestCase):
    def test_below_when_room(self):
        bar, buttons = layout_toolbar(Rect(100, 100, 200, 150), SCREEN)
        self.assertEqual(bar.y, 256)
        self.assertEqual(len(buttons), len(BUTTONS))
        self.assertEqual(list(buttons), BUTTONS)

    def test_above_when_near_bottom(self):
        bar, _ = layout_toolbar(Rect(100, 600, 200, 160), SCREEN)
        self.assertEqual(bar.bottom, 594)

    def test_inside_bottom_right_when_no_room(self):
        bar, _ = layout_toolbar(Rect(0, 0, 1000, 800), SCREEN)
        self.assertEqual(bar.right, 996)
        self.assertEqual(bar.bottom, 796)

    def test_clamped_horizontally(self):
        bar, _ = layout_toolbar(Rect(900, 100, 80, 100), SCREEN)
        self.assertLessEqual(bar.right, 1000)


if __name__ == "__main__":
    unittest.main()
