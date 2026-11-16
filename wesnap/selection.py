"""Pure selection drag state machine (no Tk dependency)."""

from .geometry import HANDLE_KEYS, Rect


class SelectionController:
    """Tracks a rectangular selection built by press/drag/release input."""

    def __init__(self, bounds: Rect, handle_size: int = 8):
        self.bounds = bounds
        self.handle_size = handle_size
        self._rect: Rect | None = None
        self._mode = "none"
        self._anchor = (0, 0)
        self._origin: Rect | None = None

    @property
    def rect(self) -> Rect | None:
        return self._rect

    @property
    def mode(self) -> str:
        return self._mode

    def press(self, x: int, y: int) -> str:
        if self._rect is not None:
            hit = self._rect.hit_test(x, y, self.handle_size)
            if hit != "outside":
                self._mode = "move" if hit == "inside" else hit
                self._origin = self._rect
                self._anchor = (x, y)
                return self._mode
        self._mode = "new"
        self._anchor = (x, y)
        self._rect = Rect(x, y, 0, 0)
        return "new"

    def drag(self, x: int, y: int) -> None:
        if self._mode == "none":
            return
        px = min(max(x, self.bounds.x), self.bounds.right)
        py = min(max(y, self.bounds.y), self.bounds.bottom)
        if self._mode == "new":
            ax, ay = self._anchor
            self._rect = Rect(ax, ay, px - ax, py - ay).normalized()
        elif self._mode == "move":
            if self._origin is None:
                return
            ax, ay = self._anchor
            self._rect = self._origin.moved(px - ax, py - ay).clamp(self.bounds)
        elif self._mode in HANDLE_KEYS and self._origin is not None:
            self._rect = self._origin.resized(self._mode, px, py, self.bounds)

    def release(self) -> None:
        if self._mode == "new" and self._rect is not None:
            if self._rect.w < 4 or self._rect.h < 4:
                self._rect = None
        self._mode = "none"
        self._origin = None

    def nudge(self, dx: int, dy: int) -> None:
        if self._rect is not None:
            self._rect = self._rect.moved(dx, dy).clamp(self.bounds)

    def reset(self) -> None:
        self._rect = None
        self._mode = "none"
        self._origin = None
