"""Global hotkey parsing, registration and a shared Win32 message pump."""

import ctypes
import logging
import queue
import threading
from ctypes import wintypes as wt

logger = logging.getLogger("wesnap")

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

_MOD_NAMES = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
}

_VK_NAMES = {
    "printscreen": 0x2C,
    "space": 0x20,
    "tab": 0x09,
    "enter": 0x0D,
    "insert": 0x2D,
    "delete": 0x2E,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
}


def _modifier(part: str) -> int:
    try:
        return _MOD_NAMES[part]
    except KeyError:
        raise ValueError(f"unknown modifier: {part!r}") from None


def _vk(key: str) -> int:
    if len(key) == 1 and key.isalnum():
        return ord(key.upper())
    if key.startswith("f") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        return 0x70 + int(key[1:]) - 1
    try:
        return _VK_NAMES[key]
    except KeyError:
        raise ValueError(f"unknown key: {key!r}") from None


def parse_hotkey(text: str) -> tuple[int, int]:
    parts = [part.strip().lower() for part in text.split("+") if part.strip()]
    if len(parts) < 2:
        raise ValueError("hotkey needs at least one modifier and one key")
    mods = 0
    for part in parts[:-1]:
        mods |= _modifier(part)
    if mods == 0:
        raise ValueError("hotkey needs a modifier")
    return mods, _vk(parts[-1])


def _vk_name(vk: int) -> str:
    if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
        return chr(vk)
    if 0x70 <= vk <= 0x87:
        return f"F{vk - 0x70 + 1}"
    for name, value in _VK_NAMES.items():
        if value == vk:
            return "PrintScreen" if name == "printscreen" else name.capitalize()
    return f"0x{vk:02X}"


def format_hotkey(mods: int, vk: int) -> str:
    order = ((MOD_CONTROL, "Ctrl"), (MOD_ALT, "Alt"), (MOD_SHIFT, "Shift"), (MOD_WIN, "Win"))
    parts = [name for bit, name in order if mods & bit]
    parts.append(_vk_name(vk))
    return "+".join(parts)


# ---------------------------------------------------------------------------
# Win32 message pump, hotkey registration and cross-thread call queue.

WM_APP = 0x8000
WM_HOTKEY = 0x0312
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
HCURSOR = getattr(wt, "HCURSOR", wt.HANDLE)
HBRUSH = getattr(wt, "HBRUSH", wt.HANDLE)
HICON = getattr(wt, "HICON", wt.HANDLE)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wt.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wt.HINSTANCE),
        ("hIcon", HICON),
        ("hCursor", HCURSOR),
        ("hbrBackground", HBRUSH),
        ("lpszMenuName", wt.LPCWSTR),
        ("lpszClassName", wt.LPCWSTR),
    ]


user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.RegisterClassW.restype = wt.ATOM
user32.UnregisterClassW.argtypes = [wt.LPCWSTR, wt.HINSTANCE]
user32.UnregisterClassW.restype = wt.BOOL
user32.CreateWindowExW.argtypes = [
    wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wt.HWND, wt.HMENU, wt.HINSTANCE, wt.LPVOID]
