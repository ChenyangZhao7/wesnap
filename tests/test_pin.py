import unittest

from wesnap.pin import pin_hit_test, zoom_size


class PinTest(unittest.TestCase):
    def test_hit_corners_and_edges(self):
        self.assertEqual(pin_hit_test(200, 100, 0, 0), "nw")
        self.assertEqual(pin_hit_test(200, 100, 200, 100), "se")
        self.assertEqual(pin_hit_test(200, 100, 100, 0), "n")
        self.assertEqual(pin_hit_test(200, 100, 100, 50), "inside")
        self.assertEqual(pin_hit_test(200, 100, 300, 300), "outside")

    def test_zoom_clamped(self):
        self.assertEqual(zoom_size(200, 100, 10.0), (600, 300))
        self.assertEqual(zoom_size(200, 100, 0.01), (50, 25))


if __name__ == "__main__":
    unittest.main()
