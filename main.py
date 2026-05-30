#!/usr/bin/env python3
"""GameGent CLI — configure GameSir Tarantula Pro controller via USB HID."""

import argparse
import sys
import time

from core import (
    set_hardware_state, LIGHTING_MODES,
    set_color, set_abxy_layout, set_led_color, set_face_button_color, set_face_colors,
    set_stick_config, StickConfig, KeyboardMapping,
    STICK_MODES, CURVE_PRESETS,
    set_rumble_level, fire_rumble,
    read_rumble_level, read_lighting, read_color, read_state,
    read_stick_targeting, read_stick_geometry,
    GyroConfig, GYRO_OUTPUT_MODES, GYRO_MOTION_MODES, GYRO_METHODS, GYRO_AXIS_MODES,
    set_gyro_config,
    apply_mapping,
    TriggerConfig, HAIR_MODES, set_trigger_config,
    turbo_packet, turbo_enable_packet,
    load_config, save_config,
)
from core.hid_keycodes import CONTROLLER_BUTTON, CONTROLLER_SOURCE


def cmd_light(args):
    mode = args.mode.lower()
    if mode not in LIGHTING_MODES:
        print(f"Unknown mode '{mode}'. Options: {list(LIGHTING_MODES.keys())}")
        sys.exit(1)
    set_hardware_state(mode, args.brightness, args.speed)
    print(f"Light: {mode} brightness={args.brightness} speed={args.speed}")


def cmd_color(args):
    set_color(args.hue)
    print(f"Color: hue={args.hue}°")


def cmd_layout(args):
    set_abxy_layout(args.layout)
    print(f"Layout: {args.layout}")


def cmd_led(args):
    set_led_color(args.target, args.hue, args.saturation, args.lightness)
    print(f"LED {args.target}: hue={args.hue}° sat={args.saturation}% light={args.lightness}%")


def cmd_face(args):
    if args.button == "all":
        set_face_colors(
            (args.a_hue, args.a_sat, args.a_light),
            (args.b_hue, args.b_sat, args.b_light),
            (args.x_hue, args.x_sat, args.x_light),
            (args.y_hue, args.y_sat, args.y_light),
        )
        print(f"Face all: A={args.a_hue}° B={args.b_hue}° X={args.x_hue}° Y={args.y_hue}°")
    else:
        set_face_button_color(args.button, args.hue, args.saturation, args.lightness)
        print(f"Face {args.button}: hue={args.hue}°")


def cmd_trigger(args):
    left = TriggerConfig(
        trigger_id=0,
        hair_mode=args.left_hair if args.left_hair is not None else args.hair,
        hair_trigger_begin=args.left_hair_begin if args.left_hair_begin is not None else args.hair_begin,
        hair_trigger_end=args.left_hair_end if args.left_hair_end is not None else args.hair_end,
        deadzone_begin=args.left_dz_begin if args.left_dz_begin is not None else args.dz_begin,
        deadzone_end=args.left_dz_end if args.left_dz_end is not None else args.dz_end,
        antideadzone_begin=args.left_anti_begin if args.left_anti_begin is not None else args.anti_begin,
        antideadzone_end=args.left_anti_end if args.left_anti_end is not None else args.anti_end,
        curve_preset=args.left_curve if args.left_curve is not None else args.curve,
        curve_intensity=args.left_intensity if args.left_intensity is not None else args.curve_intensity,
    )
    right = TriggerConfig(
        trigger_id=1,
        hair_mode=args.right_hair if args.right_hair is not None else args.hair,
        hair_trigger_begin=args.right_hair_begin if args.right_hair_begin is not None else args.hair_begin,
        hair_trigger_end=args.right_hair_end if args.right_hair_end is not None else args.hair_end,
        deadzone_begin=args.right_dz_begin if args.right_dz_begin is not None else args.dz_begin,
        deadzone_end=args.right_dz_end if args.right_dz_end is not None else args.dz_end,
        antideadzone_begin=args.right_anti_begin if args.right_anti_begin is not None else args.anti_begin,
        antideadzone_end=args.right_anti_end if args.right_anti_end is not None else args.anti_end,
        curve_preset=args.right_curve if args.right_curve is not None else args.curve,
        curve_intensity=args.right_intensity if args.right_intensity is not None else args.curve_intensity,
    )
    set_trigger_config(left, right)
    print(f"Left:  hair={left.hair_mode} dz={left.deadzone_begin}-{left.deadzone_end} anti={left.antideadzone_begin}-{left.antideadzone_end} curve={left.curve_preset}")
    print(f"Right: hair={right.hair_mode} dz={right.deadzone_begin}-{right.deadzone_end} anti={right.antideadzone_begin}-{right.antideadzone_end} curve={right.curve_preset}")


