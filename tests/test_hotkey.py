import unittest
from wesnap.hotkey import (MOD_ALT, MOD_CONTROL, MOD_SHIFT, format_hotkey,
                           parse_hotkey)


class HotkeyParseTest(unittest.TestCase):
    def test_parse_alt_a(self):
        self.assertEqual(parse_hotkey("Alt+A"), (MOD_ALT, 0x41))

    def test_parse_combined(self):
        self.assertEqual(parse_hotkey("ctrl+shift+F5"), (MOD_CONTROL | MOD_SHIFT, 0x74))

    def test_format_roundtrip(self):
        self.assertEqual(format_hotkey(MOD_CONTROL | MOD_ALT, 0x41), "Ctrl+Alt+A")
        self.assertEqual(parse_hotkey(format_hotkey(MOD_ALT, 0x2C)), (MOD_ALT, 0x2C))

    def test_invalid_requires_modifier(self):
        with self.assertRaises(ValueError):
            parse_hotkey("A")


if __name__ == "__main__":
    unittest.main()
