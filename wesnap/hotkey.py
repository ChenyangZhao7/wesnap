"""Global hotkey parsing and (later) registration."""

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

_MOD_NAMES = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
}

_VK_NAMES = {
    "printscreen": 0x2C,
    "space": 0x20,
    "tab": 0x09,
    "enter": 0x0D,
    "insert": 0x2D,
    "delete": 0x2E,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
}


def _modifier(part: str) -> int:
    try:
        return _MOD_NAMES[part]
    except KeyError:
        raise ValueError(f"unknown modifier: {part!r}") from None


def _vk(key: str) -> int:
    if len(key) == 1 and key.isalnum():
        return ord(key.upper())
    if key.startswith("f") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        return 0x70 + int(key[1:]) - 1
    try:
        return _VK_NAMES[key]
    except KeyError:
        raise ValueError(f"unknown key: {key!r}") from None


def parse_hotkey(text: str) -> tuple[int, int]:
    parts = [part.strip().lower() for part in text.split("+") if part.strip()]
    if len(parts) < 2:
        raise ValueError("hotkey needs at least one modifier and one key")
    mods = 0
    for part in parts[:-1]:
        mods |= _modifier(part)
    if mods == 0:
        raise ValueError("hotkey needs a modifier")
    return mods, _vk(parts[-1])


def _vk_name(vk: int) -> str:
    if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
        return chr(vk)
    if 0x70 <= vk <= 0x87:
        return f"F{vk - 0x70 + 1}"
    for name, value in _VK_NAMES.items():
        if value == vk:
            return "PrintScreen" if name == "printscreen" else name.capitalize()
    return f"0x{vk:02X}"


def format_hotkey(mods: int, vk: int) -> str:
    order = ((MOD_CONTROL, "Ctrl"), (MOD_ALT, "Alt"), (MOD_SHIFT, "Shift"), (MOD_WIN, "Win"))
    parts = [name for bit, name in order if mods & bit]
    parts.append(_vk_name(vk))
    return "+".join(parts)
