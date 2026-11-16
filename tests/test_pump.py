import ctypes
import time
import unittest

from wesnap.hotkey import HotkeyManager, MessagePump


def wait_events(pump, timeout=1.0):
    end = time.time() + timeout
    seen = []
    while time.time() < end:
        seen += pump.drain()
        if seen:
            return seen
        time.sleep(0.01)
    return seen


class PumpTest(unittest.TestCase):
    def test_hotkey_roundtrip(self):
        pump = MessagePump()
        self.assertTrue(pump.start())
        self.addCleanup(pump.stop)
        hits = []
        hm = HotkeyManager(pump, lambda: hits.append(1))
        self.assertTrue(hm.register("Ctrl+Alt+Shift+F9"))
        self.addCleanup(hm.unregister)
        post = ctypes.windll.user32.PostMessageW
        post.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
        post.restype = ctypes.c_int
        post(pump.hwnd, 0x0312, 1, 0)
        events = wait_events(pump)
        for fn in events:
            fn()
        self.assertEqual(hits, [1])

    def test_invalid_hotkey_rejected(self):
        pump = MessagePump()
        self.assertTrue(pump.start())
        self.addCleanup(pump.stop)
        hm = HotkeyManager(pump, lambda: None)
        self.assertFalse(hm.register("not-a-key"))


if __name__ == "__main__":
    unittest.main()
