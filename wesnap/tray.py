"""Tray icon built directly on Shell_NotifyIcon."""

import ctypes
import os
from ctypes import wintypes as wt

WM_TRAY = 0x8001
WM_COMMAND = 0x0111
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205
WM_NULL = 0x0000

NIM_ADD = 0
NIM_MODIFY = 1
NIM_DELETE = 2
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
NIF_INFO = 0x00000010
NIIF_INFO = 0x00000001

IDI_APPLICATION = 32512
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010

MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
TPM_RIGHTBUTTON = 0x0002
TPM_RETURNCMD = 0x0100

user32 = ctypes.WinDLL("user32", use_last_error=True)


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.DWORD),
        ("hWnd", wt.HWND),
        ("uID", wt.UINT),
        ("uFlags", wt.UINT),
        ("uCallbackMessage", wt.UINT),
        ("hIcon", wt.HICON),
        ("szTip", ctypes.c_wchar * 128),
        ("dwState", wt.DWORD),
        ("dwStateMask", wt.DWORD),
        ("szInfo", ctypes.c_wchar * 256),
        ("uVersion", wt.UINT),
        ("szInfoTitle", ctypes.c_wchar * 64),
        ("dwInfoFlags", wt.DWORD),
    ]


user32.Shell_NotifyIconW.argtypes = [wt.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
user32.Shell_NotifyIconW.restype = wt.BOOL
user32.LoadImageW.argtypes = [wt.HINSTANCE, wt.LPCWSTR, wt.UINT, ctypes.c_int,
                              ctypes.c_int, wt.UINT]
user32.LoadImageW.restype = wt.HANDLE
user32.LoadIconW.argtypes = [wt.HINSTANCE, wt.LPVOID]
user32.LoadIconW.restype = wt.HICON
user32.CreatePopupMenu.restype = wt.HMENU
user32.AppendMenuW.argtypes = [wt.HMENU, wt.UINT, ctypes.c_size_t, wt.LPCWSTR]
user32.AppendMenuW.restype = wt.BOOL
user32.TrackPopupMenu.argtypes = [wt.HMENU, wt.UINT, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_int, wt.HWND, wt.LPVOID]
user32.TrackPopupMenu.restype = ctypes.c_int
user32.DestroyMenu.argtypes = [wt.HMENU]
user32.DestroyMenu.restype = wt.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(wt.POINT)]
user32.GetCursorPos.restype = wt.BOOL
user32.SetForegroundWindow.argtypes = [wt.HWND]
user32.SetForegroundWindow.restype = wt.BOOL
user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.PostMessageW.restype = wt.BOOL


class TrayIcon:
    """A tray icon whose menu is rebuilt on every right-click."""

    def __init__(self, pump, tooltip: str, menu, on_left_click, icon_path: str | None = None):
        self.pump = pump
        self.tooltip = tooltip
        self.menu = menu
        self.on_left_click = on_left_click
        self.icon_path = icon_path
        self._icon = self._load_icon()
        self._commands: dict[int, object] = {}
        self._added = False
        pump.add_handler(WM_TRAY, self._on_tray)
        pump.add_handler(WM_COMMAND, self._on_command)

    def _load_icon(self):
        if self.icon_path and os.path.exists(self.icon_path):
            handle = user32.LoadImageW(None, self.icon_path, IMAGE_ICON, 16, 16,
                                       LR_LOADFROMFILE)
            if handle:
                return handle
        return user32.LoadIconW(None, ctypes.c_void_p(IDI_APPLICATION))

    def _data(self, flags: int) -> NOTIFYICONDATAW:
        data = NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        data.hWnd = self.pump.hwnd
        data.uID = 1
        data.uFlags = flags
        data.uCallbackMessage = WM_TRAY
        data.hIcon = self._icon
        data.szTip = self.tooltip[:127]
        return data

    def show(self) -> None:
        def _add():
            self._added = bool(user32.Shell_NotifyIconW(
                NIM_ADD, ctypes.byref(self._data(NIF_MESSAGE | NIF_ICON | NIF_TIP))))

        self.pump.call_on_thread(_add)

    def hide(self) -> None:
        def _delete():
            user32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._data(0)))
            self._added = False

        self.pump.call_on_thread(_delete)

    def set_tooltip(self, text: str) -> None:
        self.tooltip = text

        def _modify():
            if self._added:
                user32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self._data(NIF_TIP)))

        self.pump.call_on_thread(_modify)

    def notify(self, title: str, message: str) -> None:
        def _notify():
            if not self._added:
                return
            data = self._data(NIF_INFO)
            data.szInfo = message[:255]
            data.szInfoTitle = title[:63]
            data.dwInfoFlags = NIIF_INFO
            user32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(data))

        self.pump.call_on_thread(_notify)

    def _on_tray(self, wparam, lparam) -> None:
        event = lparam & 0xFFFF
        if event in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
            self.pump.post(self.on_left_click)
        elif event == WM_RBUTTONUP:
            self._show_menu()

    def _on_command(self, wparam, lparam) -> None:
        callback = self._commands.get(wparam)
        if callback is not None:
            self.pump.post(callback)

    def _show_menu(self) -> None:
        items = self.menu() or []
        menu = user32.CreatePopupMenu()
        self._commands = {}
        for index, (label, callback) in enumerate(items):
            if label is None:
                user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
            else:
                command = 1000 + index
                user32.AppendMenuW(menu, MF_STRING, command, label)
                self._commands[command] = callback
        point = wt.POINT()
        user32.GetCursorPos(ctypes.byref(point))
        user32.SetForegroundWindow(self.pump.hwnd)
        command = user32.TrackPopupMenu(
            menu, TPM_RIGHTBUTTON | TPM_RETURNCMD, point.x, point.y, 0,
            self.pump.hwnd, None)
        user32.DestroyMenu(menu)
        user32.PostMessageW(self.pump.hwnd, WM_NULL, 0, 0)
        callback = self._commands.get(command)
        if callback is not None:
            self.pump.post(callback)