def cmd_turbo(args):
    import os, time
    from core.remap import resolve_button_index
    from core.transport import open_device

    btn = resolve_button_index(args.button)
    turbo = turbo_packet(btn, args.rate, args.continuous)
    enable = turbo_enable_packet(btn)
    commit = bytearray(32)
    commit[0:4] = [0x07, 0x03, 0x08, 0x03]

    fd = open_device()
    try:
        os.write(fd, turbo); time.sleep(0.03)
        os.write(fd, enable); time.sleep(0.03)
        os.write(fd, commit); time.sleep(0.03)
    finally:
        os.close(fd)

    mode = "continuous" if args.continuous else f"turbo {args.rate}Hz"
    print(f"Turbo: {args.button} ({mode})")


def cmd_rumble(args):
    if args.pct is not None:
        set_rumble_level(args.pct, args.pct if args.right is None else args.right)
        print(f"Rumble level set: left={args.pct}% right={args.right if args.right is not None else args.pct}%")
    if args.fire:
        l, r = args.fire if args.fire_right is None else (args.fire, args.fire_right)
        duration = args.duration if args.duration else 500
        print(f"Rumble fire: left={l}% right={r}% for {duration}ms")
        fire_rumble(l, r, duration)


def cmd_stick(args):
    stick = args.stick.lower()
    mode = args.mode.lower()
    if mode not in STICK_MODES:
        print(f"Unknown stick mode '{mode}'. Options: {list(STICK_MODES.keys())}")
        sys.exit(1)

    cfg = StickConfig(
        stick_id=0 if stick == "left" else 1,
        mode=mode,
        x_sensitivity=args.x_sens,
        y_sensitivity=args.y_sens,
        overlap_percent=args.overlap,
        mouse_x_dpi=args.mouse_dpi,
        mouse_y_dpi=args.mouse_ydpi,
        is_circle=not args.square,
        deadzone_min=args.deadzone_min,
        antideadzone_min=args.antideadzone_min,
        deadzone_max=args.deadzone_max,
        antideadzone_max=args.antideadzone_max,
        curve_preset=args.curve,
        curve_intensity=args.curve_intensity,
    )

    if mode == "keyboard":
        kbd = KeyboardMapping(
            left=args.kbd_left, right=args.kbd_right,
            up=args.kbd_up, down=args.kbd_down,
            overlap_left=args.kbd_ol_left, overlap_right=args.kbd_ol_right,
            overlap_up=args.kbd_ol_up, overlap_down=args.kbd_ol_down,
        )
        cfg.keyboard = kbd

    # Use default for the other stick
    other = StickConfig(stick_id=1 if stick == "left" else 0, mode="native")
    left_cfg = cfg if stick == "left" else other
    right_cfg = cfg if stick == "right" else other

    set_stick_config(left_cfg, right_cfg)
    print(f"Stick {stick}: mode={mode}")


def cmd_map(args):
    apply_mapping(args.button, args.target)
    print(f"Mapped {args.button} -> {args.target}")


def resolve_gyro_button(value):
    """Resolve button name or hex to index. Accepts c1, rb, lt, a, 0x29, etc."""
    v = str(value).lower().strip()
    if v in CONTROLLER_SOURCE:
        return CONTROLLER_SOURCE[v]
    if v in CONTROLLER_BUTTON:
        return CONTROLLER_BUTTON[v]
    if v.startswith("0x"):
        return int(v, 16)
    return int(v, 10)


def cmd_gyro(args):
    cfg = GyroConfig(
        output_mode=args.mode,
        motion_mode=args.motion,
        axis_mode=args.axis,
        activate_method=args.method,
        activate_button=resolve_gyro_button(args.button),
        x_sensitivity=args.x_sens,
        y_sensitivity=args.y_sens,
        overlap_percent=args.overlap,
        deadzone_min=args.deadzone_min,
        deadzone_max=args.deadzone_max,
        antideadzone_min=args.antideadzone_min,
        antideadzone_max=args.antideadzone_max,
        invert_x=args.invert_x,
        invert_y=args.invert_y,
        curve_preset=args.curve,
        curve_intensity=args.curve_intensity,
        kb_up=args.kb_up,
        kb_down=args.kb_down,
        kb_left=args.kb_left,
        kb_right=args.kb_right,
    )
    set_gyro_config(cfg)
    kb_info = f" keys={args.kb_up}/{args.kb_down}/{args.kb_left}/{args.kb_right}" if args.mode == "keyboard" else ""
    print(f"Gyro: mode={args.mode} motion={args.motion} method={args.method} axis={args.axis} button={args.button}{kb_info}")