user32.CreateWindowExW.restype = wt.HWND
user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.DestroyWindow.argtypes = [wt.HWND]
user32.DestroyWindow.restype = wt.BOOL
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.PostQuitMessage.restype = None
user32.GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
user32.GetMessageW.restype = wt.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(wt.MSG)]
user32.TranslateMessage.restype = wt.BOOL
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wt.MSG)]
user32.DispatchMessageW.restype = LRESULT
user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.PostMessageW.restype = wt.BOOL
user32.RegisterHotKey.argtypes = [wt.HWND, ctypes.c_int, wt.UINT, wt.UINT]
user32.RegisterHotKey.restype = wt.BOOL
user32.UnregisterHotKey.argtypes = [wt.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wt.BOOL
kernel32.GetModuleHandleW.argtypes = [wt.LPCWSTR]
kernel32.GetModuleHandleW.restype = wt.HMODULE


class MessagePump:
    """A background thread owning a hidden window and its message loop."""

    def __init__(self):
        self.events: queue.Queue = queue.Queue()
        self._handlers: dict[int, object] = {}
        self._pending: list = []
        self._hwnd: int | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._wndproc = None

    @property
    def hwnd(self) -> int | None:
        return self._hwnd

    def start(self) -> bool:
        self._thread = threading.Thread(target=self._run, name="wesnap-pump", daemon=True)
        self._thread.start()
        self._ready.wait(3.0)
        return self._hwnd is not None

    def stop(self) -> None:
        if self._hwnd:
            user32.PostMessageW(self._hwnd, WM_CLOSE, 0, 0)
        if self._thread is not None:
            self._thread.join(3.0)
        self._hwnd = None

    def add_handler(self, msg: int, handler) -> None:
        self._handlers[msg] = handler

    def post(self, fn) -> None:
        self.events.put(fn)

    def call_on_thread(self, fn) -> None:
        self._pending.append(fn)
        if self._hwnd:
            user32.PostMessageW(self._hwnd, WM_APP, 0, 0)

    def drain(self) -> list:
        out = []
        while True:
            try:
                out.append(self.events.get_nowait())
            except queue.Empty:
                return out

    def _flush_pending(self) -> None:
        while self._pending:
            fn = self._pending.pop(0)
            try:
                fn()
            except Exception:
                logger.exception("pump callback failed")

    def _run(self) -> None:
        hinst = kernel32.GetModuleHandleW(None)
        class_name = f"WeSnapPump{id(self):x}"
        proc = WNDPROC(self._proc)
        self._wndproc = proc
        wc = WNDCLASSW()
        wc.lpfnWndProc = proc
        wc.hInstance = hinst
        wc.lpszClassName = class_name
        if not user32.RegisterClassW(ctypes.byref(wc)):
            self._ready.set()
            return
        hwnd = user32.CreateWindowExW(0, class_name, "WeSnapPump", 0,
                                      0, 0, 0, 0, None, None, hinst, None)
        self._hwnd = hwnd or None
        self._ready.set()
        if not hwnd:
            user32.UnregisterClassW(class_name, hinst)
            return
        msg = wt.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        user32.UnregisterClassW(class_name, hinst)

    def _proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_APP:
            self._flush_pending()
            return 0
        handler = self._handlers.get(msg)
        if handler is not None:
            try:
                handler(int(wparam), int(lparam))
            except Exception:
                logger.exception("message handler failed")
            return 0
        if msg == WM_CLOSE:
            user32.DestroyWindow(hwnd)
            return 0
        if msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


class HotkeyManager:
    """Registers one global hotkey on the pump thread."""

    HOTKEY_ID = 1

    def __init__(self, pump: MessagePump, on_hotkey):
        self.pump = pump
        self.on_hotkey = on_hotkey
        self.text: str | None = None
        pump.add_handler(WM_HOTKEY, lambda wparam, lparam: pump.post(on_hotkey))

    def register(self, text: str) -> bool:
        try:
            mods, vk = parse_hotkey(text)
        except ValueError:
            return False
        done = threading.Event()
        result = {"ok": False}

        def _do():
            try:
                self._unregister_now()
                result["ok"] = bool(user32.RegisterHotKey(
                    self.pump.hwnd, self.HOTKEY_ID, mods, vk))
            finally:
                done.set()

        self.pump.call_on_thread(_do)
        done.wait(2.0)
        if result["ok"]:
            self.text = text
        return result["ok"]

    def unregister(self) -> None:
        done = threading.Event()

        def _do():
            try:
                self._unregister_now()
            finally:
                done.set()

        self.pump.call_on_thread(_do)
        done.wait(2.0)
        self.text = None

    def _unregister_now(self) -> None:
        if self.pump.hwnd:
            user32.UnregisterHotKey(self.pump.hwnd, self.HOTKEY_ID)

