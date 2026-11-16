"""Thin Win32 helpers: screen metrics, GDI capture, desktop path."""

import ctypes
import os
import winreg
from ctypes import wintypes as wt
from pathlib import Path

from .geometry import Rect

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

SRCCOPY = 0x00CC0020
CAPTUREBLT = 0x40000000
DIB_RGB_COLORS = 0
BI_RGB = 0


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wt.DWORD),
        ("biWidth", wt.LONG),
        ("biHeight", wt.LONG),
        ("biPlanes", wt.WORD),
        ("biBitCount", wt.WORD),
        ("biCompression", wt.DWORD),
        ("biSizeImage", wt.DWORD),
        ("biXPelsPerMeter", wt.LONG),
        ("biYPelsPerMeter", wt.LONG),
        ("biClrUsed", wt.DWORD),
        ("biClrImportant", wt.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wt.DWORD * 3)]


user32.GetDC.argtypes = [wt.HWND]
user32.GetDC.restype = wt.HDC
user32.ReleaseDC.argtypes = [wt.HWND, wt.HDC]
user32.ReleaseDC.restype = ctypes.c_int
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int

gdi32.CreateCompatibleDC.argtypes = [wt.HDC]
gdi32.CreateCompatibleDC.restype = wt.HDC
gdi32.CreateCompatibleBitmap.argtypes = [wt.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wt.HBITMAP
gdi32.SelectObject.argtypes = [wt.HDC, wt.HGDIOBJ]
gdi32.SelectObject.restype = wt.HGDIOBJ
gdi32.DeleteObject.argtypes = [wt.HGDIOBJ]
gdi32.DeleteObject.restype = wt.BOOL
gdi32.DeleteDC.argtypes = [wt.HDC]
gdi32.DeleteDC.restype = wt.BOOL
gdi32.BitBlt.argtypes = [wt.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                         wt.HDC, ctypes.c_int, ctypes.c_int, wt.DWORD]
gdi32.BitBlt.restype = wt.BOOL
gdi32.GetDIBits.argtypes = [wt.HDC, wt.HBITMAP, wt.UINT, wt.UINT, ctypes.c_void_p,
                            ctypes.POINTER(BITMAPINFO), wt.UINT]
gdi32.GetDIBits.restype = ctypes.c_int


def desktop_dir() -> str:
    """Resolve the user's Desktop folder, honouring redirection."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "Desktop")
        expanded = os.path.expandvars(value)
        if expanded and os.path.isdir(expanded):
            return expanded
    except OSError:
        pass
    return str(Path.home() / "Desktop")


def get_virtual_screen_rect() -> Rect:
    return Rect(
        user32.GetSystemMetrics(SM_XVIRTUALSCREEN),
        user32.GetSystemMetrics(SM_YVIRTUALSCREEN),
        user32.GetSystemMetrics(SM_CXVIRTUALSCREEN),
        user32.GetSystemMetrics(SM_CYVIRTUALSCREEN),
    )


def capture_region_bytes(rect: Rect) -> bytes:
    """Capture a physical-pixel rectangle from the screen as top-down BGRA.

    The screen DC addresses virtual-desktop coordinates, so ``rect`` is passed
    through unchanged (negative coordinates included).
    """
    if rect.w <= 0 or rect.h <= 0:
        raise ValueError("capture rect must be positive")
    screen = user32.GetDC(None)
    if not screen:
        raise OSError(ctypes.get_last_error(), "GetDC failed")
    mem = gdi32.CreateCompatibleDC(screen)
    bmp = gdi32.CreateCompatibleBitmap(screen, rect.w, rect.h)
    old = gdi32.SelectObject(mem, bmp)
    try:
        if not gdi32.BitBlt(mem, 0, 0, rect.w, rect.h, screen, rect.x, rect.y,
                            SRCCOPY | CAPTUREBLT):
            raise OSError(ctypes.get_last_error(), "BitBlt failed")
        info = BITMAPINFO()
        header = info.bmiHeader
        header.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        header.biWidth = rect.w
        header.biHeight = -rect.h
        header.biPlanes = 1
        header.biBitCount = 32
        header.biCompression = BI_RGB
        buffer = ctypes.create_string_buffer(rect.w * rect.h * 4)
        copied = gdi32.GetDIBits(mem, bmp, 0, rect.h, buffer, ctypes.byref(info),
                                 DIB_RGB_COLORS)
        if copied != rect.h:
            raise OSError(ctypes.get_last_error(), "GetDIBits failed")
        return buffer.raw
    finally:
        gdi32.SelectObject(mem, old)
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(mem)
        user32.ReleaseDC(None, screen)


kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.LPCWSTR]
kernel32.CreateMutexW.restype = wt.HANDLE
kernel32.CloseHandle.argtypes = [wt.HANDLE]
kernel32.CloseHandle.restype = wt.BOOL

ERROR_ALREADY_EXISTS = 183
_mutexes: list[int] = []

_MONITORENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HANDLE, wt.HDC,
                                      ctypes.POINTER(wt.RECT), wt.LPARAM)
user32.EnumDisplayMonitors.argtypes = [wt.HDC, ctypes.POINTER(wt.RECT),
                                       _MONITORENUMPROC, wt.LPARAM]
user32.EnumDisplayMonitors.restype = wt.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(wt.POINT)]
user32.GetCursorPos.restype = wt.BOOL


def enum_monitors() -> list[Rect]:
    rects: list[Rect] = []

    def _collect(hmonitor, hdc, lprc, data):
        r = lprc.contents
        rects.append(Rect(r.left, r.top, r.right - r.left, r.bottom - r.top))
        return True

    user32.EnumDisplayMonitors(None, None, _MONITORENUMPROC(_collect), 0)
    return rects or [get_virtual_screen_rect()]


def get_cursor_pos() -> tuple[int, int]:
    point = wt.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def get_dpi_for_window(hwnd: int) -> int:
    try:
        user32.GetDpiForWindow.argtypes = [wt.HWND]
        user32.GetDpiForWindow.restype = wt.UINT
        return int(user32.GetDpiForWindow(hwnd)) or 96
    except (AttributeError, OSError):
        return 96


def set_dpi_aware() -> None:
    """Opt the process into per-monitor DPI awareness (physical pixels)."""
    try:
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetProcessDpiAwarenessContext.restype = wt.BOOL
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        pass


def acquire_single_instance(name: str = r"Local\WeSnap") -> bool:
    handle = kernel32.CreateMutexW(None, True, name)
    if not handle:
        return False
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return False
    _mutexes.append(handle)
    return True
