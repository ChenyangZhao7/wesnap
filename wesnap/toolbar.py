"""Toolbar layout (pure geometry)."""

from .geometry import Rect

BUTTONS = ["rect", "ellipse", "arrow", "pen", "text", "mosaic",
           "undo", "longshot", "pin", "save", "done", "cancel"]

BUTTON_SIZE = 30
SPACING = 4
PADDING = 4


def layout_toolbar(selection: Rect, screen: Rect, size=(412, 38), gap=6,
                   ) -> tuple[Rect, dict[str, Rect]]:
    width, height = size
    sel = selection.normalized()
    x = max(screen.x, min(sel.x, screen.right - width))
    if sel.bottom + gap + height <= screen.bottom:
        y = sel.bottom + gap
    elif sel.y - gap - height >= screen.y:
        y = sel.y - gap - height
    else:
        x = screen.right - PADDING - width
        y = screen.bottom - PADDING - height
    bar = Rect(x, y, width, height)
    buttons = {
        name: Rect(bar.x + PADDING + index * (BUTTON_SIZE + SPACING),
                   bar.y + PADDING, BUTTON_SIZE, BUTTON_SIZE)
        for index, name in enumerate(BUTTONS)
    }
    return bar, buttons
