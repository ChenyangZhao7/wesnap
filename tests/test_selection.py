import unittest
from wesnap.geometry import Rect
from wesnap.selection import SelectionController

BOUNDS = Rect(0, 0, 1000, 800)


class SelectionTest(unittest.TestCase):
    def test_drag_creates_rect(self):
        c = SelectionController(BOUNDS)
        self.assertEqual(c.press(100, 100), "new")
        c.drag(300, 250)
        c.release()
        self.assertEqual(c.rect, Rect(100, 100, 200, 150))

    def test_reverse_drag_normalizes(self):
        c = SelectionController(BOUNDS)
        c.press(300, 250)
        c.drag(100, 100)
        c.release()
        self.assertEqual(c.rect, Rect(100, 100, 200, 150))

    def test_click_without_drag_clears(self):
        c = SelectionController(BOUNDS)
        c.press(100, 100)
        c.release()
        self.assertIsNone(c.rect)

    def test_move_and_resize(self):
        c = SelectionController(BOUNDS)
        c.press(100, 100)
        c.drag(300, 250)
        c.release()
        self.assertEqual(c.press(150, 150), "move")
        c.drag(200, 200)
        c.release()
        self.assertEqual(c.rect, Rect(150, 150, 200, 150))
        self.assertEqual(c.press(350, 300), "se")
        c.drag(400, 350)
        c.release()
        self.assertEqual(c.rect, Rect(150, 150, 250, 200))

    def test_clamped_to_bounds_and_nudge(self):
        c = SelectionController(BOUNDS)
        c.press(900, 700)
        c.drag(2000, 2000)
        c.release()
        self.assertEqual(c.rect, Rect(900, 700, 100, 100))
        c.nudge(500, 500)
        self.assertEqual(c.rect, Rect(900, 700, 100, 100))


if __name__ == "__main__":
    unittest.main()
