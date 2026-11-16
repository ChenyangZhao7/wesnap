import unittest

from wesnap.annotate import arrow_head


class ArrowHeadTest(unittest.TestCase):
    def test_head_is_symmetric_around_axis(self):
        head = arrow_head((0, 0), (100, 0), 2)
        self.assertEqual(head[0], (100, 0))
        self.assertEqual(head[1][1], -head[2][1])
        self.assertLess(head[1][0], 100)
        self.assertLess(head[2][0], 100)

    def test_head_follows_direction(self):
        head = arrow_head((100, 100), (0, 100), 2)
        self.assertGreater(head[1][0], 0)
        self.assertGreater(head[2][0], 0)


if __name__ == "__main__":
    unittest.main()
