"""Floating pinned screenshot windows."""

import tkinter as tk

from PIL import Image, ImageTk

from .geometry import Rect

MIN_SCALE = 0.25
MAX_SCALE = 3.0


def pin_hit_test(width: int, height: int, x: int, y: int, handle: int = 8) -> str:
    return Rect(0, 0, width, height).hit_test(x, y, handle)


def zoom_size(width: int, height: int, factor: float,
              min_scale: float = MIN_SCALE, max_scale: float = MAX_SCALE,
              ) -> tuple[int, int]:
    scale = max(min_scale, min(max_scale, factor))
    return max(1, round(width * scale)), max(1, round(height * scale))


class PinWindow:
    def __init__(self, root: tk.Tk, image: Image.Image, on_copy, on_save_as,
                 on_close=None):
        self.root = root
        self.image = image.convert("RGB")
        self.on_copy = on_copy
        self.on_save_as = on_save_as
        self.on_close = on_close
        self._closed = False
        self._scale = 1.0
        self._mode = "inside"
        self._press = (0, 0)
        self._start_scale = 1.0
        self._start_size = (self.image.width, self.image.height)
        self._x = 0
        self._y = 0
        self._photo = None

        top = tk.Toplevel(root)
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        try:
            top.attributes("-toolwindow", True)
        except tk.TclError:
            pass
        self.top = top
        self.canvas = tk.Canvas(top, bd=0, highlightthickness=0, bg="black")
        self.canvas.pack()

        self._resize_to(1.0)
        from . import win32
        cursor = win32.get_cursor_pos()
        monitors = win32.enum_monitors()
        monitor = next((m for m in monitors if m.contains(*cursor)), monitors[0])
        width = self.image.width
        height = self.image.height
        self._x = min(max(cursor[0] - 20, monitor.x), monitor.right - width)
        self._y = min(max(cursor[1] - 20, monitor.y), monitor.bottom - height)
        self._move_to(self._x, self._y)

        self.canvas.bind("<ButtonPress-1>", self._press_event)
        self.canvas.bind("<B1-Motion>", self._drag_event)
        self.canvas.bind("<Double-Button-1>", lambda e: self.close())
        self.canvas.bind("<MouseWheel>", self._wheel_event)
        self.canvas.bind("<ButtonPress-3>", self._menu_event)
        top.bind("<Escape>", lambda e: self.close())
        top.bind("<Control-c>", lambda e: self.on_copy())
        top.bind("<Control-s>", lambda e: self.on_save_as())
        top.focus_force()

    # -- actions -----------------------------------------------------------

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.top.destroy()
        except tk.TclError:
            pass
        if self.on_close is not None:
            self.on_close()

    # -- geometry ----------------------------------------------------------

    def _move_to(self, x: int, y: int) -> None:
        self._x, self._y = x, y
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if width <= 1 or height <= 1:
            width, height = self._window_size()
        self.top.geometry(f"{width}x{height}+{x}+{y}")

    def _window_size(self) -> tuple[int, int]:
        return zoom_size(self.image.width, self.image.height, self._scale)

    def _resize_to(self, scale: float) -> None:
        scale = max(MIN_SCALE, min(MAX_SCALE, scale))
        self._scale = scale
        width, height = self._window_size()
        thumb = self.image.resize((width, height), Image.Resampling.LANCZOS)
        self._photo = ImageTk.PhotoImage(thumb, master=self.canvas)
        self.canvas.config(width=width, height=height)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._photo)
        self.top.geometry(f"{width}x{height}+{self._x}+{self._y}")

    # -- events ------------------------------------------------------------

    def _press_event(self, event) -> None:
        self._mode = pin_hit_test(self.canvas.winfo_width(),
                                  self.canvas.winfo_height(),
                                  event.x, event.y)
        self._press = (event.x_root, event.y_root)
        self._start_scale = self._scale
        self._start_size = (self.canvas.winfo_width(), self.canvas.winfo_height())

    def _drag_event(self, event) -> None:
        dx = event.x_root - self._press[0]
        dy = event.y_root - self._press[1]
        if self._mode == "inside":
            self._move_to(self._x + dx, self._y + dy)
            self._press = (event.x_root, event.y_root)
            return
        start_w, start_h = self._start_size
        if "e" in self._mode:
            new_w = start_w + dx
            scale = new_w / self.image.width
        elif "w" in self._mode:
            new_w = start_w - dx
            scale = new_w / self.image.width
        elif "s" in self._mode:
            new_h = start_h + dy
            scale = new_h / self.image.height
        else:
            new_h = start_h - dy
            scale = new_h / self.image.height
        self._resize_to(scale)

    def _wheel_event(self, event) -> None:
        step = 1.1 if event.delta > 0 else 1 / 1.1
        self._resize_to(self._scale * step)

    def _menu_event(self, event) -> None:
        menu = tk.Menu(self.top, tearoff=0)
        menu.add_command(label="复制", command=self.on_copy)
        menu.add_command(label="另存为…", command=self.on_save_as)
        menu.add_separator()
        menu.add_command(label="关闭", command=self.close)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
