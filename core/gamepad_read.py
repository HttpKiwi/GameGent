# core/gamepad_read.py — read live gamepad state from Linux joystick API
"""Prefer the real Xbox/GameSir pad over GameSir mouse/keyboard passthrough nodes."""

from __future__ import annotations

import glob
import os
import struct
import threading
from typing import Any

JS_EVENT_BUTTON = 0x01
JS_EVENT_AXIS = 0x02
JS_EVENT_INIT = 0x80

# Linux xpad button order for "Generic X-Box pad"
LINUX_BUTTONS = {
    0: "a",
    1: "b",
    2: "x",
    3: "y",
    4: "lb",
    5: "rb",
    6: "back",
    7: "start",
    8: "screenshot",
    9: "l3",
    10: "r3",
}

_SKIP_NAME_PARTS = ("mouse", "keyboard", "passthrough")
_PREFER_NAME_PARTS = ("x-box", "xbox", "gamepad", "game sir", "gamesir", "controller")

_lock = threading.Lock()
_fd: int | None = None
_path: str | None = None
_name: str | None = None
_axes: dict[int, float] = {}
_buttons: dict[int, int] = {}


def _js_name(js_path: str) -> str:
    base = os.path.basename(js_path)
    name_path = f"/sys/class/input/{base}/device/name"
    try:
        with open(name_path, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return base


def find_gamepad_js() -> tuple[str, str] | None:
    """Return (path, name) for the best joystick device, or None."""
    candidates: list[tuple[int, str, str]] = []
    for path in sorted(glob.glob("/dev/input/js*")):
        name = _js_name(path)
        lower = name.lower()
        if any(part in lower for part in _SKIP_NAME_PARTS):
            continue
        score = 0
        if any(part in lower for part in _PREFER_NAME_PARTS):
            score += 10
        if "generic x-box" in lower or "xbox" in lower:
            score += 5
        candidates.append((score, path, name))

    if not candidates:
        return None
    candidates.sort(key=lambda row: (-row[0], row[1]))
    _, path, name = candidates[0]
    return path, name


def _close_device() -> None:
    global _fd, _path, _name
    if _fd is not None:
        try:
            os.close(_fd)
        except OSError:
            pass
    _fd = None
    _path = None
    _name = None
    _axes.clear()
    _buttons.clear()


def _ensure_device() -> bool:
    """Open the selected joystick once; its INIT events provide full state."""
    global _fd, _path, _name
    if _fd is not None:
        return True

    found = find_gamepad_js()
    if not found:
        return False
    path, name = found
    try:
        _fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except OSError:
        _close_device()
        return False
    _path = path
    _name = name
    return True


def _drain_pending_events() -> bool:
    """Drain currently queued deltas without sleeping or reopening the device."""
    if _fd is None:
        return False
    while True:
        try:
            data = os.read(_fd, 8)
        except BlockingIOError:
            return True
        except OSError:
            _close_device()
            return False
        if len(data) < 8:
            _close_device()
            return False

        _t, value, typ, number = struct.unpack("IhBB", data)
        typ &= ~JS_EVENT_INIT
        if typ == JS_EVENT_AXIS:
            _axes[number] = max(-1.0, min(1.0, value / 32767.0))
        elif typ == JS_EVENT_BUTTON:
            _buttons[number] = 1 if value else 0


def _normalize_trigger(value: float) -> float:
    # Linux xpad ABS_Z / ABS_RZ are bipolar: -1.0 at rest → +1.0 fully pressed.
    # Always remap; switching to raw value past 0 caused a midpoint jump.
    return max(0.0, min(1.0, (value + 1.0) / 2.0))


def _hat_to_dpad(x: float, y: float) -> list[str]:
    pressed: list[str] = []
    if x < -0.5:
        pressed.append("dpad_left")
    if x > 0.5:
        pressed.append("dpad_right")
    if y < -0.5:
        pressed.append("dpad_up")
    if y > 0.5:
        pressed.append("dpad_down")
    return pressed


def read_gamepad_state() -> dict[str, Any]:
    """Read current gamepad state for the UI live tester."""
    with _lock:
        if not _ensure_device() or not _drain_pending_events():
            return {
                "connected": False,
                "id": None,
                "pressed": [],
                "leftStick": {"x": 0, "y": 0},
                "rightStick": {"x": 0, "y": 0},
                "lt": 0,
                "rt": 0,
                "axes": [],
                "buttons": [],
            }

        path = _path
        name = _name
        axes = dict(_axes)
        buttons = dict(_buttons)

    # Linux xpad: LX LY LT RX RY RT HATX HATY
    left = {"x": float(axes.get(0, 0.0)), "y": float(axes.get(1, 0.0))}
    right = {"x": float(axes.get(3, 0.0)), "y": float(axes.get(4, 0.0))}
    lt = _normalize_trigger(float(axes.get(2, -1.0)))
    rt = _normalize_trigger(float(axes.get(5, -1.0)))

    pressed: list[str] = []
    for idx, value in buttons.items():
        if value and idx in LINUX_BUTTONS:
            pressed.append(LINUX_BUTTONS[idx])
    pressed.extend(_hat_to_dpad(float(axes.get(6, 0.0)), float(axes.get(7, 0.0))))
    if lt > 0.5:
        pressed.append("lt")
    if rt > 0.5:
        pressed.append("rt")

    seen: set[str] = set()
    ordered: list[str] = []
    for name_id in pressed:
        if name_id not in seen:
            seen.add(name_id)
            ordered.append(name_id)

    max_axis = max(axes.keys(), default=-1)
    axis_list = [float(axes.get(i, 0.0)) for i in range(max_axis + 1)]
    max_btn = max(buttons.keys(), default=-1)
    button_list = [float(buttons.get(i, 0)) for i in range(max_btn + 1)]

    return {
        "connected": True,
        "id": name,
        "path": path,
        "pressed": ordered,
        "leftStick": left,
        "rightStick": right,
        "lt": lt,
        "rt": rt,
        "axes": axis_list,
        "buttons": button_list,
        "layout": "linux-xpad",
    }
