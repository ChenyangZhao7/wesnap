"""Screen capture built on the GDI helpers in :mod:`wesnap.win32`."""

from dataclasses import dataclass

from PIL import Image

from . import win32
from .geometry import Rect


@dataclass
class Capture:
    image: Image.Image
    bounds: Rect


def _decode(data: bytes, width: int, height: int) -> Image.Image:
    return Image.frombytes("RGB", (width, height), data, "raw", "BGRX", 0, 1)


def grab_virtual_screen() -> Capture:
    bounds = win32.get_virtual_screen_rect()
    return Capture(_decode(win32.capture_region_bytes(bounds), bounds.w, bounds.h), bounds)


def grab_rect(rect: Rect) -> Image.Image:
    return _decode(win32.capture_region_bytes(rect), rect.w, rect.h)


def rect_to_image_box(rect: Rect, origin: Rect) -> tuple[int, int, int, int]:
    return (rect.x - origin.x, rect.y - origin.y,
            rect.right - origin.x, rect.bottom - origin.y)
