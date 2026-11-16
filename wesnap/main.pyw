"""Entry point for WeSnap (run with pythonw.exe, no console)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wesnap import win32  # noqa: E402
from wesnap.app import App, setup_logging  # noqa: E402


def main() -> None:
    win32.set_dpi_aware()
    if not win32.acquire_single_instance():
        return
    try:
        App().run()
    except Exception:
        setup_logging().exception("fatal error")


if __name__ == "__main__":
    main()
