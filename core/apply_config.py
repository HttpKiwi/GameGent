"""Push a full software config to the controller hardware."""

from __future__ import annotations

from .lighting import (
    set_hardware_state,
    set_abxy_layout,
    set_led_color,
    set_face_colors,
)
from .stick import StickConfig, KeyboardMapping, set_stick_config
from .trigger import TriggerConfig, set_trigger_config
from .gyro import GyroConfig, set_gyro_config
from .remap import apply_mapping, set_turbo
from .hid_keycodes import (
    CONTROLLER_BUTTON,
    CONTROLLER_SOURCE,
)
from .rumble import set_rumble_level


def _stick_ratio(stick: dict) -> int:
    for k in ("axis_ratio", "sensitivity", "y_sensitivity"):
        if k in stick:
            return int(stick[k])
    return 50


def _keyboard_mapping(stick: dict) -> KeyboardMapping | None:
    kbd = stick.get("keyboard")
    if not isinstance(kbd, dict):
        return None
    known = KeyboardMapping.__dataclass_fields__
    return KeyboardMapping(**{k: v for k, v in kbd.items() if k in known})


def _build_stick(stick_id: int, stick: dict | None) -> StickConfig:
    stick = stick or {}
    cfg = StickConfig(
        stick_id=stick_id,
        mode=stick.get("mode", "native"),
        axis_ratio=_stick_ratio(stick),
        invert_x=bool(stick.get("invert_x", False)),
        invert_y=bool(stick.get("invert_y", False)),
        overlap_percent=int(stick.get("overlap_percent", 50)),
        mouse_dpi=int(stick.get("mouse_dpi", stick.get("mouse_x_dpi", 50))),
        is_circle=bool(stick.get("is_circle", True)),
        deadzone_min=int(stick.get("deadzone_min", 5)),
        antideadzone_min=int(stick.get("antideadzone_min", 0)),
        deadzone_max=int(stick.get("deadzone_max", 100)),
        antideadzone_max=int(stick.get("antideadzone_max", 100)),
        curve_preset=stick.get("curve_preset", "linear"),
        curve_intensity=int(stick.get("curve_intensity", 100)),
        curve_points=stick.get("curve_points"),
    )
    if cfg.mode == "wheel":
        kbd = _keyboard_mapping(stick)
        if kbd:
            cfg.keyboard = kbd
    return cfg


def _build_trigger(trigger_id: int, trig: dict | None) -> TriggerConfig:
    trig = trig or {}
    return TriggerConfig(
        trigger_id=trigger_id,
        hair_mode=trig.get("hair_mode", "off"),
        hair_trigger_begin=trig.get("hair_trigger_begin"),
        hair_trigger_end=trig.get("hair_trigger_end"),
        deadzone_begin=int(trig.get("deadzone_begin", 0)),
        deadzone_end=int(trig.get("deadzone_end", 95)),
        antideadzone_begin=int(trig.get("antideadzone_begin", 0)),
        antideadzone_end=int(trig.get("antideadzone_end", 100)),
        curve_preset=trig.get("curve_preset", "linear"),
        curve_intensity=int(trig.get("curve_intensity", 100)),
        curve_points=trig.get("curve_points"),
    )


def _resolve_gyro_button(value) -> int:
    v = str(value).lower().strip()
    if v in CONTROLLER_SOURCE:
        return CONTROLLER_SOURCE[v]
    if v in CONTROLLER_BUTTON:
        return CONTROLLER_BUTTON[v]
    if v.startswith("0x"):
        return int(v, 16)
    return int(v, 10)


def _face_hsl(face_leds: list, index: int) -> tuple[int, int, int]:
    color = face_leds[index]
    # Stored as [byteHue 0-255, sat, light]
    hue = int(round((int(color[0]) / 255) * 360))
    return (hue, int(color[1]), int(color[2]))


# Config keys that feed each hardware section; used to push only what changed.
SECTION_KEYS = {
    "lighting": ("lighting_mode", "brightness", "lighting_speed"),
    "led": ("color_hue", "color_saturation", "color_lightness", "lighting_zone", "brightness"),
    "layout": ("layout",),
    "face_leds": ("face_leds", "bayx_leds"),
    "home_led": ("home_led",),
    "sticks": ("stick_left", "stick_right"),
    "triggers": ("trigger_left", "trigger_right"),
    "gyro": ("gyro",),
    "mappings": ("key_mappings", "turbo_settings"),
    "rumble": ("rumble_left", "rumble_right"),
}


def changed_sections(old: dict, new: dict) -> set[str]:
    return {
        name for name, keys in SECTION_KEYS.items()
        if any(old.get(k) != new.get(k) for k in keys)
    }


def _face_set(leds) -> list | None:
    """4 (hue deg, sat, value) tuples from stored [hue byte, sat, value] entries, or None."""
    leds = leds or []
    if not any(leds):
        return None
    # The UI shows unset buttons as red, so send what the user sees.
    leds = [leds[i] if i < len(leds) and leds[i] else [0, 100, 100] for i in range(4)]
    return [_face_hsl(leds, i) for i in range(4)]


def _apply_face_leds(config: dict) -> str:
    """ABXY (Xbox layout) and BAYX (Switch layout) LED sets; each written only if present."""
    wrote = False
    for name, key in (("abxy", "face_leds"), ("bayx", "bayx_leds")):
        colors = _face_set(config.get(key))
        if colors:
            set_face_colors(*colors, name=name)
            wrote = True
    return "ok" if wrote else "skipped"


