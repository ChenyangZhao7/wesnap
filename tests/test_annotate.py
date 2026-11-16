import unittest

from PIL import Image

from wesnap.annotate import (ArrowAnn, DEFAULT_COLOR, EllipseAnn, MosaicAnn,
                             PenAnn, RectAnn, TextAnn, UndoStack, render)
from wesnap.geometry import Rect


def white(w=200, h=120):
    return Image.new("RGB", (w, h), "white")


class AnnotateTest(unittest.TestCase):
    def test_rect_and_clipping(self):
        img = render(white(), [RectAnn(Rect(0, 0, 60, 60))])
        self.assertEqual(img.getpixel((0, 0)), DEFAULT_COLOR)
        img2 = render(white(), [RectAnn(Rect(500, 500, 20, 20))])
        self.assertEqual(img2.getpixel((0, 0)), (255, 255, 255))
        img3 = render(white(), [RectAnn(Rect(-5, -5, 30, 30))])
        self.assertEqual(img3.size, (200, 120))

    def test_ellipse_center_hollow(self):
        img = render(white(), [EllipseAnn(Rect(10, 10, 80, 60))])
        self.assertEqual(img.getpixel((50, 40)), (255, 255, 255))
        self.assertEqual(img.getpixel((10, 40)), DEFAULT_COLOR)

    def test_arrow_and_pen_hit_path(self):
        img = render(white(), [ArrowAnn((10, 10), (100, 10))])
        self.assertEqual(img.getpixel((50, 10)), DEFAULT_COLOR)
        img2 = render(white(), [PenAnn([(20, 20), (30, 30), (40, 40)])])
        self.assertEqual(img2.getpixel((30, 30)), DEFAULT_COLOR)

    def test_text_renders_chinese_without_error(self):
        img = render(white(), [TextAnn(10, 10, "中文标注，测试。")])
        self.assertNotEqual(img.tobytes(), white().tobytes())

    def test_mosaic_makes_blocks_uniform(self):
        base = Image.new("RGB", (100, 100))
        for y in range(100):
            for x in range(100):
                base.putpixel((x, y), (x * 2 % 256, y * 2 % 256, 0))
        img = render(base, [MosaicAnn([(50, 50)], block=8, radius=12)])
        self.assertEqual(img.getpixel((48, 48)), img.getpixel((52, 52)))

    def test_undo_stack(self):
        s = UndoStack()
        a = RectAnn(Rect(0, 0, 5, 5))
        s.push(a)
        self.assertEqual(len(s), 1)
        self.assertIs(s.pop(), a)
        self.assertIsNone(s.pop())


if __name__ == "__main__":
    unittest.main()
