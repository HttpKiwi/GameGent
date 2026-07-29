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
from .remap import apply_mapping, resolve_button_index, resolve_target_packet
from .hid_keycodes import (
    CONTROLLER_BUTTON,
    CONTROLLER_SOURCE,
    apply_turbo,
    turbo_enable_packet,
)
from .transport import open_device
from .rumble import set_rumble_level


def _stick_sensitivity(stick: dict) -> tuple[int, int]:
    if "x_sensitivity" in stick or "y_sensitivity" in stick:
        return int(stick.get("x_sensitivity", 50)), int(stick.get("y_sensitivity", 50))
    sens = int(stick.get("sensitivity", 50))
    return sens, 100 - sens


def _keyboard_mapping(stick: dict) -> KeyboardMapping | None:
    kbd = stick.get("keyboard")
    if not isinstance(kbd, dict):
        return None
    return KeyboardMapping(
        left=int(kbd.get("left", 0x04)),
        right=int(kbd.get("right", 0x07)),
        up=int(kbd.get("up", 0x1A)),
        down=int(kbd.get("down", 0x16)),
        overlap_left=int(kbd.get("overlap_left", 1)),
        overlap_right=int(kbd.get("overlap_right", 1)),
        overlap_up=int(kbd.get("overlap_up", 1)),
        overlap_down=int(kbd.get("overlap_down", 1)),
        left_outer=int(kbd.get("left_outer", 0)),
        right_outer=int(kbd.get("right_outer", 0)),
        up_outer=int(kbd.get("up_outer", 0)),
        down_outer=int(kbd.get("down_outer", 0)),
    )


def _build_stick(stick_id: int, stick: dict | None) -> StickConfig:
    stick = stick or {}
    x_sens, y_sens = _stick_sensitivity(stick)
    cfg = StickConfig(
        stick_id=stick_id,
        mode=stick.get("mode", "native"),
        x_sensitivity=x_sens,
        y_sensitivity=y_sens,
        overlap_percent=int(stick.get("overlap_percent", 50)),
        mouse_dpi=int(stick.get("mouse_dpi", stick.get("mouse_x_dpi", 50))),
        is_circle=bool(stick.get("is_circle", True)),
        deadzone_min=int(stick.get("deadzone_min", 5)),
        antideadzone_min=int(stick.get("antideadzone_min", 0)),
        deadzone_max=int(stick.get("deadzone_max", 100)),
        antideadzone_max=int(stick.get("antideadzone_max", 100)),
        curve_preset=stick.get("curve_preset", "linear"),
        curve_intensity=int(stick.get("curve_intensity", 50)),
    )
    if cfg.mode == "keyboard":
        kbd = _keyboard_mapping(stick)
        if kbd:
            cfg.keyboard = kbd
    return cfg


