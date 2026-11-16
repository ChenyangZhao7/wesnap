import unittest

from wesnap.capture import grab_rect, grab_virtual_screen, rect_to_image_box
from wesnap.geometry import Rect


class CaptureTest(unittest.TestCase):
    def test_box_with_negative_origin(self):
        origin = Rect(-1920, 0, 4480, 1600)
        self.assertEqual(rect_to_image_box(Rect(-100, 50, 200, 100), origin),
                         (1820, 50, 2020, 150))

    def test_virtual_screen_matches_bounds(self):
        cap = grab_virtual_screen()
        self.assertEqual(cap.image.size, (cap.bounds.w, cap.bounds.h))
        self.assertEqual(cap.image.mode, "RGB")

    def test_grab_rect_size(self):
        img = grab_rect(Rect(0, 0, 64, 32))
        self.assertEqual(img.size, (64, 32))
        self.assertEqual(img.mode, "RGB")


if __name__ == "__main__":
    unittest.main()