def _apply_home_led(config: dict) -> str:
    home = config.get("home_led")
    if not (home and len(home) >= 3):
        return "skipped"
    hue = int(round((int(home[0]) / 255) * 360))
    set_led_color("home", hue, int(home[1]), int(home[2]))
    return "ok"


def _apply_gyro(config: dict) -> str:
    g = config.get("gyro") or {}
    if not g:
        return "skipped"
    set_gyro_config(GyroConfig(
        output_mode=g.get("output_mode", "mouse"),
        motion_mode=g.get("motion_mode", "aim"),
        axis_mode=g.get("axis_mode", "global"),
        activate_method=g.get("activate_method", "hold"),
        activate_button=_resolve_gyro_button(g.get("activate_button", "c1")),
        x_sensitivity=int(g.get("x_sensitivity", 50)),
        y_sensitivity=int(g.get("y_sensitivity", 50)),
        axis_ratio=int(g.get("axis_ratio", 50)),
        overlap_percent=int(g.get("overlap_percent", 50)),
        deadzone_min=int(g.get("deadzone_min", 0)),
        deadzone_max=int(g.get("deadzone_max", 100)),
        antideadzone_min=int(g.get("antideadzone_min", 0)),
        antideadzone_max=int(g.get("antideadzone_max", 100)),
        invert_x=bool(g.get("invert_x", False)),
        invert_y=bool(g.get("invert_y", False)),
        curve_preset=g.get("curve_preset", "linear"),
        curve_intensity=int(g.get("curve_intensity", 100)),
        curve_points=g.get("curve_points"),
        kb_up=g.get("kb_up", "key:w"),
        kb_down=g.get("kb_down", "key:s"),
        kb_left=g.get("kb_left", "key:a"),
        kb_right=g.get("kb_right", "key:d"),
    ))
    return "ok"


def _apply_rumble(config: dict) -> str:
    if "rumble_left" not in config and "rumble_right" not in config:
        return "skipped"
    left = int(config.get("rumble_left", 0))
    set_rumble_level(left, int(config.get("rumble_right", left)))
    return "ok"


def _apply_mappings(config: dict, previous: dict | None) -> str:
    """Push key mappings; with `previous`, only buttons whose mapping/turbo changed
    (buttons removed since then are unbound). Macro/combo entries are read-only here."""
    mappings = config.get("key_mappings") or {}
    turbo_settings = config.get("turbo_settings") or {}
    old_maps = (previous or {}).get("key_mappings") or {}
    old_turbo = (previous or {}).get("turbo_settings") or {}

    work = {}
    for button, target in mappings.items():
        if previous is None or old_maps.get(button) != target or old_turbo.get(button) != turbo_settings.get(button):
            work[button] = target
    if previous is not None:
        work.update({b: "reset" for b in old_maps if b not in mappings})

    ok, errors = 0, []
    for button, target in work.items():
        if target.startswith("macro:"):
            continue
        try:
            apply_mapping(button, target)
            turbo = turbo_settings.get(button)
            if isinstance(turbo, dict) and target not in ("unbind", "reset"):
                rate = int(turbo.get("rate", 10)) if turbo.get("turbo", True) else None  # None = toggle only
                set_turbo(button, turbo.get("target") or target, rate, bool(turbo.get("continuous", False)))
            ok += 1
        except Exception as e:
            errors.append(f"{button}: {e}")
    if errors:
        return f"{ok} ok; errors: {'; '.join(errors)}"
    return f"{ok} ok" if ok else "skipped"


def apply_config_to_device(config: dict, previous: dict | None = None) -> dict:
    """Apply config sections to hardware. Returns per-section status.

    With `previous` (the last applied config), only sections that differ are sent.
    """
    only = None if previous is None else changed_sections(previous, config)

    def led_color():
        panel = int(config.get("lighting_zone", 1)) == 1
        # Panel value tracks the brightness setting (as in the official app).
        value = int(config.get("brightness", 100)) if panel else int(config.get("color_lightness", 50))
        set_led_color("panel" if panel else "home",
                      int(config.get("color_hue", 0)),
                      int(config.get("color_saturation", 100)),
                      value)

    sections = {
        "lighting": lambda: set_hardware_state(config.get("lighting_mode", "static"),
                                               int(config.get("brightness", 100)),
                                               int(config.get("lighting_speed", 100))),
        "led": led_color,
        "layout": lambda: set_abxy_layout(config.get("layout", "xbox")),
        "face_leds": lambda: _apply_face_leds(config),
        "home_led": lambda: _apply_home_led(config),
        "sticks": lambda: set_stick_config(_build_stick(0, config.get("stick_left")),
                                           _build_stick(1, config.get("stick_right"))),
        "triggers": lambda: set_trigger_config(_build_trigger(0, config.get("trigger_left")),
                                               _build_trigger(1, config.get("trigger_right"))),
        "gyro": lambda: _apply_gyro(config),
        "mappings": lambda: _apply_mappings(config, previous),
        "rumble": lambda: _apply_rumble(config),
    }

    results: dict[str, str] = {}
    for name, run in sections.items():
        if only is not None and name not in only:
            continue
        try:
            results[name] = run() or "ok"
        except Exception as e:
            results[name] = str(e)
    return results