def _build_trigger(trigger_id: int, trig: dict | None) -> TriggerConfig:
    trig = trig or {}
    return TriggerConfig(
        trigger_id=trigger_id,
        hair_mode=trig.get("hair_mode", "off"),
        hair_trigger_begin=int(trig.get("hair_trigger_begin", 0)),
        hair_trigger_end=int(trig.get("hair_trigger_end", 100)),
        deadzone_begin=int(trig.get("deadzone_begin", 0)),
        deadzone_end=int(trig.get("deadzone_end", 100)),
        antideadzone_begin=int(trig.get("antideadzone_begin", 0)),
        antideadzone_end=int(trig.get("antideadzone_end", 100)),
        curve_preset=trig.get("curve_preset", "linear"),
        curve_intensity=int(trig.get("curve_intensity", 50)),
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


def _face_hsl(face_leds: list | None, index: int) -> tuple[int, int, int]:
    if not face_leds or index >= len(face_leds) or not face_leds[index]:
        return (0, 100, 50)
    color = face_leds[index]
    # Stored as [byteHue 0-255, sat, light]
    hue = int(round((int(color[0]) / 255) * 360))
    return (hue, int(color[1]), int(color[2]))


def _apply_turbo(button: str, target: str, rate: int, continuous: bool) -> None:
    import os
    import time

    btn = resolve_button_index(button)
    remap = resolve_target_packet(btn, target)
    turbo = apply_turbo(remap, rate, continuous, turbo=True)
    enable = turbo_enable_packet(btn)
    commit = bytearray(32)
    commit[0:4] = [0x07, 0x03, 0x08, 0x03]

    fd = open_device()
    try:
        os.write(fd, turbo)
        time.sleep(0.03)
        os.write(fd, enable)
        time.sleep(0.03)
        os.write(fd, commit)
        time.sleep(0.03)
    finally:
        os.close(fd)


def apply_config_to_device(config: dict) -> dict:
    """Apply working config sections to hardware. Returns per-section status."""
    results: dict[str, str] = {}

    try:
        mode = config.get("lighting_mode", "static")
        brightness = int(config.get("brightness", 100))
        speed = int(config.get("lighting_speed", 100))
        set_hardware_state(mode, brightness, speed)
        results["lighting"] = "ok"
    except Exception as e:
        results["lighting"] = str(e)

    try:
        hue = int(config.get("color_hue", 0))
        sat = int(config.get("color_saturation", 100))
        light = int(config.get("color_lightness", 50))
        zone = int(config.get("lighting_zone", 1))
        target = "panel" if zone == 1 else "home"
        set_led_color(target, hue, sat, light)
        results["led"] = "ok"
    except Exception as e:
        results["led"] = str(e)

    try:
        layout = config.get("layout", "xbox")
        set_abxy_layout(layout)
        results["layout"] = "ok"
    except Exception as e:
        results["layout"] = str(e)

    try:
        face = config.get("face_leds")
        a = _face_hsl(face, 0)
        b = _face_hsl(face, 1)
        x = _face_hsl(face, 2)
        y = _face_hsl(face, 3)
        set_face_colors(a, b, x, y)
        results["face_leds"] = "ok"
    except Exception as e:
        results["face_leds"] = str(e)

    try:
        home = config.get("home_led")
        if home and len(home) >= 3:
            hue = int(round((int(home[0]) / 255) * 360))
            set_led_color("home", hue, int(home[1]), int(home[2]))
        results["home_led"] = "ok"
    except Exception as e:
        results["home_led"] = str(e)

    try:
        left = _build_stick(0, config.get("stick_left"))
        right = _build_stick(1, config.get("stick_right"))
        set_stick_config(left, right)
        results["sticks"] = "ok"
    except Exception as e:
        results["sticks"] = str(e)

    try:
        left = _build_trigger(0, config.get("trigger_left"))
        right = _build_trigger(1, config.get("trigger_right"))
        set_trigger_config(left, right)
        results["triggers"] = "ok"
    except Exception as e:
        results["triggers"] = str(e)

    try:
        g = config.get("gyro") or {}
        if g:
            cfg = GyroConfig(
                output_mode=g.get("output_mode", "mouse"),
                motion_mode=g.get("motion_mode", "aim"),
                axis_mode=g.get("axis_mode", "global"),
                activate_method=g.get("activate_method", "hold"),
                activate_button=_resolve_gyro_button(g.get("activate_button", "c1")),
                x_sensitivity=int(g.get("x_sensitivity", 50)),
                y_sensitivity=int(g.get("y_sensitivity", 50)),
                overlap_percent=int(g.get("overlap_percent", 50)),
                mouse_dpi=int(g.get("mouse_dpi", 50)),
                deadzone_min=int(g.get("deadzone_min", 0)),
                deadzone_max=int(g.get("deadzone_max", 100)),
                antideadzone_min=int(g.get("antideadzone_min", 0)),
                antideadzone_max=int(g.get("antideadzone_max", 100)),
                invert_x=bool(g.get("invert_x", False)),
                invert_y=bool(g.get("invert_y", False)),
                curve_preset=g.get("curve_preset", "linear"),
                curve_intensity=int(g.get("curve_intensity", 50)),
                kb_up=g.get("kb_up", "key:w"),
                kb_down=g.get("kb_down", "key:s"),
                kb_left=g.get("kb_left", "key:a"),
                kb_right=g.get("kb_right", "key:d"),
            )
            set_gyro_config(cfg)
            results["gyro"] = "ok"
        else:
            results["gyro"] = "skipped"
    except Exception as e:
        results["gyro"] = str(e)

    mappings = config.get("key_mappings") or {}
    turbo_settings = config.get("turbo_settings") or {}
    map_ok = 0
    map_err = []
    if isinstance(mappings, dict):
        for button, target in mappings.items():
            try:
                apply_mapping(button, target)
                turbo = turbo_settings.get(button) if isinstance(turbo_settings, dict) else None
                if isinstance(turbo, dict):
                    _apply_turbo(
                        button,
                        turbo.get("target") or target,
                        int(turbo.get("rate", 10)),
                        bool(turbo.get("continuous", False)),
                    )
                map_ok += 1
            except Exception as e:
                map_err.append(f"{button}: {e}")
    if map_err:
        results["mappings"] = f"{map_ok} ok; errors: {'; '.join(map_err)}"
    elif mappings:
        results["mappings"] = f"{map_ok} ok"
    else:
        results["mappings"] = "skipped"

    try:
        if "rumble_left" in config or "rumble_right" in config:
            left = int(config.get("rumble_left", 0))
            right = int(config.get("rumble_right", left))
            set_rumble_level(left, right)
            results["rumble"] = "ok"
        else:
            results["rumble"] = "skipped"
    except Exception as e:
        results["rumble"] = str(e)

    return results
