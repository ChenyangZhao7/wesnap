import random
import unittest

from PIL import Image

from wesnap.stitcher import common_prefix_rows, frames_differ, stitch


def tall_source(w=200, h=900):
    rng = random.Random(42)
    return Image.frombytes("RGB", (w, h), rng.randbytes(w * h * 3))


SRC = tall_source()


def frame(top, h):
    return SRC.crop((0, top, SRC.width, top + h))


class StitcherTest(unittest.TestCase):
    def test_exact_overlap_appends_only_new_rows(self):
        canvas = frame(0, 500)
        result = stitch(canvas, frame(400, 300))
        self.assertEqual(result.status, "appended")
        self.assertEqual(result.appended_rows, 200)
        self.assertEqual(result.image.size[1], 700)
        self.assertEqual(result.image.crop((0, 500, 200, 700)).tobytes(),
                         frame(500, 200).tobytes())

    def test_identical_frame_ignored(self):
        result = stitch(frame(0, 500), frame(200, 300))
        self.assertEqual(result.status, "ignored")
        self.assertEqual(result.appended_rows, 0)

    def test_scroll_up_ignored(self):
        result = stitch(frame(0, 600), frame(100, 300))
        self.assertEqual(result.status, "ignored")

    def test_sticky_header_not_duplicated(self):
        header = Image.new("RGB", (200, 40), (10, 10, 10))
        canvas = frame(0, 500).copy()
        canvas.paste(header, (0, 0))
        nxt = frame(400, 300).copy()
        nxt.paste(header, (0, 0))
        result = stitch(canvas, nxt, prev_frame=canvas)
        self.assertEqual(result.header_skipped, 40)
        self.assertEqual(result.image.size[1], 700)
        self.assertEqual(result.appended_rows, 200)

    def test_no_match_appends_full_frame_low_confidence(self):
        other = Image.new("RGB", (200, 300), (0, 0, 0))
        result = stitch(frame(0, 300), other)
        self.assertEqual(result.status, "appended_full")
        self.assertEqual(result.appended_rows, 300)

    def test_max_height_guard(self):
        result = stitch(frame(0, 500), frame(400, 300), max_height=500)
        self.assertEqual(result.status, "max_height")
        self.assertEqual(result.image.size[1], 500)

    def test_frames_differ(self):
        a = frame(0, 100)
        self.assertFalse(frames_differ(a, a.copy()))
        self.assertTrue(frames_differ(a, frame(50, 100)))

    def test_scroll_up_by_non_multiple_of_four_ignored(self):
        result = stitch(frame(0, 700), frame(101, 300))
        self.assertEqual(result.status, "ignored")

    def test_small_scroll_overlap_below_min_overlap(self):
        result = stitch(frame(0, 300), frame(290, 300))
        self.assertEqual(result.status, "appended")
        self.assertEqual(result.appended_rows, 290)
        self.assertEqual(result.image.size[1], 590)

    def test_common_prefix_rows_detects_sticky_header(self):
        header = Image.new("RGB", (200, 40), (10, 10, 10))
        prev = frame(0, 500).copy()
        prev.paste(header, (0, 0))
        cur = frame(400, 300).copy()
        cur.paste(header, (0, 0))
        self.assertEqual(common_prefix_rows(prev, cur), 40)


if __name__ == "__main__":
    unittest.main()
