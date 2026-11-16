import unittest

from wesnap.win32 import acquire_single_instance


class SingleInstanceTest(unittest.TestCase):
    def test_second_acquire_fails(self):
        self.assertTrue(acquire_single_instance("Local\\WeSnapTest"))
        self.assertFalse(acquire_single_instance("Local\\WeSnapTest"))


if __name__ == "__main__":
    unittest.main()
