"""Persistent settings and screenshot file naming."""

import json
import os
from datetime import datetime
from pathlib import Path

from .win32 import desktop_dir

DEFAULT_HOTKEY = "Alt+A"


def settings_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "WeSnap" / "settings.json"


def _defaults(default_dir: str | None = None) -> dict:
    return {
        "hotkey": DEFAULT_HOTKEY,
        "save_dir": default_dir if default_dir is not None else desktop_dir(),
        "auto_save": True,
        "auto_copy": True,
        "start_on_login": False,
    }


DEFAULTS = _defaults()


def load_settings(path: Path | str | None = None, default_dir: str | None = None) -> dict:
    path = Path(path) if path is not None else settings_path()
    defaults = _defaults(default_dir)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return defaults
    except OSError:
        return defaults
    try:
        data = json.loads(raw)
    except (ValueError, OSError):
        try:
            path.replace(path.with_suffix(".json.bak"))
        except OSError:
            pass
        return defaults
    if not isinstance(data, dict):
        try:
            path.replace(path.with_suffix(".json.bak"))
        except OSError:
            pass
        return defaults
    merged = dict(defaults)
    merged.update({key: value for key, value in data.items() if key in defaults})
    return merged


def save_settings(data: dict, path: Path | str | None = None) -> None:
    path = Path(path) if path is not None else settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def next_screenshot_path(save_dir: str, now: datetime | None = None) -> Path:
    now = now or datetime.now()
    stem = f"Screenshot_{now:%Y%m%d_%H%M%S}"
    candidate = Path(save_dir) / f"{stem}.png"
    index = 2
    while candidate.exists():
        candidate = Path(save_dir) / f"{stem}_{index}.png"
        index += 1
    return candidate
