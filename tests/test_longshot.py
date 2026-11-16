import unittest

from wesnap.geometry import Rect
from wesnap.longshot import place_panel

SCREEN = Rect(0, 0, 1000, 800)
PANEL = (200, 150)


class PlacePanelTest(unittest.TestCase):
    def test_right_side_preferred(self):
        self.assertEqual(place_panel(Rect(100, 100, 300, 300), PANEL, SCREEN),
                         Rect(408, 100, 200, 150))

    def test_left_side_when_no_right_room(self):
        self.assertEqual(place_panel(Rect(700, 100, 280, 300), PANEL, SCREEN),
                         Rect(492, 100, 200, 150))

    def test_below_then_above(self):
        self.assertEqual(place_panel(Rect(100, 100, 800, 400), PANEL, SCREEN).y, 508)
        self.assertEqual(place_panel(Rect(100, 300, 800, 460), PANEL, SCREEN).y, 142)

    def test_none_when_selection_covers_screen(self):
        self.assertIsNone(place_panel(Rect(0, 0, 1000, 800), PANEL, SCREEN))


if __name__ == "__main__":
    unittest.main()
