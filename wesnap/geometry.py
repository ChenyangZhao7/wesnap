"""Pure geometry primitives shared by the overlay, toolbar and pin window."""

from dataclasses import dataclass

MIN_SIZE = 5
HANDLE_KEYS = ("nw", "n", "ne", "e", "se", "s", "sw", "w")


@dataclass(frozen=True)
class Rect:
    """A rectangle in physical pixels, top-left based."""

    x: int
    y: int
    w: int
    h: int

    @property
    def right(self) -> int:
        return self.x + self.w

    @property
    def bottom(self) -> int:
        return self.y + self.h

    def normalized(self) -> "Rect":
        x, y, w, h = self.x, self.y, self.w, self.h
        if w < 0:
            x += w
            w = -w
        if h < 0:
            y += h
            h = -h
        return Rect(x, y, w, h)

    def clamp(self, bounds: "Rect", min_size: int = MIN_SIZE) -> "Rect":
        w = max(min_size, min(self.w, bounds.w))
        h = max(min_size, min(self.h, bounds.h))
        x = min(max(self.x, bounds.x), bounds.right - w)
        y = min(max(self.y, bounds.y), bounds.bottom - h)
        return Rect(x, y, w, h)

    def contains(self, px: int, py: int) -> bool:
        return self.x <= px < self.right and self.y <= py < self.bottom

    def moved(self, dx: int, dy: int) -> "Rect":
        return Rect(self.x + dx, self.y + dy, self.w, self.h)

    def resized(self, handle: str, px: int, py: int, bounds: "Rect") -> "Rect":
        left, top, right, bottom = self.x, self.y, self.right, self.bottom
        if "w" in handle:
            left = right - MIN_SIZE if px > right - MIN_SIZE else px
        elif "e" in handle:
            right = left + MIN_SIZE if px < left + MIN_SIZE else px
        if "n" in handle:
            top = bottom - MIN_SIZE if py > bottom - MIN_SIZE else py
        elif "s" in handle:
            bottom = top + MIN_SIZE if py < top + MIN_SIZE else py
        return Rect(left, top, right - left, bottom - top).clamp(bounds)

    def handle_rects(self, size: int = 8) -> dict[str, "Rect"]:
        half = size // 2
        cx, cy = self.x + self.w // 2, self.y + self.h // 2
        centers = {
            "nw": (self.x, self.y),
            "n": (cx, self.y),
            "ne": (self.right, self.y),
            "e": (self.right, cy),
            "se": (self.right, self.bottom),
            "s": (cx, self.bottom),
            "sw": (self.x, self.bottom),
            "w": (self.x, cy),
        }
        return {key: Rect(x - half, y - half, size, size) for key, (x, y) in centers.items()}

    def hit_test(self, px: int, py: int, handle_size: int = 8, tolerance: int = 2) -> str:
        for key, rect in self.handle_rects(handle_size).items():
            if (rect.x - tolerance <= px <= rect.right + tolerance
                    and rect.y - tolerance <= py <= rect.bottom + tolerance):
                return key
        return "inside" if self.contains(px, py) else "outside"