def cmd_config(args):
    config = load_config()
    if args.show:
        import json
        print(json.dumps(config, indent=2))
    else:
        if args.get:
            keys = args.get.split(".")
            val = config
            for k in keys:
                val = val.get(k, {})
            print(val)
        if args.set:
            key, _, value = args.set.partition("=")
            keys = key.split(".")
            target = config
            for k in keys[:-1]:
                target = target.setdefault(k, {})
            try:
                target[keys[-1]] = int(value)
            except ValueError:
                target[keys[-1]] = value
            save_config(config)
            print(f"Set {key} = {value}")


def cmd_status(args):
    import json
    state = read_state()
    # Add gyro reads
    try:
        from core import read_gyro_targeting, read_gyro_geometry
        t = read_gyro_targeting()
        g = read_gyro_geometry()
        gyro = {}
        if t:
            gyro["x_sensitivity"] = t[4]
            gyro["y_sensitivity"] = t[5]
            gyro["method"] = t[6]
            gyro["motion_mode"] = t[7]
            gyro["output_mode"] = t[8]
            gyro["activate_button"] = t[9]
            gyro["axis"] = t[10]
        if g:
            gyro["x_sensitivity"] = g[10]
            gyro["deadzone_min"] = g[11]
            gyro["antideadzone_min"] = g[12]
            gyro["curve_coords"] = list(g[13:19])
            gyro["deadzone_max"] = g[19] if g[19] else 100
            gyro["antideadzone_max"] = g[20] if g[20] else 100
            gyro["curve_type"] = g[21] if len(g) > 21 else 0
            gyro["curve_intensity"] = g[22] if len(g) > 22 else 50
        if gyro:
            state["gyro"] = gyro
    except Exception:
        pass
    if args.json:
        print(json.dumps(state, indent=2, default=str))
    else:
        r = state.get("rumble", {})
        l = state.get("lighting", {})
        c = state.get("color", {})
        print(f"Rumble:   left={r.get('left', '?')}%  right={r.get('right', '?')}%")
        print(f"Lighting: brightness={l.get('brightness', '?')}  speed={l.get('speed', '?')}  mode={l.get('mode', '?')}")
        print(f"Color:    hue={c.get('hue', '?')}  sat={c.get('saturation', '?')}  light={c.get('lightness', '?')}")
        for name in ["left", "right"]:
            s = state.get(f"stick_{name}", {})
            if s:
                mode_names = {v: k for k, v in STICK_MODES.items()}
                mode = mode_names.get(s.get("mode", -1), str(s.get("mode", "?")))
                print(f"Stick {name}: mode={mode}  circle={s.get('is_circle', '?')}  dz_min={s.get('deadzone_min', '?')}  dz_max={s.get('deadzone_max', '?')}")
        gyro = state.get("gyro", {})
        if gyro:
            print(f"Gyro:    output_mode={gyro.get('output_mode', '?')}  button=0x{gyro.get('activate_button', 0):02x}  dz_min={gyro.get('deadzone_min', '?')}")
        layout = state.get("layout")
        if layout:
            print(f"Layout:  {layout}")
        for name in ["left", "right"]:
            tr = state.get(f"trigger_{name}", {})
            if tr:
                hair = tr.get("hair_mode", 0)
                hair_names = {0:"off",1:"adaptive",2:"fixed"}
                print(f"Trigger {name}: hair={hair_names.get(hair, hair)} dz={tr.get('deadzone_begin', '?')}-{tr.get('deadzone_end', '?')} anti={tr.get('antideadzone_begin', '?')}-{tr.get('antideadzone_end', '?')} curve={tr.get('curve_type', '?')}")
        if args.raw:
            for page, data in state.items():
                if page.startswith("page_"):
                    print(f"\n{page}:")
                    for reg, val in data.items():
                        print(f"  [{reg:02x}]: {val}")


