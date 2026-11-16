"""Application orchestration: tray, hotkey, capture lifecycle, settings."""

import logging
import os
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

from . import startup, win32
from .capture import grab_rect, grab_virtual_screen
from .clipboard import ClipboardError, copy_image
from .hotkey import (MOD_ALT, MOD_CONTROL, MOD_SHIFT, HotkeyManager,
                     MessagePump, format_hotkey)
from .longshot import LongCaptureSession
from .overlay import ScreenshotOverlay
from .pin import PinWindow
from .settings import load_settings, next_screenshot_path, save_settings
from .tray import TrayIcon

APP_NAME = "微截"
LOG_MAX_BYTES = 1_000_000
ALT_STATE = 0x20000


def finish_plan(auto_save: bool, auto_copy: bool) -> str:
    if auto_save and auto_copy:
        return "save_copy"
    if auto_save:
        return "save"
    if auto_copy:
        return "copy"
    return "save_as"


def setup_logging() -> logging.Logger:
    base = Path(os.environ.get("APPDATA") or str(Path.home())) / "WeSnap"
    base.mkdir(parents=True, exist_ok=True)
    log_path = base / "wesnap.log"
    try:
        if log_path.exists() and log_path.stat().st_size > LOG_MAX_BYTES:
            log_path.replace(base / "wesnap.1.log")
    except OSError:
        pass
    logger = logging.getLogger("wesnap")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)
    return logger


def pythonw_path() -> str:
    executable = Path(sys.executable)
    candidate = executable.with_name("pythonw.exe")
    return str(candidate if candidate.exists() else executable)


def main_script_path() -> str:
    return str(Path(__file__).with_name("main.pyw"))


