"""Factory defaults of the official app (GameSir Connect, T3Pro default profile), in config shape.

Resetting a section writes these values back; autosave then pushes them to the controller.
"""
from __future__ import annotations

import copy

CURVE_POINTS = [[30, 30], [50, 50], [70, 70]]


def _stick() -> dict:
    return {
        "mode": "native", "is_circle": True, "axis_ratio": 50, "overlap_percent": 40, "mouse_dpi": 50,
        "invert_x": False, "invert_y": False,
        "deadzone_min": 5, "antideadzone_min": 0, "deadzone_max": 100, "antideadzone_max": 100,
        "curve_preset": "linear", "curve_intensity": 100, "curve_points": copy.deepcopy(CURVE_POINTS),
        "keyboard": {"left": "key:a", "right": "key:d", "up": "key:w", "down": "key:s", "outline": "key:left_shift"},
    }


def _trigger() -> dict:
    return {
        "hair_mode": "off", "hair_trigger_begin": 10, "hair_trigger_end": 20,
        "deadzone_begin": 5, "deadzone_end": 95, "antideadzone_begin": 0, "antideadzone_end": 100,
        "curve_preset": "linear", "curve_intensity": 100, "curve_points": copy.deepcopy(CURVE_POINTS),
    }


def _gyro() -> dict:
    return {
        "output_mode": "off", "motion_mode": "aim", "axis_mode": "yaw", "activate_button": "b",
        "activate_method": "off", "invert_x": False, "invert_y": False,
        "x_sensitivity": 50, "y_sensitivity": 50, "axis_ratio": 50, "overlap_percent": 40,
        "deadzone_min": 0, "antideadzone_min": 0, "deadzone_max": 100, "antideadzone_max": 100,
        "curve_preset": "linear", "curve_intensity": 100, "curve_points": copy.deepcopy(CURVE_POINTS),
        "kb_up": "none", "kb_down": "none", "kb_left": "none", "kb_right": "none",
    }


def _lighting() -> dict:
    # face/home entries are [hue byte, saturation, value]; hue degrees 120/0/240/59 -> 85/0/170/41
    return {
        "lighting_mode": "colorful", "brightness": 50, "lighting_speed": 50,
        "color_hue": 240, "color_saturation": 100, "color_lightness": 50, "lighting_zone": 1,
        "home_led": [0, 0, 100],
        "face_leds": [[85, 100, 6], [0, 100, 6], [170, 100, 6], [41, 100, 6]],
        "bayx_leds": [[0, 0, 6]] * 4,
    }


SECTIONS = {
    "sticks": lambda: {"stick_left": _stick(), "stick_right": _stick()},
    "triggers": lambda: {"trigger_left": _trigger(), "trigger_right": _trigger()},
    "gyro": lambda: {"gyro": _gyro()},
    "mappings": lambda: {"key_mappings": {}, "turbo_settings": {}},
    "lighting": _lighting,
    "rumble": lambda: {"rumble_left": 75, "rumble_right": 75},
}


def factory_defaults() -> dict:
    out: dict = {"layout": "xbox"}
    for make in SECTIONS.values():
        out.update(make())
    return out


def reset_sections(config: dict, sections: list[str] | None = None) -> dict:
    """Copy of `config` with the named sections (default: all) set to factory defaults."""
    names = list(SECTIONS) if not sections or "all" in sections else sections
    unknown = [n for n in names if n not in SECTIONS]
    if unknown:
        raise ValueError(f"Unknown section(s) {unknown}; choose from {list(SECTIONS)} or 'all'")
    out = dict(config)
    for n in names:
        out.update(SECTIONS[n]())
    return out
