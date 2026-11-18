# WeSnap

**English** | [中文](README.zh-CN.md)

![CI](https://github.com/ChenyangZhao7/wesnap/actions/workflows/ci.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

A WeChat-style screenshot tool for Windows, built for one person's daily use: `Alt+A` to summon, drag to select and resize, annotate, pin to screen, capture long scrolling pages — then "Done" saves to the desktop and copies to the clipboard.

## Starting it

- Double-click the "微截" shortcut on the desktop, or `wesnap\微截.vbs`.
- It lives in the system tray and never opens a console. On first launch, if `Alt+A` is already taken, a settings window opens and asks for another key.
- Recreate the desktop shortcut: `python tools\install_shortcut.py`
- Regenerate the icon: `python tools\make_icon.py`

Requires Python 3.14 and Pillow 13, both already installed on this machine.

## Usage

Press `Alt+A` (configurable) to start:

- Drag to select; drag any of the 8 handles on the edges and corners to resize; drag inside the selection to move it; arrow keys nudge by 1px, `Shift+arrow` by 10px.
- Toolbar: `[Rectangle] [Ellipse] [Arrow] [Brush] [Text] [Mosaic] [Undo] | [Long screenshot] [Pin] | [Save] [✓ Done] [✕ Cancel]`.
- Click the active tool again to leave annotation mode and go back to moving the selection.
- Text: click where it goes, type, `Enter` confirms, `Esc` cancels; clicking anywhere else also commits. Chinese input methods work.
- "Done": saves to the configured folder and copies to the clipboard; if both switches are off it falls back to "Save as" so the image is not lost. `Enter`, double-clicking the selection and the "Done" button are equivalent.
- "Save": save as, without touching the clipboard.
- "Pin": sticks the screenshot to the screen; drag to move, drag an edge to resize, scroll to zoom, right-click for copy / save as / close, `Esc` or double-click to close.
- Long screenshot: select a region, click "Long screenshot", then scroll the wheel inside the selection to page through. A preview panel outside the selection updates live. "Done" saves and copies. The panel needs room outside the selection or the button stays greyed out; annotations must all be undone first; a single image is capped at 30000px.
- `Esc` or right-click cancels; `Enter` finishes; `Ctrl+Z` undoes.

Tray: left click takes a screenshot; right click offers screenshot / settings / start at login / quit.

## File locations

- Settings: `%APPDATA%\WeSnap\settings.json`
- Log: `%APPDATA%\WeSnap\wesnap.log` (rolls to `wesnap.1.log` past 1MB)
- Default folder: the desktop, named `Screenshot_yyyyMMdd_HHmmss.png`, with `_2`, `_3` appended on collisions.

## Settings

Tray → Settings: record a new hotkey, choose the save folder, toggle auto-save / auto-copy / start at login. When a hotkey conflicts it says so and keeps the window open instead of pretending it worked.

## Why there is no exe

Smart App Control is enabled on this machine and blocks every unsigned exe. The program runs Python through the signed `pythonw.exe`, so it ships as a folder plus a launcher and shortcut. Turning Smart App Control off is irreversible and unnecessary.

## Known limitations

- Cross-monitor selection is not supported: the selection stays on the monitor the cursor was on when the hotkey fired.
- Long screenshots need space outside the selection for the control panel; a single image is capped at 30000px; pages with fixed headers or sidebars may show repeated strips or misalignment (a weakness of every scroll-stitching tool).
- Annotation colour and width are fixed at WeChat red, 2px (the data model reserves fields for a palette later).

## Development

- All tests: `python -m unittest discover -s tests -v` (four real GUI event tests are skipped by default)
- GUI-level integration tests (briefly shows a full-screen overlay): `$env:WESNAP_GUI_TESTS='1'; python -m unittest tests.test_screenshot_flow -v`
- Design doc: `docs/superpowers/specs/2026-11-16-wesnap-design.md`
- Implementation plan: `docs/superpowers/plans/2026-11-16-wesnap.md`
- The only third-party dependency is Pillow; the entire UI is Tk + ctypes.

## License

MIT