def main():
    parser = argparse.ArgumentParser(description="GameGent — GameSir Tarantula Pro CLI")
    sub = parser.add_subparsers(dest="command")

    # light
    p = sub.add_parser("light", help="Set lighting mode")
    p.add_argument("mode", choices=list(LIGHTING_MODES.keys()))
    p.add_argument("--brightness", type=int, default=100)
    p.add_argument("--speed", type=int, default=100)
    p.set_defaults(func=cmd_light)

    # color
    p = sub.add_parser("color", help="Set lighting hue")
    p.add_argument("hue", type=int)
    p.set_defaults(func=cmd_color)

    # layout
    p = sub.add_parser("layout", help="Set ABXY button layout")
    p.add_argument("layout", choices=["xbox", "switch"])
    p.set_defaults(func=cmd_layout)

    # led
    p = sub.add_parser("led", help="Set per-LED color (panel or home)")
    p.add_argument("target", choices=["panel", "home"])
    p.add_argument("hue", type=int)
    p.add_argument("--saturation", type=int, default=100)
    p.add_argument("--lightness", type=int, default=50)
    p.set_defaults(func=cmd_led)

    # face
    p = sub.add_parser("face", help="Set button LED color (A, B, X, Y, home)")
    p.add_argument("button", choices=["a", "b", "x", "y", "home", "all"])
    p.add_argument("hue", type=int, nargs="?", default=0, help="Hue for single button mode")
    p.add_argument("--saturation", type=int, default=100)
    p.add_argument("--lightness", type=int, default=50)
    p.add_argument("--a-hue", type=int, default=0)
    p.add_argument("--a-sat", type=int, default=100)
    p.add_argument("--a-light", type=int, default=50)
    p.add_argument("--b-hue", type=int, default=0)
    p.add_argument("--b-sat", type=int, default=100)
    p.add_argument("--b-light", type=int, default=50)
    p.add_argument("--x-hue", type=int, default=0)
    p.add_argument("--x-sat", type=int, default=100)
    p.add_argument("--x-light", type=int, default=50)
    p.add_argument("--y-hue", type=int, default=0)
    p.add_argument("--y-sat", type=int, default=100)
    p.add_argument("--y-light", type=int, default=50)
    p.set_defaults(func=cmd_face)

    # trigger
    p = sub.add_parser("trigger", help="Configure trigger deadzones and hair trigger")
    p.add_argument("--hair", choices=list(HAIR_MODES.keys()), default="off", help="Default for both triggers")
    p.add_argument("--hair-begin", type=int, default=None, help="Hair trigger range begin")
    p.add_argument("--hair-end", type=int, default=None, help="Hair trigger range end")
    p.add_argument("--dz-begin", type=int, default=0)
    p.add_argument("--dz-end", type=int, default=100)
    p.add_argument("--anti-begin", type=int, default=0)
    p.add_argument("--anti-end", type=int, default=100)
    p.add_argument("--curve", choices=list(CURVE_PRESETS.keys()), default="linear")
    p.add_argument("--curve-intensity", type=int, default=50)
    # Left trigger overrides
    p.add_argument("--left-hair", choices=list(HAIR_MODES.keys()), default=None)
    p.add_argument("--left-hair-begin", type=int, default=None)
    p.add_argument("--left-hair-end", type=int, default=None)
    p.add_argument("--left-dz-begin", type=int, default=None)
    p.add_argument("--left-dz-end", type=int, default=None)
    p.add_argument("--left-anti-begin", type=int, default=None)
    p.add_argument("--left-anti-end", type=int, default=None)
    p.add_argument("--left-curve", choices=list(CURVE_PRESETS.keys()), default=None)
    p.add_argument("--left-intensity", type=int, default=None)
    # Right trigger overrides
    p.add_argument("--right-hair", choices=list(HAIR_MODES.keys()), default=None)
    p.add_argument("--right-hair-begin", type=int, default=None)
    p.add_argument("--right-hair-end", type=int, default=None)
    p.add_argument("--right-dz-begin", type=int, default=None)
    p.add_argument("--right-dz-end", type=int, default=None)
    p.add_argument("--right-anti-begin", type=int, default=None)
    p.add_argument("--right-anti-end", type=int, default=None)
    p.add_argument("--right-curve", choices=list(CURVE_PRESETS.keys()), default=None)
    p.add_argument("--right-intensity", type=int, default=None)
    p.set_defaults(func=cmd_trigger)

    # turbo
    p = sub.add_parser("turbo", help="Set turbo/continuous fire on a mapped button")
    p.add_argument("button", help="Button to turbo (e.g. l4, c1, rb)")
    p.add_argument("--rate", type=int, default=10, help="Turbo rate in Hz (default: 10)")
    p.add_argument("--continuous", action="store_true", help="Continuous fire (toggle on/off)")
    p.set_defaults(func=cmd_turbo)

    # rumble
    p = sub.add_parser("rumble", help="Set or fire grip rumble")
    p.add_argument("--set", dest="pct", type=int, help="Set rumble level (0-100%%)")
    p.add_argument("--right", type=int, help="Right grip level for --set (default: same as left)")
    p.add_argument("--fire", type=int, help="Fire rumble burst (0-100%%)")
    p.add_argument("--fire-right", type=int, help="Right grip for --fire (default: same as left)")
    p.add_argument("--duration", type=int, help="Burst duration in ms (default: 500)")
    p.set_defaults(func=cmd_rumble)

    # stick
    p = sub.add_parser("stick", help="Configure stick")
    p.add_argument("stick", choices=["left", "right"])
    p.add_argument("mode", choices=list(STICK_MODES.keys()))
    p.add_argument("--x-sens", type=int, default=50)
    p.add_argument("--y-sens", type=int, default=50)
    p.add_argument("--overlap", type=int, default=50)
    p.add_argument("--mouse-dpi", type=int, default=50)
    p.add_argument("--mouse-ydpi", type=int, default=50)
    p.add_argument("--square", action="store_true")
    p.add_argument("--deadzone-min", type=int, default=5)
    p.add_argument("--antideadzone-min", type=int, default=0)
    p.add_argument("--deadzone-max", type=int, default=100)
    p.add_argument("--antideadzone-max", type=int, default=100)
    p.add_argument("--curve", choices=list(CURVE_PRESETS.keys()), default="linear")
    p.add_argument("--curve-intensity", type=int, default=50)
    p.add_argument("--kbd-left", type=int, default=0x04)
    p.add_argument("--kbd-right", type=int, default=0x07)
    p.add_argument("--kbd-up", type=int, default=0x1a)
    p.add_argument("--kbd-down", type=int, default=0x16)
    p.add_argument("--kbd-ol-left", type=int, default=1)
    p.add_argument("--kbd-ol-right", type=int, default=1)
    p.add_argument("--kbd-ol-up", type=int, default=1)
    p.add_argument("--kbd-ol-down", type=int, default=1)
    p.set_defaults(func=cmd_stick)

    # map
    p = sub.add_parser("map", help="Remap button")
    p.add_argument("button")
    p.add_argument("target")
    p.set_defaults(func=cmd_map)

    # gyro
    p = sub.add_parser("gyro", help="Configure gyro/motion aim")
    p.add_argument("mode", choices=list(GYRO_OUTPUT_MODES.keys()))
    p.add_argument("--motion", choices=list(GYRO_MOTION_MODES.keys()), default="aim")
    p.add_argument("--method", choices=list(GYRO_METHODS.keys()), default="hold")
    p.add_argument("--axis", choices=list(GYRO_AXIS_MODES.keys()), default="global")
    p.add_argument("--button", default="c1", help="Activate button (name or hex)")
    p.add_argument("--x-sens", type=int, default=50)
    p.add_argument("--y-sens", type=int, default=50)
    p.add_argument("--overlap", type=int, default=50, help="Overlap threshold (keyboard mode)")
    p.add_argument("--deadzone-min", type=int, default=0)
    p.add_argument("--deadzone-max", type=int, default=100)
    p.add_argument("--antideadzone-min", type=int, default=0)
    p.add_argument("--antideadzone-max", type=int, default=100)
    p.add_argument("--curve", choices=list(CURVE_PRESETS.keys()), default="linear")
    p.add_argument("--curve-intensity", type=int, default=50)
    p.add_argument("--kb-up", default="key:w", help="Keyboard up target (key:x, controller:lt, mouse:scroll_up, unbind)")
    p.add_argument("--kb-down", default="key:s")
    p.add_argument("--kb-left", default="key:a")
    p.add_argument("--kb-right", default="key:d")
    p.add_argument("--invert-x", action="store_true", help="Invert X axis")
    p.add_argument("--invert-y", action="store_true", help="Invert Y axis")
    p.set_defaults(func=cmd_gyro)

    # config
    p = sub.add_parser("config", help="Get/set config values")
    p.add_argument("--show", action="store_true", help="Show full config")
    p.add_argument("--get", help="Get config key (dot notation)")
    p.add_argument("--set", help="Set config key=value (dot notation)")
    p.set_defaults(func=cmd_config)

    # status
    p = sub.add_parser("status", help="Read current controller state")
    p.add_argument("--json", action="store_true", help="Output as JSON")
    p.add_argument("--raw", action="store_true", help="Include raw page dumps")
    p.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
