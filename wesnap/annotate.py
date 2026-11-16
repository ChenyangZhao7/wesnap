"""Annotation shapes, undo stack and composite rendering."""

import math
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFont

from .geometry import Rect

DEFAULT_COLOR = (230, 67, 64)
DEFAULT_WIDTH = 2

_FONT_PATHS = (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc")


def ui_font(size: int = 14) -> ImageFont.ImageFont:
    for path in _FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


class Annotation:
    """Anything that can paint itself onto a capture crop."""

    def render(self, canvas: Image.Image) -> None:
        raise NotImplementedError

    def bounds(self) -> Rect:
        raise NotImplementedError


@dataclass
class RectAnn(Annotation):
    rect: Rect
    color: tuple[int, int, int] = DEFAULT_COLOR
    width: int = DEFAULT_WIDTH

    def render(self, canvas: Image.Image) -> None:
        r = self.rect.normalized()
        ImageDraw.Draw(canvas).rectangle(
            [r.x, r.y, max(r.x, r.right - 1), max(r.y, r.bottom - 1)],
            outline=self.color, width=self.width)

    def bounds(self) -> Rect:
        return self.rect.normalized()


@dataclass
class EllipseAnn(Annotation):
    rect: Rect
    color: tuple[int, int, int] = DEFAULT_COLOR
    width: int = DEFAULT_WIDTH

    def render(self, canvas: Image.Image) -> None:
        r = self.rect.normalized()
        ImageDraw.Draw(canvas).ellipse(
            [r.x, r.y, max(r.x, r.right - 1), max(r.y, r.bottom - 1)],
            outline=self.color, width=self.width)

    def bounds(self) -> Rect:
        return self.rect.normalized()


@dataclass
class ArrowAnn(Annotation):
    start: tuple[int, int]
    end: tuple[int, int]
    color: tuple[int, int, int] = DEFAULT_COLOR
    width: int = DEFAULT_WIDTH

    def render(self, canvas: Image.Image) -> None:
        draw = ImageDraw.Draw(canvas)
        draw.line([self.start, self.end], fill=self.color, width=self.width)
        angle = math.atan2(self.end[1] - self.start[1], self.end[0] - self.start[0])
        length = 10 + self.width * 3
        spread = 0.45
        head = [
            self.end,
            (int(self.end[0] - length * math.cos(angle - spread)),
             int(self.end[1] - length * math.sin(angle - spread))),
            (int(self.end[0] - length * math.cos(angle + spread)),
             int(self.end[1] - length * math.sin(angle + spread))),
        ]
        draw.polygon(head, fill=self.color)

    def bounds(self) -> Rect:
        return Rect(min(self.start[0], self.end[0]), min(self.start[1], self.end[1]),
                    abs(self.end[0] - self.start[0]), abs(self.end[1] - self.start[1]))


@dataclass
class PenAnn(Annotation):
    points: list[tuple[int, int]]
    color: tuple[int, int, int] = DEFAULT_COLOR
    width: int = DEFAULT_WIDTH

    def render(self, canvas: Image.Image) -> None:
        if len(self.points) < 2:
            return
        ImageDraw.Draw(canvas).line(self.points, fill=self.color, width=self.width,
                                    joint="curve")

    def bounds(self) -> Rect:
        xs = [p[0] for p in self.points] or [0]
        ys = [p[1] for p in self.points] or [0]
        return Rect(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


@dataclass
class TextAnn(Annotation):
    x: int
    y: int
    text: str
    size: int = 14
    color: tuple[int, int, int] = DEFAULT_COLOR

    def font(self):
        return ui_font(self.size)

    def render(self, canvas: Image.Image) -> None:
        ImageDraw.Draw(canvas).text((self.x, self.y), self.text, font=self.font(),
                                    fill=self.color)

    def bounds(self) -> Rect:
        left, top, right, bottom = self.font().getbbox(self.text)
        return Rect(self.x + left, self.y + top, right - left, bottom - top)


@dataclass
class MosaicAnn(Annotation):
    points: list[tuple[int, int]]
    block: int = 8
    radius: int = 10

    def render(self, canvas: Image.Image) -> None:
        draw = ImageDraw.Draw(canvas)
        width, height = canvas.size
        for px, py in self.points:
            x0 = (px - self.radius) // self.block * self.block
            y0 = (py - self.radius) // self.block * self.block
            x1 = (px + self.radius) // self.block * self.block
            y1 = (py + self.radius) // self.block * self.block
            for by in range(y0, y1 + 1, self.block):
                for bx in range(x0, x1 + 1, self.block):
                    cx = bx + self.block // 2
                    cy = by + self.block // 2
                    if (cx - px) ** 2 + (cy - py) ** 2 > self.radius ** 2:
                        continue
                    if bx < 0 or by < 0 or bx + self.block > width or by + self.block > height:
                        continue
                    color = canvas.getpixel((cx, cy))
                    draw.rectangle([bx, by, bx + self.block - 1, by + self.block - 1],
                                   fill=color)

    def bounds(self) -> Rect:
        xs = [p[0] for p in self.points] or [0]
        ys = [p[1] for p in self.points] or [0]
        return Rect(min(xs) - self.radius, min(ys) - self.radius,
                    2 * self.radius, 2 * self.radius)


class UndoStack:
    def __init__(self):
        self._items: list[Annotation] = []

    def push(self, annotation: Annotation) -> None:
        self._items.append(annotation)

    def pop(self) -> Annotation | None:
        return self._items.pop() if self._items else None

    def clear(self) -> None:
        self._items.clear()

    def items(self) -> list[Annotation]:
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)


def render(base: Image.Image, annotations: list[Annotation]) -> Image.Image:
    canvas = base.copy()
    for annotation in annotations:
        annotation.render(canvas)
    return canvas
