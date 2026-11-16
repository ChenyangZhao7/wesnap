import unittest

from PIL import Image, ImageGrab

from wesnap.clipboard import ClipboardError, copy_image, retry


class ClipboardTest(unittest.TestCase):
    def test_retry_recovers(self):
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise OSError("busy")
            return "ok"

        self.assertEqual(retry(flaky), "ok")
        self.assertEqual(calls["n"], 3)

    def test_retry_raises_after_attempts(self):
        def always():
            raise OSError("busy")

        with self.assertRaises(ClipboardError):
            retry(always)

    def test_copy_image_roundtrip(self):
        img = Image.new("RGB", (32, 16), (255, 0, 0))
        copy_image(img)
        back = ImageGrab.grabclipboard()
        self.assertIsInstance(back, Image.Image)
        self.assertEqual(back.size, (32, 16))


if __name__ == "__main__":
    unittest.main()