class App:
    def __init__(self):
        self.log = setup_logging()
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.report_callback_exception = self._report_exception
        self.settings = load_settings()
        self.overlay = None
        self.longshot = None
        self.pins: list[PinWindow] = []
        self._settings_window = None
        self._recording = False

        self.pump = MessagePump()
        if not self.pump.start():
            raise RuntimeError("unable to start the Win32 message pump")
        self.hotkey = HotkeyManager(self.pump, self._on_hotkey)
        self.hotkey_ok = self.hotkey.register(self.settings["hotkey"])
        icon = str(Path(__file__).with_name("wesnap.ico"))
        tooltip = f"{APP_NAME} · {self.settings['hotkey']}"
        if not self.hotkey_ok:
            tooltip = f"{APP_NAME} · 热键未生效"
        self.tray = TrayIcon(self.pump, tooltip, self._tray_menu,
                             self._tray_capture, icon_path=icon)
        self._poll()

    # -- lifecycle ---------------------------------------------------------

    def run(self) -> None:
        self.tray.show()
        if not self.tray.added:
            self.log.warning("tray icon could not be created")
            self.root.after(200, lambda: messagebox.showwarning(
                APP_NAME, "托盘图标创建失败，程序仍在运行；详情见日志。"))
        if not self.hotkey_ok:
            self.log.warning("hotkey %s could not be registered",
                             self.settings["hotkey"])
            self.root.after(300, lambda: self.open_settings(hotkey_error=True))
            self.root.after(2500, lambda: self.tray.notify(
                APP_NAME, f"无法注册热键 {self.settings['hotkey']}，请在设置中更换。"))
        self.root.mainloop()

    def quit(self) -> None:
        try:
            if self.longshot is not None:
                self.longshot.cancel()
            if self.overlay is not None:
                self.overlay.close()
            for pin in list(self.pins):
                pin.close()
            self.tray.hide()
            self.pump.stop()
        finally:
            try:
                self.root.destroy()
            except tk.TclError:
                pass

    def _poll(self) -> None:
        try:
            for callback in self.pump.drain():
                try:
                    callback()
                except Exception:
                    self.log.exception("queued callback failed")
        finally:
            try:
                self.root.after(50, self._poll)
            except tk.TclError:
                pass

    def _report_exception(self, exc, val, tb) -> None:
        self.log.error("Tk callback failed", exc_info=(exc, val, tb))
        try:
            self.tray.notify(APP_NAME, "程序出错，详情见日志")
        except Exception:
            pass

    # -- capture flow ------------------------------------------------------

    def _on_hotkey(self) -> None:
        self.trigger_capture()

    def trigger_capture(self) -> None:
        if self.overlay is not None:
            self.overlay.close()
            self._end_overlay()
            return
        if self.longshot is not None:
            self.longshot.cancel()
            return
        self._hide_pins()
        self.root.update_idletasks()
        try:
            capture = grab_virtual_screen()
        except Exception:
            self.log.exception("screen capture failed")
            self.tray.notify(APP_NAME, "抓屏失败")
            self._show_pins()
            return
        self.overlay = ScreenshotOverlay(
            self.root, capture, self,
            on_longshot=self.start_longshot,
            on_cancel=self._end_overlay)
        self.overlay.start()

    def _hide_pins(self) -> None:
        for pin in self.pins:
            try:
                pin.top.withdraw()
            except tk.TclError:
                pass

    def _show_pins(self) -> None:
        for pin in self.pins:
            try:
                pin.top.deiconify()
            except tk.TclError:
                pass

    def _end_overlay(self) -> None:
        self.overlay = None
        self._show_pins()

    # -- overlay actions ---------------------------------------------------

    def finish(self, image, rect) -> bool:
        return self.finish_capture(image, rect)

    def finish_capture(self, image, rect) -> bool:
        plan = finish_plan(self.settings["auto_save"], self.settings["auto_copy"])
        if not self._store(image, plan):
            return False
        self._end_overlay()
        return True

    def save_as(self, image) -> bool:
        directory = self.settings.get("save_dir") or win32.desktop_dir()
        path = filedialog.asksaveasfilename(
            parent=self.root, title="保存截图", initialdir=directory,
            initialfile=next_screenshot_path(directory).name,
            defaultextension=".png", filetypes=[("PNG 图片", "*.png")])
        if not path:
            return False
        try:
            image.save(path, "PNG")
        except OSError:
            self.log.exception("save-as failed: %s", path)
            self.tray.notify(APP_NAME, "保存失败")
            return False
        self.tray.notify(APP_NAME, "已保存")
        self._end_overlay()
        return True

    def pin(self, image) -> bool:
        def on_copy():
            try:
                copy_image(image)
            except ClipboardError:
                self.log.warning("pin copy failed")
                self.tray.notify(APP_NAME, "复制到剪贴板失败")

        def on_save_as():
            self._save_image_dialog(image)

        pin = PinWindow(self.root, image, on_copy, on_save_as,
                        lambda: self._remove_pin(pin))
        self.pins.append(pin)
        self.root.after(0, self._end_overlay)
        return True

    def _remove_pin(self, pin) -> None:
        if pin in self.pins:
            self.pins.remove(pin)

    def _save_image_dialog(self, image) -> None:
        directory = self.settings.get("save_dir") or win32.desktop_dir()
        path = filedialog.asksaveasfilename(
            parent=self.root, title="保存截图", initialdir=directory,
            initialfile=next_screenshot_path(directory).name,
            defaultextension=".png", filetypes=[("PNG 图片", "*.png")])
        if not path:
            return
        try:
            image.save(path, "PNG")
            self.tray.notify(APP_NAME, "已保存")
        except OSError:
            self.log.exception("pin save failed: %s", path)
            self.tray.notify(APP_NAME, "保存失败")

    # -- storage -----------------------------------------------------------

    def _save_auto(self, image) -> Path:
        directory = self.settings.get("save_dir") or win32.desktop_dir()
        try:
            path = next_screenshot_path(directory)
            image.save(path, "PNG")
            return path
        except OSError:
            fallback = win32.desktop_dir()
            if Path(directory) == Path(fallback):
                raise
            path = next_screenshot_path(fallback)
            image.save(path, "PNG")
            return path

    def _store(self, image, plan: str) -> bool:
        if plan == "save_as":
            return self.save_as(image)
        saved = None
        try:
            if plan in ("save_copy", "save"):
                saved = self._save_auto(image)
            if plan in ("save_copy", "copy"):
                try:
                    copy_image(image)
                except ClipboardError:
                    self.log.warning("clipboard copy failed")
                    if saved is None:
                        return self.save_as(image)
                    self.tray.notify(APP_NAME, "已保存，但复制到剪贴板失败")
        except OSError:
            self.log.exception("saving screenshot failed")
            self.tray.notify(APP_NAME, "保存失败，请检查保存目录")
            return False
        if saved is not None:
            self.tray.notify(APP_NAME, f"已保存 {saved.name}")
        return True

    # -- long screenshot ---------------------------------------------------

    def start_longshot(self, rect) -> None:
        self.overlay = None
        try:
            self.longshot = LongCaptureSession(
                self.root, rect, self._longshot_done, self._longshot_cancelled,
                grab=grab_rect)
            self.longshot.start()
        except Exception:
            self.log.exception("long screenshot failed to start")
            self.longshot = None
            self._show_pins()
            self.tray.notify(APP_NAME, "长截图启动失败")

    def _longshot_done(self, image) -> None:
        self.longshot = None
        plan = finish_plan(self.settings["auto_save"], self.settings["auto_copy"])
        if not self._store(image, plan):
            path = self._emergency_save(image)
            if path is not None:
                self.tray.notify(APP_NAME, f"保存未完成，长截图已存到 {path}")
            else:
                self.tray.notify(APP_NAME, "长截图保存失败")
        self._show_pins()

    def _emergency_save(self, image) -> Path | None:
        try:
            base = Path(os.environ.get("TEMP") or str(Path.home())) / "WeSnap"
            base.mkdir(parents=True, exist_ok=True)
            path = base / f"longshot_{datetime.now():%Y%m%d_%H%M%S}.png"
            image.save(path, "PNG")
            return path
        except OSError:
            self.log.exception("emergency longshot save failed")
            return None

    def _longshot_cancelled(self) -> None:
        self.longshot = None
        self._show_pins()
        self.tray.notify(APP_NAME, "长截图已取消")

    # -- tray --------------------------------------------------------------

    def _tray_capture(self) -> None:
        if not self.hotkey_ok:
            self.tray.notify(APP_NAME, "热键未生效，请先在设置中设置可用热键")
            self.open_settings(hotkey_error=True)
            return
        self.trigger_capture()

    def _tray_menu(self):
        capture = (f"截图（{self.settings['hotkey']}）" if self.hotkey_ok
                   else "截图（热键未生效）")
        start = "✓ 开机自启" if self.settings.get("start_on_login") else "开机自启"
        return [
            (capture, self._tray_capture),
            ("设置…", self.open_settings),
            (start, self._toggle_start_on_login),
            (None, None),
            ("退出", self.quit),
        ]

    def _toggle_start_on_login(self) -> None:
        enabled = not self.settings.get("start_on_login", False)
        try:
            startup.set_start_on_login(enabled, pythonw_path(), main_script_path())
        except OSError:
            self.log.exception("autostart toggle failed")
            self.tray.notify(APP_NAME, "开机自启设置失败")
            return
        self.settings["start_on_login"] = enabled
        save_settings(self.settings)
        self.tray.notify(APP_NAME, "已开启开机自启" if enabled else "已关闭开机自启")

    # -- settings window ---------------------------------------------------

    def open_settings(self, hotkey_error: bool = False) -> None:
        if self._settings_window is not None:
            try:
                self._settings_window.lift()
                self._settings_window.focus_force()
                return
            except tk.TclError:
                self._settings_window = None
        win = tk.Toplevel(self.root)
        win.title(f"{APP_NAME} 设置")
        win.attributes("-topmost", True)
        win.resizable(False, False)
        self._settings_window = win
        self._recording = False

        hotkey_var = tk.StringVar(value=self.settings["hotkey"])
        dir_var = tk.StringVar(value=self.settings.get("save_dir", ""))
        auto_save_var = tk.BooleanVar(value=self.settings.get("auto_save", True))
        auto_copy_var = tk.BooleanVar(value=self.settings.get("auto_copy", True))
        start_var = tk.BooleanVar(value=startup.is_start_on_login())

        frame = tk.Frame(win, padx=16, pady=12)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="快捷键", anchor="w").grid(row=0, column=0, sticky="w")
        hotkey_entry = tk.Entry(frame, textvariable=hotkey_var, state="readonly",
                                width=22)
        hotkey_entry.grid(row=0, column=1, sticky="we", padx=6)
        record_btn = tk.Button(frame, text="重新录制", width=10)
        record_btn.grid(row=0, column=2)

        tk.Label(frame, text="保存目录", anchor="w").grid(row=1, column=0,
                                                          sticky="w", pady=(8, 0))
        dir_entry = tk.Entry(frame, textvariable=dir_var, state="readonly", width=22)
        dir_entry.grid(row=1, column=1, sticky="we", padx=6, pady=(8, 0))
        browse_btn = tk.Button(frame, text="浏览…", width=10)
        browse_btn.grid(row=1, column=2, pady=(8, 0))

        tk.Checkbutton(frame, text="完成后自动保存", variable=auto_save_var,
                       anchor="w").grid(row=2, column=0, columnspan=3, sticky="w",
                                        pady=(8, 0))
        tk.Checkbutton(frame, text="完成后复制到剪贴板", variable=auto_copy_var,
                       anchor="w").grid(row=3, column=0, columnspan=3, sticky="w")
        tk.Checkbutton(frame, text="开机自启", variable=start_var,
                       anchor="w").grid(row=4, column=0, columnspan=3, sticky="w")

        hint = tk.Label(frame, text="点「重新录制」后按下新的组合键", fg="#777777",
                        anchor="w")
        hint.grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 0))

        buttons = tk.Frame(frame)
        buttons.grid(row=6, column=0, columnspan=3, sticky="e", pady=(12, 0))

        def start_recording():
            self._recording = True
            hint.config(text="请按下新的组合键…", fg="#c0392b")
            win.focus_force()

        def browse():
            chosen = filedialog.askdirectory(parent=win, initialdir=dir_var.get() or
                                             win32.desktop_dir())
            if chosen:
                dir_var.set(chosen)

        def cancel():
            win.destroy()
            self._settings_window = None

        def save():
            old_hotkey = self.settings["hotkey"]
            new_hotkey = hotkey_var.get()
            if new_hotkey != old_hotkey or not self.hotkey_ok:
                if not self.hotkey.register(new_hotkey):
                    self.hotkey.register(old_hotkey)
                    messagebox.showerror(
                        APP_NAME,
                        f"无法注册热键 {new_hotkey}，可能已被其他程序占用。",
                        parent=win)
                    return
                self.hotkey_ok = True
                self.settings["hotkey"] = new_hotkey
                self.tray.set_tooltip(f"{APP_NAME} · {new_hotkey}")
            self.settings["save_dir"] = dir_var.get().strip() or win32.desktop_dir()
            self.settings["auto_save"] = bool(auto_save_var.get())
            self.settings["auto_copy"] = bool(auto_copy_var.get())
            self.settings["start_on_login"] = bool(start_var.get())
            save_settings(self.settings)
            try:
                startup.set_start_on_login(bool(start_var.get()), pythonw_path(),
                                           main_script_path())
            except OSError:
                self.log.exception("autostart update failed")
                self.tray.notify(APP_NAME, "开机自启设置失败")
            self.tray.notify(APP_NAME, "设置已保存")
            win.destroy()
            self._settings_window = None

        record_btn.config(command=start_recording)
        browse_btn.config(command=browse)
        tk.Button(buttons, text="取消", width=8, command=cancel).pack(side="right",
                                                                     padx=(6, 0))
        tk.Button(buttons, text="保存", width=8, command=save).pack(side="right")

        def on_key(event):
            if not self._recording:
                return
            keysym = event.keysym
            if keysym in ("Shift_L", "Shift_R", "Control_L", "Control_R",
                          "Alt_L", "Alt_R", "Win_L", "Win_R", "Caps_Lock"):
                return
            mods = 0
            if event.state & 0x4:
                mods |= MOD_CONTROL
            if event.state & 0x1:
                mods |= MOD_SHIFT
            if event.state & ALT_STATE or event.state & 0x8:
                mods |= MOD_ALT
            vk = None
            if len(keysym) == 1 and keysym.isalnum():
                vk = ord(keysym.upper())
            elif keysym == "Print":
                vk = 0x2C
            elif keysym.startswith("F") and keysym[1:].isdigit():
                vk = 0x70 + int(keysym[1:]) - 1
            elif keysym == "space":
                vk = 0x20
            if vk is None or mods == 0:
                hint.config(text="需要至少一个修饰键（Ctrl/Alt/Shift/Win）", fg="#c0392b")
                return "break"
            hotkey_var.set(format_hotkey(mods, vk))
            self._recording = False
            hint.config(text="点「重新录制」后按下新的组合键", fg="#777777")
            return "break"

        win.bind("<KeyPress>", on_key)
        win.protocol("WM_DELETE_WINDOW", cancel)
        win.focus_force()

    # -- startup warnings --------------------------------------------------

    def report_hotkey_failure(self) -> None:
        self.tray.set_tooltip(f"{APP_NAME} · 热键未生效")
