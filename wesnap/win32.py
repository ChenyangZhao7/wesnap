"""Thin Win32 helpers. Expanded as features land."""

import os
import winreg
from pathlib import Path


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
