"""Mapping targets <-> SetKeyMapping report type + code bytes.

Encoding follows the official app (doc/TARANTULA_PRO_PROTOCOL.md §5.7):
  controller  01 N   [id1, id2, id3]            N = 1..3 buttons pressed together
  keyboard    02 N   [modifier bits, k1, k2, k3] N = 1 + number of keys (<= 3)
  mouse       03 04  [0, 0, scroll, buttons]
  media       04 04  [0, 0, 0, bits]

Target strings: "controller:a", "controller:a+controller:b", "key:a", "key:ctrl+shift+a",
"mouse:left_click+scroll_up", "media:play". Every token may repeat the prefix.
"""
from __future__ import annotations

from .hid_keycodes import (
    CONTROLLER_BUTTON, CONTROLLER_SOURCE, KEYBOARD_USAGE, MOUSE_BUTTON, MOUSE_SCROLL,
)

# Modifier byte bit order used by the app: LCtrl, LShift, LAlt, Win, RCtrl, RShift, RAlt (+RGui).
MODIFIER_BITS = {
    "left_ctrl": 0, "ctrl": 0, "lctrl": 0, "control": 0,
    "left_shift": 1, "shift": 1, "lshift": 1,
    "left_alt": 2, "alt": 2, "lalt": 2,
    "left_gui": 3, "gui": 3, "win": 3, "super": 3, "meta": 3, "lgui": 3,
    "right_ctrl": 4, "rctrl": 4,
    "right_shift": 5, "rshift": 5,
    "right_alt": 6, "ralt": 6, "altgr": 6,
    "right_gui": 7, "rgui": 7,
}
_CANONICAL_MODIFIER = ["left_ctrl", "left_shift", "left_alt", "left_gui",
                       "right_ctrl", "right_shift", "right_alt", "right_gui"]

# Consumer-control bit order used by the app.
MEDIA_BITS = {"mute": 0, "vol_down": 1, "vol_up": 2, "mic_mute": 3,
              "play": 4, "prev": 5, "stop": 6, "next": 7}
_MEDIA_NAMES = {v: k for k, v in MEDIA_BITS.items()}

SCROLL_BOTH = 0x80

_USAGE_TO_KEY = {v: k for k, v in KEYBOARD_USAGE.items()}
_ID_TO_BUTTON = {v: k for k, v in CONTROLLER_BUTTON.items()}
_ID_TO_BUTTON.update({v: k for k, v in CONTROLLER_SOURCE.items()})
_BIT_TO_MOUSE = {v: k for k, v in MOUSE_BUTTON.items()}

_PREFIXES = {
    "controller": ("controller", "btn", "button"),
    "key": ("key", "keyboard"),
    "mouse": ("mouse",),
    "media": ("media",),
}


def _split(target: str) -> tuple[str, list[str]] | None:
    """('key', ['ctrl', 'a']) for 'key:ctrl+key:a'; None if there is no known prefix."""
    head, sep, rest = target.partition(":")
    if not sep:
        return None
    for kind, names in _PREFIXES.items():
        if head in names:
            tokens = []
            for tok in rest.split("+"):
                tok = tok.strip()
                if ":" in tok and tok.split(":", 1)[0] in names:
                    tok = tok.split(":", 1)[1].strip()
                if tok:
                    tokens.append(tok)
            return kind, tokens
    return None


