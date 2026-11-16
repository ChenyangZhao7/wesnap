import unittest
from wesnap.startup import build_run_command


class StartupTest(unittest.TestCase):
    def test_build_run_command_quotes_paths(self):
        cmd = build_run_command(r"C:\Python\pythonw.exe", r"Z:\screenshot\wesnap\main.pyw")
        self.assertEqual(cmd, r'"C:\Python\pythonw.exe" "Z:\screenshot\wesnap\main.pyw"')


if __name__ == "__main__":
    unittest.main()
