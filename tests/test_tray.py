import logging
import time
import unittest
from unittest import mock

from wesnap.tray import TrayIcon, WM_LBUTTONUP


class FakePump:
    def __init__(self):
        self.handlers = {}
        self.posted = []
        self.hwnd = 0

    def add_handler(self, msg, handler):
        self.handlers[msg] = handler

    def post(self, fn):
        self.posted.append(fn)

    def call_on_thread(self, fn):
        fn()


class TrayTest(unittest.TestCase):
    def setUp(self):
        logging.getLogger("wesnap").addHandler(logging.NullHandler())
    def make_tray(self):
        pump = FakePump()
        tray = TrayIcon(pump, "test", lambda: [], lambda: None)
        return pump, tray

    def test_quick_double_click_fires_once(self):
        pump, tray = self.make_tray()
        tray._on_tray(0, WM_LBUTTONUP)
        tray._on_tray(0, WM_LBUTTONUP)
        self.assertEqual(len(pump.posted), 1)
        tray._last_click = time.monotonic() - 1
        tray._on_tray(0, WM_LBUTTONUP)
        self.assertEqual(len(pump.posted), 2)

    def test_show_reports_failure(self):
        pump, tray = self.make_tray()
        with mock.patch("wesnap.tray._shell_notify", return_value=False):
            tray.show()
        self.assertFalse(tray.added)

    def test_show_reports_success(self):
        pump, tray = self.make_tray()
        with mock.patch("wesnap.tray._shell_notify", return_value=True):
            tray.show()
        self.assertTrue(tray.added)


if __name__ == "__main__":
    unittest.main()
