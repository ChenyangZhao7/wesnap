"""Full-screen selection overlay with annotations and a floating toolbar."""

import time
import tkinter as tk

from PIL import ImageEnhance, ImageTk

from . import win32
from .annotate import (ArrowAnn, EllipseAnn, MosaicAnn, PenAnn, RectAnn,
                       TextAnn, UndoStack, arrow_head, render)
from .capture import Capture, rect_to_image_box
from .geometry import Rect
from .icons import draw_icon
from .longshot import PANEL_SIZE, place_panel
from .selection import SelectionController
from .toolbar import layout_toolbar

TOOL_BUTTONS = {"rect", "ellipse", "arrow", "pen", "text", "mosaic"}
TEXT_POINT_SIZE = 14
ACCENT = "#00A0FF"
TOOLBAR_BG = "#2b2b2b"
HANDLE_FILL = "#ffffff"


def _hex(color: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % color


def badge_text(selection: Rect) -> str:
    return f"{selection.w} × {selection.h}  ({selection.x}, {selection.y})"


class ScreenshotOverlay:
    """One borderless window per monitor; selection is limited to one monitor."""

    def __init__(self, root: tk.Tk, capture: Capture, actions,
                 on_longshot=None, on_cancel=None):
        self.root = root
        self.capture = capture
        self.actions = actions
        self.on_longshot = on_longshot
        self.on_cancel = on_cancel

        self._closed = False
        self._tool: str | None = None
        self._undo = UndoStack()
        self._draft = None
        self._drawing = False
        self._start = (0, 0)
        self._status = ""
        self._toolbar: dict[str, Rect] | None = None
        self._longshot_enabled = False
        self._text_entry: tk.Entry | None = None
        self._text_pos: tuple[int, int] | None = None
        self._photos = []
        self._last_click_time = 0.0
        self._last_click_pos = (0, 0)

        self.monitors = win32.enum_monitors()
        cursor = win32.get_cursor_pos()
        self.active = next((m for m in self.monitors if m.contains(*cursor)),
                           self.monitors[0])
        self._controller = SelectionController(self.active)

        self._views = {}
        for monitor in self.monitors:
            top = tk.Toplevel(root)
            top.overrideredirect(True)
            top.attributes("-topmost", True)
            top.geometry(f"{monitor.w}x{monitor.h}+{monitor.x}+{monitor.y}")
            top.withdraw()
            canvas = tk.Canvas(top, width=monitor.w, height=monitor.h,
                               highlightthickness=0, bd=0, bg="black",
                               cursor="crosshair")
            canvas.pack(fill="both", expand=True)
            box = rect_to_image_box(monitor, capture.bounds)
            original = capture.image.crop(box)
            dim = ImageEnhance.Brightness(original).enhance(0.45)
            photo = ImageTk.PhotoImage(dim, master=canvas)
            canvas.create_image(0, 0, anchor="nw", image=photo, tags=("dim",))
            dpi = win32.get_dpi_for_window(top.winfo_id())
            font_px = max(12, round(TEXT_POINT_SIZE * dpi / 72))
            self._views[monitor] = (top, canvas, original, photo, font_px)
            self._bind(canvas, top, monitor)

    # -- lifecycle ---------------------------------------------------------

    @property
    def rect(self) -> Rect | None:
        return self._controller.rect

    def start(self) -> None:
        for top, _canvas, _original, _photo, _font in self._views.values():
            top.deiconify()
        top, canvas = self._active_view()[:2]
        top.lift()
        canvas.focus_set()
        self._render()

    def hide(self) -> None:
        for top, _canvas, _original, _photo, _font in self._views.values():
            top.withdraw()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        entry = self._text_entry
        self._text_entry = None
        if entry is not None:
            try:
                entry.destroy()
            except tk.TclError:
                pass
        for view in list(self._views.values()):
            try:
                view[0].destroy()
            except tk.TclError:
                pass
        self._views = {}

    # -- view helpers ------------------------------------------------------

    def _active_view(self):
        return self._views[self.active]

    @property
    def _font_px(self) -> int:
        return self._active_view()[4]

    def _bind(self, canvas: tk.Canvas, top: tk.Toplevel, monitor: Rect) -> None:
        canvas.bind("<ButtonPress-1>", lambda e: self._on_press(e, monitor))
        canvas.bind("<B1-Motion>", lambda e: self._on_motion(e, monitor))
        canvas.bind("<ButtonRelease-1>", lambda e: self._on_release(e, monitor))
        canvas.bind("<Motion>", lambda e: self._on_hover(e, monitor))
        canvas.bind("<ButtonPress-3>", lambda e: self._cancel())
        top.bind("<Escape>", lambda e: self._cancel())
        top.bind("<Return>", lambda e: self._finish())
        top.bind("<Control-z>", lambda e: self._undo_last())
        for key, dx, dy in (("<Left>", -1, 0), ("<Right>", 1, 0),
                            ("<Up>", 0, -1), ("<Down>", 0, 1)):
            top.bind(key, lambda e, dx=dx, dy=dy: self._nudge(
                dx * (10 if e.state & 0x1 else 1),
                dy * (10 if e.state & 0x1 else 1)))

    # -- pointer -----------------------------------------------------------

    def _on_press(self, event, monitor: Rect) -> None:
        if self._closed or monitor != self.active:
            return
        self._commit_text_entry()
        pt = (monitor.x + event.x, monitor.y + event.y)
        selection = self._controller.rect
        if selection is not None and self._toolbar:
            for name, rect in self._toolbar.items():
                if rect.contains(*pt):
                    self._on_button(name)
                    return
        self._maybe_finish_double_click(pt, selection)
        if self._closed:
            return
        if selection is not None and self._tool in TOOL_BUTTONS:
            if selection.contains(*pt):
                if self._tool == "text":
                    self._open_text_entry(event.x, event.y, pt, selection)
                else:
                    self._begin_draw(pt, selection)
                return
        mode = self._controller.press(*pt)
        if mode == "new":
            self._undo.clear()
            self._status = ""
        self._render()

    def _maybe_finish_double_click(self, pt, selection) -> bool:
        if selection is None or self._tool is not None:
            self._last_click_time = time.monotonic()
            self._last_click_pos = pt
            return False
        now = time.monotonic()
        if (now - self._last_click_time < 0.4
                and abs(pt[0] - self._last_click_pos[0]) <= 4
                and abs(pt[1] - self._last_click_pos[1]) <= 4):
            self._last_click_time = 0.0
            self._finish()
            return True
        self._last_click_time = now
        self._last_click_pos = pt
        return False

    def _on_motion(self, event, monitor: Rect) -> None:
        if self._closed or monitor != self.active:
            return
        pt = (monitor.x + event.x, monitor.y + event.y)
        if self._drawing and self._draft is not None:
            self._update_draft(pt)
        else:
            self._controller.drag(*pt)
        self._render()

    def _on_release(self, event, monitor: Rect) -> None:
        if self._closed or monitor != self.active:
            return
        if self._drawing:
            self._finish_draft()
        else:
            self._controller.release()
        self._render()

    def _on_hover(self, event, monitor: Rect) -> None:
        if self._closed or monitor != self.active:
            return
        canvas = self._active_view()[1]
        canvas.delete("hover")
        x, y = event.x, event.y
        canvas.create_line(0, y, monitor.w, y, fill="#8a8a8a", dash=(3, 3),
                           tags=("hover",))
        canvas.create_line(x, 0, x, monitor.h, fill="#8a8a8a", dash=(3, 3),
                           tags=("hover",))
        selection = self._controller.rect
        if selection is not None:
            text = badge_text(selection)
            canvas.create_text(min(x + 14, monitor.w - 170),
                               min(y + 14, monitor.h - 24),
                               text=text, anchor="nw", fill="#ffffff",
                               font=("Microsoft YaHei", -14), tags=("hover",))

    # -- annotation drafting ----------------------------------------------

    def _begin_draw(self, pt, selection: Rect) -> None:
        rx, ry = pt[0] - selection.x, pt[1] - selection.y
        self._drawing = True
        self._start = (rx, ry)
        if self._tool in ("rect", "ellipse"):
            cls = RectAnn if self._tool == "rect" else EllipseAnn
            self._draft = cls(Rect(rx, ry, 0, 0))
        elif self._tool == "arrow":
            self._draft = ArrowAnn((rx, ry), (rx, ry))
        elif self._tool == "pen":
            self._draft = PenAnn([(rx, ry)])
        elif self._tool == "mosaic":
            self._draft = MosaicAnn([(rx, ry)])
        self._render()

    def _update_draft(self, pt) -> None:
        selection = self._controller.rect
        if selection is None:
            return
        rx = min(max(pt[0] - selection.x, 0), selection.w)
        ry = min(max(pt[1] - selection.y, 0), selection.h)
        draft = self._draft
        if isinstance(draft, (RectAnn, EllipseAnn)):
            sx, sy = self._start
            draft.rect = Rect(sx, sy, rx - sx, ry - sy).normalized()
        elif isinstance(draft, ArrowAnn):
            draft.end = (rx, ry)
        elif isinstance(draft, (PenAnn, MosaicAnn)):
            if draft.points[-1] != (rx, ry):
                draft.points.append((rx, ry))

    def _finish_draft(self) -> None:
        draft = self._draft
        self._draft = None
        self._drawing = False
        if draft is None:
            return
        keep = True
        if isinstance(draft, (RectAnn, EllipseAnn)):
            keep = draft.rect.normalized().w >= 3 and draft.rect.normalized().h >= 3
        elif isinstance(draft, ArrowAnn):
            keep = abs(draft.end[0] - draft.start[0]) + \
                abs(draft.end[1] - draft.start[1]) >= 5
        elif isinstance(draft, PenAnn):
            keep = len(draft.points) >= 2
        elif isinstance(draft, MosaicAnn):
            keep = bool(draft.points)
        if keep:
            self._undo.push(draft)

    # -- text tool ---------------------------------------------------------

    def _open_text_entry(self, cx: int, cy: int, pt, selection: Rect) -> None:
        self._commit_text_entry()
        canvas = self._active_view()[1]
        entry = tk.Entry(canvas, font=("Microsoft YaHei", -self._font_px),
                         bg="#1e1e1e", fg="#ffffff", insertbackground="#ffffff",
                         relief="solid", bd=1)
        entry.place(x=cx, y=cy, width=220, height=self._font_px + 10)
        entry.focus_set()
        entry.bind("<Return>", lambda e: self._commit_text_entry_and_break())
        entry.bind("<Escape>", lambda e: self._cancel_text_entry_and_break())
        entry.bind("<FocusOut>", lambda e: self._commit_text_entry())
        self._text_entry = entry
        self._text_pos = (pt[0] - selection.x, pt[1] - selection.y)

    def _commit_text_entry_and_break(self):
        self._commit_text_entry()
        return "break"

    def _cancel_text_entry_and_break(self):
        self._cancel_text_entry()
        return "break"

    def _commit_text_entry(self) -> None:
        entry = self._text_entry
        if entry is None:
            return
        text = entry.get().strip()
        pos = self._text_pos
        self._text_entry = None
        self._text_pos = None
        try:
            entry.destroy()
        except tk.TclError:
            pass
        if text and pos is not None:
            self._undo.push(TextAnn(pos[0], pos[1], text, size=self._font_px))
        self._render()

    def _cancel_text_entry(self) -> None:
        entry = self._text_entry
        self._text_entry = None
        self._text_pos = None
        if entry is not None:
            try:
                entry.destroy()
            except tk.TclError:
                pass
        self._render()

    # -- actions -----------------------------------------------------------

    def _on_button(self, name: str) -> None:
        if name in TOOL_BUTTONS:
            self._tool = None if self._tool == name else name
            self._status = ""
        elif name == "undo":
            self._undo.pop()
            self._status = ""
        elif name == "longshot":
            if self._undo.items():
                self._status = "长截图不支持标注，请先撤销全部标注"
            elif self.on_longshot is None:
                self._status = "长截图不可用"
            elif place_panel(self._controller.rect, PANEL_SIZE, self.active) is None:
                self._status = "选区太大，长截图需要选区外有放控制面板的空间"
            else:
                selection = self._controller.rect
                self.close()
                self.on_longshot(selection)
                return
        elif name == "pin":
            if self.actions.pin(self._composite()):
                self.close()
                return
        elif name == "save":
            if self.actions.save_as(self._composite()):
                self.close()
                return
        elif name == "done":
            self._finish()
            return
        elif name == "cancel":
            self._cancel()
            return
        self._render()

    def _finish(self) -> None:
        selection = self._controller.rect
        if selection is None:
            return
        if self.actions.finish(self._composite(), selection):
            self.close()

    def _cancel(self) -> None:
        if self._closed:
            return
        self.close()
        if self.on_cancel is not None:
            self.on_cancel()

    def _undo_last(self) -> None:
        if self._text_entry is not None:
            return
        self._undo.pop()
        self._render()

    def _nudge(self, dx: int, dy: int) -> None:
        if self._closed or self._text_entry is not None:
            return
        self._controller.nudge(dx, dy)
        self._render()

    def _composite(self):
        self._commit_text_entry()
        selection = self._controller.rect
        box = rect_to_image_box(selection, self.capture.bounds)
        return render(self.capture.image.crop(box), self._undo.items())

    # -- rendering ---------------------------------------------------------

    def _render(self) -> None:
        if self._closed:
            return
        for monitor, (top, canvas, _original, _photo, _font) in self._views.items():
            canvas.delete("sel")
            if monitor != self.active:
                canvas.create_text(monitor.w // 2, monitor.h // 2,
                                   text="请在光标所在屏幕框选",
                                   fill="#bbbbbb",
                                   font=("Microsoft YaHei", -18),
                                   tags=("sel",))
        selection = self._controller.rect
        if selection is None:
            self._toolbar = None
            return
        self._render_active(selection)

    def _render_active(self, selection: Rect) -> None:
        _top, canvas, original, _photo, font_px = self._active_view()
        sx = selection.x - self.active.x
        sy = selection.y - self.active.y
        crop = original.crop((sx, sy, sx + selection.w, sy + selection.h))
        reveal = ImageTk.PhotoImage(crop, master=canvas)
        self._photos = [reveal]
        canvas.create_image(sx, sy, anchor="nw", image=reveal, tags=("sel",))
        canvas.create_rectangle(sx, sy, sx + selection.w - 1, sy + selection.h - 1,
                                outline=ACCENT, width=2, tags=("sel",))
        for handle in selection.handle_rects().values():
            hx, hy = handle.x - self.active.x, handle.y - self.active.y
            canvas.create_rectangle(hx, hy, hx + handle.w, hy + handle.h,
                                    fill=HANDLE_FILL, outline=ACCENT,
                                    tags=("sel",))
        for annotation in self._undo.items():
            self._draw_annotation(canvas, annotation, sx, sy)
        if self._draft is not None:
            self._draw_annotation(canvas, self._draft, sx, sy)
        bar, buttons = layout_toolbar(selection, self.active)
        self._toolbar = buttons
        bx, by = bar.x - self.active.x, bar.y - self.active.y
        canvas.create_rectangle(bx, by, bx + bar.w, by + bar.h,
                                fill=TOOLBAR_BG, outline="#555555",
                                tags=("sel",))
        has_annotations = bool(self._undo.items())
        panel_ok = place_panel(selection, PANEL_SIZE, self.active) is not None
        self._longshot_enabled = bool(not has_annotations and
                                      self.on_longshot is not None and panel_ok)
        for name, rect in buttons.items():
            rx, ry = rect.x - self.active.x, rect.y - self.active.y
            selected = name == self._tool
            enabled = self._longshot_enabled if name == "longshot" else True
            if selected:
                fill = "#3a6ea5"
            else:
                fill = TOOLBAR_BG
            canvas.create_rectangle(rx, ry, rx + rect.w, ry + rect.h,
                                    fill=fill, outline="", tags=("sel",))
            draw_icon(canvas, name, Rect(rx, ry, rect.w, rect.h),
                      color="#dddddd" if enabled else "#666666")
        if self._status:
            ty = by - 10 if by > 30 else by + bar.h + 24
            canvas.create_text(bx + 4, ty, text=self._status, anchor="sw",
                               fill="#ffd36b",
                               font=("Microsoft YaHei", -14), tags=("sel",))

    def _draw_annotation(self, canvas, annotation, ox: int, oy: int) -> None:
        if isinstance(annotation, (RectAnn, EllipseAnn)):
            r = annotation.rect.normalized()
            maker = canvas.create_rectangle if isinstance(annotation, RectAnn) \
                else canvas.create_oval
            maker(ox + r.x, oy + r.y, ox + r.x + r.w, oy + r.y + r.h,
                  outline=_hex(annotation.color), width=annotation.width,
                  tags=("sel",))
        elif isinstance(annotation, ArrowAnn):
            canvas.create_line(ox + annotation.start[0], oy + annotation.start[1],
                               ox + annotation.end[0], oy + annotation.end[1],
                               fill=_hex(annotation.color), width=annotation.width,
                               tags=("sel",))
            head = arrow_head(annotation.start, annotation.end, annotation.width)
            canvas.create_polygon(
                [value for point in head for value in (ox + point[0], oy + point[1])],
                fill=_hex(annotation.color),
                outline=_hex(annotation.color), tags=("sel",))
        elif isinstance(annotation, PenAnn):
            if len(annotation.points) >= 2:
                coords = []
                for px, py in annotation.points:
                    coords.extend((ox + px, oy + py))
                canvas.create_line(*coords, fill=_hex(annotation.color),
                                   width=annotation.width, tags=("sel",))
        elif isinstance(annotation, TextAnn):
            canvas.create_text(ox + annotation.x, oy + annotation.y,
                               text=annotation.text, anchor="nw",
                               fill=_hex(annotation.color),
                               font=("Microsoft YaHei", -annotation.size),
                               tags=("sel",))
        elif isinstance(annotation, MosaicAnn):
            for px, py in annotation.points:
                canvas.create_rectangle(ox + px - annotation.radius,
                                        oy + py - annotation.radius,
                                        ox + px + annotation.radius,
                                        oy + py + annotation.radius,
                                        fill="#777777", stipple="gray50",
                                        outline="", tags=("sel",))
