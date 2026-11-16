import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from wesnap.settings import DEFAULTS, load_settings, next_screenshot_path, save_settings


class SettingsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "settings.json"
        self.dir = self.tmp.name

    def test_missing_file_returns_defaults(self):
        data = load_settings(self.path, default_dir=self.dir)
        self.assertEqual(data["hotkey"], "Alt+A")
        self.assertEqual(data["save_dir"], self.dir)
        self.assertTrue(data["auto_save"])
        self.assertTrue(data["auto_copy"])

    def test_corrupt_file_backs_up_and_defaults(self):
        self.path.write_text("{not json", encoding="utf-8")
        data = load_settings(self.path, default_dir=self.dir)
        self.assertEqual(data["hotkey"], "Alt+A")
        self.assertTrue((self.path.with_suffix(".json.bak")).exists())

    def test_roundtrip(self):
        data = dict(DEFAULTS, save_dir=self.dir, hotkey="Ctrl+Alt+X")
        save_settings(data, self.path)
        self.assertEqual(load_settings(self.path)["hotkey"], "Ctrl+Alt+X")

    def test_screenshot_path_uses_timestamp_and_suffix(self):
        now = datetime(2026, 11, 16, 14, 30, 12)
        first = next_screenshot_path(self.dir, now)
        self.assertEqual(first.name, "Screenshot_20261116_143012.png")
        first.write_bytes(b"x")
        self.assertEqual(next_screenshot_path(self.dir, now).name,
                         "Screenshot_20261116_143012_2.png")


if __name__ == "__main__":
    unittest.main()
