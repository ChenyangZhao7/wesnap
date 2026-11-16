import tkinter as tk
import unittest

from wesnap.geometry import Rect
from wesnap.icons import draw_icon


class IconTest(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.canvas = tk.Canvas(self.root, width=40, height=40)
        self.canvas.pack()

    def test_text_icon_fits_button(self):
        draw_icon(self.canvas, "text", Rect(4, 4, 30, 30))
        bbox = self.canvas.bbox("all")
        self.assertIsNotNone(bbox)
        left, top, right, bottom = bbox
        self.assertGreaterEqual(left, 0)
        self.assertGreaterEqual(top, 0)
        self.assertLessEqual(right, 38)
        self.assertLessEqual(bottom, 38)


if __name__ == "__main__":
    unittest.main()
