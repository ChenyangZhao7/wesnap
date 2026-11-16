import unittest
from wesnap.geometry import Rect


class GeometryTest(unittest.TestCase):
    def test_normalized_reverse_drag(self):
        self.assertEqual(Rect(10, 20, -30, -40).normalized(), Rect(-20, -20, 30, 40))

    def test_handle_rects_and_hit_test(self):
        r = Rect(50, 50, 100, 100)
        self.assertEqual(set(r.handle_rects().keys()),
                         {"nw", "n", "ne", "e", "se", "s", "sw", "w"})
        self.assertEqual(r.hit_test(150, 150), "se")
        self.assertEqual(r.hit_test(100, 100), "inside")
        self.assertEqual(r.hit_test(0, 0), "outside")

    def test_resize_and_min_size(self):
        bounds = Rect(0, 0, 1000, 800)
        r = Rect(100, 100, 200, 100)
        self.assertEqual(r.resized("se", 400, 300, bounds), Rect(100, 100, 300, 200))
        self.assertEqual(r.resized("nw", 500, 500, bounds), Rect(295, 195, 5, 5))

    def test_clamp_and_move(self):
        bounds = Rect(0, 0, 1000, 800)
        r = Rect(900, 700, 200, 200)
        self.assertEqual(r.clamp(bounds), Rect(800, 600, 200, 200))
        self.assertEqual(Rect(0, 0, 10, 10).moved(5, 5), Rect(5, 5, 10, 10))

    def test_contains_edges(self):
        r = Rect(10, 10, 100, 50)
        self.assertTrue(r.contains(10, 10))
        self.assertTrue(r.contains(109, 59))
        self.assertFalse(r.contains(110, 60))


if __name__ == "__main__":
    unittest.main()
