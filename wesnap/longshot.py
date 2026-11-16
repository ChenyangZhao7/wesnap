"""Manual-scroll long screenshot session and its control panel."""

import tkinter as tk

from PIL import ImageTk

from . import win32
from .capture import grab_rect
from .geometry import Rect
from .stitcher import frames_differ, stitch

PANEL_SIZE = (260, 360)
ACCENT = "#00A0FF"
PREVIEW_MAX = (236, 280)


def place_panel(selection: Rect, panel_size: tuple[int, int], screen: Rect,
                gap: int = 8) -> Rect | None:
    pw, ph = panel_size
    sel = selection.normalized()

    x = sel.right + gap
    if x + pw <= screen.right:
        y = max(screen.y, min(sel.y, screen.bottom - ph))
        if y + ph <= screen.bottom:
            return Rect(x, y, pw, ph)

    x = sel.x - gap - pw
    if x >= screen.x:
        y = max(screen.y, min(sel.y, screen.bottom - ph))
        if y + ph <= screen.bottom:
            return Rect(x, y, pw, ph)

    y = sel.bottom + gap
    if y + ph <= screen.bottom:
        x = max(screen.x, min(sel.x, screen.right - pw))
        return Rect(x, y, pw, ph)

    y = sel.y - gap - ph
    if y >= screen.y:
        x = max(screen.x, min(sel.x, screen.right - pw))
        return Rect(x, y, pw, ph)

    return None


class LongCaptureSession:
    def __init__(self, root: tk.Tk, rect: Rect, on_finish, on_cancel,
                 grab=grab_rect, poll_ms: int = 100, max_height: int = 30000):
        self.root = root
        self.rect = rect
        self.on_finish = on_finish
        self.on_cancel = on_cancel
        self.grab = grab
        self.poll_ms = poll_ms
        self.max_height = max_height

        self.canvas = None
        self._last = None
        self._closed = False
        self._after_id = None
        self._count = 0
        self._failures = 0
        self._borders = []
        self._panel = None
        self._preview = None
        self._status = None
        self._preview_photo = None

    def start(self) -> None:
        try:
            self.canvas = self.grab(self.rect)
        except Exception:
            self.on_cancel()
            return
        self._last = self.canvas.copy()
        monitors = win32.enum_monitors()
        screen = next((m for m in monitors if m.contains(self.rect.x, self.rect.y)),
                      monitors[0])
        position = place_panel(self.rect, PANEL_SIZE, screen)
        if position is None:
            self.on_cancel()
            return
        self._make_borders(screen)
        self._make_panel(position)
        self._update_preview("已拼接 0 段")
        self._schedule()

    def finish(self) -> None:
        if self._closed:
            return
        image = self.canvas.copy()
        self._teardown()
        self.on_finish(image)

    def cancel(self) -> None:
        if self._closed:
            return
        self._teardown()
        self.on_cancel()

    def _teardown(self) -> None:
        self._closed = True
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        for widget in self._borders:
            try:
                widget.destroy()
            except tk.TclError:
                pass
        self._borders = []
        if self._panel is not None:
            try:
                self._panel.destroy()
            except tk.TclError:
                pass
            self._panel = None

    def _make_borders(self, screen: Rect) -> None:
        r = self.rect
        strips = [
            (r.x, r.y - 2, r.w, 2),
            (r.x, r.y + r.h, r.w, 2),
            (r.x - 2, r.y, 2, r.h),
            (r.x + r.w, r.y, 2, r.h),
        ]
        for x, y, w, h in strips:
            if w <= 0 or h <= 0:
                continue
            if x < screen.x or y < screen.y or x + w > screen.right or y + h > screen.bottom:
                continue
            strip = tk.Toplevel(self.root)
            strip.overrideredirect(True)
            strip.attributes("-topmost", True)
            strip.configure(bg=ACCENT)
            strip.geometry(f"{w}x{h}+{x}+{y}")
            self._borders.append(strip)

    def _make_panel(self, position: Rect) -> None:
        panel = tk.Toplevel(self.root)
        panel.overrideredirect(True)
        panel.attributes("-topmost", True)
        panel.configure(bg="#2b2b2b")
        panel.geometry(f"{position.w}x{position.h}+{position.x}+{position.y}")
        self._panel = panel
        self._preview = tk.Canvas(panel, width=position.w - 8, height=position.h - 86,
                                  bg="#1e1e1e", highlightthickness=0)
        self._preview.pack(padx=4, pady=(4, 0))
        self._status = tk.Label(panel, text="", fg="#dddddd", bg="#2b2b2b",
                                anchor="w", justify="left")
        self._status.pack(fill="x", padx=8)
        row = tk.Frame(panel, bg="#2b2b2b")
        row.pack(fill="x", pady=6)
        tk.Button(row, text="完成", width=8, command=self.finish).pack(side="left", padx=8)
        tk.Button(row, text="取消", width=8, command=self.cancel).pack(side="right", padx=8)
        panel.bind("<Escape>", lambda e: self.cancel())
        panel.bind("<Return>", lambda e: self.finish())

    def _schedule(self) -> None:
        self._after_id = self.root.after(self.poll_ms, self._tick)

    def _tick(self) -> None:
        self._after_id = None
        if self._closed:
            return
        try:
            frame = self.grab(self.rect)
        except Exception:
            self._failures += 1
            if self._failures >= 5:
                if self._status is not None:
                    self._status.config(text="画面被遮挡或屏幕已锁定", fg="#ff8a65")
                return
            self._schedule()
            return
        self._failures = 0
        if frames_differ(self._last, frame):
            result = stitch(self.canvas, frame, prev_frame=self._last,
                            max_height=self.max_height)
            self._last = frame
            if result.status in ("appended", "appended_full"):
                self.canvas = result.image
                self._count += 1
                if result.status == "appended_full":
                    self._update_preview(f"已拼接 {self._count} 段（低置信，可能重复）",
                                         "#ffd36b")
                else:
                    self._update_preview(f"已拼接 {self._count} 段")
            elif result.status == "max_height":
                self._update_preview("已达高度上限，可点完成结束", "#ff8a65")
        self._schedule()

    def _update_preview(self, text: str, color: str = "#dddddd") -> None:
        if self._preview is None or self._status is None:
            return
        thumb = self.canvas.copy()
        thumb.thumbnail(PREVIEW_MAX)
        photo = ImageTk.PhotoImage(thumb, master=self._preview)
        self._preview_photo = photo
        self._preview.delete("all")
        width = max(1, self._preview.winfo_width())
        height = max(1, self._preview.winfo_height())
        self._preview.create_image(width // 2, height // 2, image=photo,
                                   anchor="center")
        self._status.config(text=f"{text} · 高 {self.canvas.height}px", fg=color)