def encode_target(target: str) -> tuple[bytes, bytes]:
    """(report type, 16-byte payload) for a target string. Raises ValueError."""
    target = target.lower().strip()
    parsed = _split(target)
    if parsed is None:  # bare names, as accepted before prefixes were required
        for kind, table in (("mouse", MOUSE_BUTTON), ("mouse", MOUSE_SCROLL),
                            ("key", KEYBOARD_USAGE), ("controller", CONTROLLER_BUTTON)):
            if target in table:
                parsed = (kind, [target])
                break
    if parsed is None:
        raise ValueError(f"Unknown mapping target: {target}")
    kind, tokens = parsed

    if kind == "controller":
        ids = []
        for t in tokens:
            if t in CONTROLLER_BUTTON:
                ids.append(CONTROLLER_BUTTON[t])
            elif t in CONTROLLER_SOURCE:
                ids.append(CONTROLLER_SOURCE[t])
            else:
                raise ValueError(f"Unknown controller button: {t}")
        if not 1 <= len(ids) <= 3:
            raise ValueError("A controller target takes 1 to 3 buttons")
        return bytes([0x01, len(ids)]), bytes(ids).ljust(16, b"\0")

    if kind == "key":
        mods, keys = 0, []
        for t in tokens:
            if t in MODIFIER_BITS:
                mods |= 1 << MODIFIER_BITS[t]
            elif t in KEYBOARD_USAGE:
                keys.append(KEYBOARD_USAGE[t])
            else:
                raise ValueError(f"Unknown keyboard key: {t}")
        if len(keys) > 3:
            raise ValueError("A keyboard target takes at most 3 keys plus modifiers")
        if not keys and not mods:
            raise ValueError(f"Empty keyboard target: {target}")
        return bytes([0x02, 1 + len(keys)]), bytes([mods, *keys]).ljust(16, b"\0")

    if kind == "mouse":
        bits, up, down = 0, False, False
        for t in tokens:
            if t in MOUSE_BUTTON:
                bits |= MOUSE_BUTTON[t]
            elif t == "scroll_up":
                up = True
            elif t == "scroll_down":
                down = True
            elif t == "scroll":
                up = down = True
            else:
                raise ValueError(f"Unknown mouse target: {t}")
        scroll = SCROLL_BOTH if up and down else 0x01 if up else 0xFF if down else 0
        return bytes([0x03, 0x04]), bytes([0, 0, scroll, bits]).ljust(16, b"\0")

    bits = 0  # media
    for t in tokens:
        if t not in MEDIA_BITS:
            raise ValueError(f"Unknown media key: {t}")
        bits |= 1 << MEDIA_BITS[t]
    return bytes([0x04, 0x04]), bytes([0, 0, 0, bits]).ljust(16, b"\0")


def decode_target(report: bytes, payload: bytes) -> str | None:
    """Target string for a read report type + payload, or None if not a known type."""
    kind, count = report[0], report[1]
    if kind == 0x01 and 1 <= count <= 3:
        ids = payload[:count]
        if count > 1:
            ids = bytes(i for i in ids if i)
        if not ids:
            return None
        return "+".join(f"controller:{_ID_TO_BUTTON.get(i, f'0x{i:02x}')}" for i in ids)

    if kind == 0x02 and count >= 1:
        mods = payload[0] if payload else 0
        parts = [f"key:{_CANONICAL_MODIFIER[b]}" for b in range(8) if mods >> b & 1]
        keys = [k for k in payload[1:count] if k]
        parts += [f"key:{_USAGE_TO_KEY.get(k, f'0x{k:02x}')}" for k in keys]
        return "+".join(parts) or None

    if kind == 0x03 and count == 4 and len(payload) >= 4:
        scroll, bits = payload[2], payload[3]
        parts = [f"mouse:{_BIT_TO_MOUSE.get(1 << b, f'0x{1 << b:02x}')}" for b in range(8) if bits >> b & 1]
        if scroll == SCROLL_BOTH:
            parts += ["mouse:scroll_up", "mouse:scroll_down"]
        elif scroll == 0x01:
            parts.append("mouse:scroll_up")
        elif scroll == 0xFF:
            parts.append("mouse:scroll_down")
        return "+".join(parts) or None

    if kind == 0x04 and count == 4 and len(payload) >= 4:
        parts = [f"media:{_MEDIA_NAMES[b]}" for b in range(8) if payload[3] >> b & 1]
        return "+".join(parts) or None

    return None
