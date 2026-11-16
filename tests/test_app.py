import unittest

from wesnap.app import finish_plan, hotkey_from_event


class FinishPlanTest(unittest.TestCase):
    def test_finish_plan_matrix(self):
        self.assertEqual(finish_plan(True, True), "save_copy")
        self.assertEqual(finish_plan(True, False), "save")
        self.assertEqual(finish_plan(False, True), "copy")
        self.assertEqual(finish_plan(False, False), "save_as")


class HotkeyRecordingTest(unittest.TestCase):
    def test_alt_letter(self):
        self.assertEqual(hotkey_from_event("a", 0x20000), "Alt+A")

    def test_ctrl_alt_letter(self):
        self.assertEqual(hotkey_from_event("a", 0x20000 | 0x4), "Ctrl+Alt+A")

    def test_requires_modifier(self):
        self.assertIsNone(hotkey_from_event("a", 0))

    def test_ignores_modifier_keys(self):
        self.assertIsNone(hotkey_from_event("Alt_L", 0x20000))


if __name__ == "__main__":
    unittest.main()
