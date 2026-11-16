import unittest

from wesnap.app import finish_plan


class FinishPlanTest(unittest.TestCase):
    def test_finish_plan_matrix(self):
        self.assertEqual(finish_plan(True, True), "save_copy")
        self.assertEqual(finish_plan(True, False), "save")
        self.assertEqual(finish_plan(False, True), "copy")
        self.assertEqual(finish_plan(False, False), "save_as")


if __name__ == "__main__":
    unittest.main()
