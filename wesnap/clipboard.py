"""Copy images to the Windows clipboard as CF_DIB plus PNG."""

import ctypes
import io
import struct
import time
from ctypes import wintypes as wt

from PIL import Image

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

CF_DIB = 8
GMEM_MOVEABLE = 0x0002
CF_PNG = user32.RegisterClipboardFormatW("PNG")


class ClipboardError(RuntimeError):
    pass


def retry(fn, attempts: int = 3, delay: float = 0.03):
    last: OSError | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except OSError as exc:
            last = exc
            if attempt + 1 < attempts:
                time.sleep(delay)
    raise ClipboardError("clipboard is busy") from last


user32.OpenClipboard.argtypes = [wt.HWND]
user32.OpenClipboard.restype = wt.BOOL
user32.EmptyClipboard.restype = wt.BOOL
user32.CloseClipboard.restype = wt.BOOL
user32.SetClipboardData.argtypes = [wt.UINT, wt.HANDLE]
user32.SetClipboardData.restype = wt.HANDLE
user32.RegisterClipboardFormatW.argtypes = [wt.LPCWSTR]
user32.RegisterClipboardFormatW.restype = wt.UINT

kernel32.GlobalAlloc.argtypes = [wt.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wt.HGLOBAL
kernel32.GlobalLock.argtypes = [wt.HGLOBAL]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [wt.HGLOBAL]
kernel32.GlobalUnlock.restype = wt.BOOL
kernel32.GlobalFree.argtypes = [wt.HGLOBAL]
kernel32.GlobalFree.restype = wt.HGLOBAL


def _dib_bytes(image: Image.Image) -> bytes:
    width, height = image.size
    stride = width * 4
    top_down = image.tobytes("raw", "BGRX")
    bottom_up = bytearray(stride * height)
    for y in range(height):
        src = (height - 1 - y) * stride
        bottom_up[y * stride:(y + 1) * stride] = top_down[src:src + stride]
    header = struct.pack("<IiiHHIIiiII", 40, width, height, 1, 32, 0,
                         stride * height, 0, 0, 0, 0)
    return header + bytes(bottom_up)


def _png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def _set_clipboard(format_id: int, payload: bytes) -> None:
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(payload))
    if not handle:
        raise OSError(ctypes.get_last_error(), "GlobalAlloc failed")
    pointer = kernel32.GlobalLock(handle)
    if not pointer:
        kernel32.GlobalFree(handle)
        raise OSError(ctypes.get_last_error(), "GlobalLock failed")
    ctypes.memmove(pointer, payload, len(payload))
    kernel32.GlobalUnlock(handle)
    if not user32.SetClipboardData(format_id, handle):
        kernel32.GlobalFree(handle)
        raise OSError(ctypes.get_last_error(), "SetClipboardData failed")


def copy_image(image: Image.Image) -> None:
    if image.mode != "RGB":
        image = image.convert("RGB")
    dib = _dib_bytes(image)
    png = _png_bytes(image)

    def _copy() -> None:
        if not user32.OpenClipboard(None):
            raise OSError(ctypes.get_last_error(), "OpenClipboard failed")
        try:
            if not user32.EmptyClipboard():
                raise OSError(ctypes.get_last_error(), "EmptyClipboard failed")
            _set_clipboard(CF_DIB, dib)
            _set_clipboard(CF_PNG, png)
        finally:
            user32.CloseClipboard()

    retry(_copy)
