# core/remap.py — button remapping
from .transport import send_raw_bytes
from .hid_keycodes import (
    KEYBOARD_USAGE, MOUSE_BUTTON, MOUSE_SCROLL,
    CONTROLLER_BUTTON, CONTROLLER_SOURCE,
    unbind_packet, combo_packet,
    build_macro_init_packet,
    apply_turbo, turbo_enable_packet, reset_packet, build_remap_packet,
)
from .targets import encode_target

SAVE_CONFIG_PAGE = bytes([0x07, 0x03, 0x08, 0x03])


def resolve_button_index(btn: str) -> int:
    """Resolve button name or hex string to index byte. Accepts all controller buttons."""
    btn = btn.lower().strip()
    if btn in CONTROLLER_SOURCE:
        return CONTROLLER_SOURCE[btn]
    if btn in CONTROLLER_BUTTON:
        return CONTROLLER_BUTTON[btn]
    if btn.startswith("0x"):
        return int(btn, 16)
    try:
        return int(btn, 10)
    except ValueError:
        raise ValueError(f"Unknown button identifier: {btn}")


def resolve_target_packet(button_index: int, target: str) -> bytes:
    """Remap packet for `target`: controller:/key:/mouse:/media: strings (see core/targets.py),
    "none" (button does nothing), or "reset" (factory mapping)."""
    t = target.lower().strip()
    if t in ("unbind", "none", "nc"):
        return unbind_packet(button_index)
    if t == "reset":
        return reset_packet(button_index)
    report, payload = encode_target(t)
    return build_remap_packet(button_index, report, payload)


def apply_mapping(btn: str, target: str):
    button_index = resolve_button_index(btn)
    pkt = resolve_target_packet(button_index, target)
    send_raw_bytes(pkt)
    commit = bytearray(32)
    commit[0:4] = [0x07, 0x03, 0x08, 0x03]
    send_raw_bytes(commit)


def resolve_combo_keys(keys: list[str]) -> tuple[list[int], list[str]]:
    """Resolve prefixed key targets to (ids, types)."""
    ids = []
    types = []
    for key in keys:
        key = key.lower().strip()
        if key.startswith("btn:") or key.startswith("button:") or key.startswith("controller:"):
            btn_name = key.split(":", 1)[1].strip()
            if btn_name in CONTROLLER_BUTTON:
                ids.append(CONTROLLER_BUTTON[btn_name])
                types.append("ctrl")
            else:
                raise ValueError(f"Unknown controller button: {btn_name}")
        elif key.startswith("key:") or key.startswith("keyboard:"):
            key_name = key.split(":", 1)[1].strip()
            if key_name in KEYBOARD_USAGE:
                ids.append(KEYBOARD_USAGE[key_name])
                types.append("kbd")
            else:
                raise ValueError(f"Unknown keyboard key: {key_name}")
        elif key.startswith("mouse:"):
            mouse_name = key.split(":", 1)[1].strip()
            if mouse_name in MOUSE_BUTTON:
                ids.append(MOUSE_BUTTON[mouse_name])
                types.append("mouse")
            elif mouse_name in MOUSE_SCROLL:
                ids.append(MOUSE_SCROLL[mouse_name])
                types.append("mouse")
            else:
                raise ValueError(f"Unknown mouse target: {mouse_name}")
        else:
            raise ValueError(f"Combo key must have prefix (controller:, key:, mouse:), got: {key}")
    return ids, types


def apply_combo(btn: str, keys: list[str]):
    button_index = resolve_button_index(btn)
    key_ids, key_types = resolve_combo_keys(keys)
    pkt = combo_packet(button_index, key_ids, key_types)
    send_raw_bytes(pkt)
    enable = bytearray(32)
    enable[0:4] = [0x07, 0x13, 0x01, 0x01]
    enable[4] = button_index
    enable[5] = 0xff
    send_raw_bytes(enable)
    commit = bytearray(32)
    commit[0:4] = [0x07, 0x03, 0x08, 0x03]
    send_raw_bytes(commit)


MAX_MACRO_STEPS = 12


def parse_macro_step(spec: str) -> tuple[str, int, int]:
    """'key:a:0:50' / 'lb:0:50' -> (target, press_ms, release_ms); times come last."""
    parts = spec.strip().rsplit(":", 2)
    if len(parts) != 3:
        raise ValueError(f"Invalid macro step '{spec}' (use target:press_ms:release_ms)")
    return parts[0], int(parts[1]), int(parts[2])


def build_macro_step_packet(button_index: int, step_index: int, target: str, press_ms: int,
                            release_ms: int, macro_type: int = 0x01, loop: bool = False,
                            loop_ms: int = 0) -> bytes:
    """SetMacroStep 07 13 01 01: one press/release of `target` (any mapping target, or a bare
    controller button name) at press_ms..release_ms after the macro starts.

    macro_type: trigger mode, 1 = fire on press, 2 = repeat while held.
    """
    report, payload = encode_target(target if ":" in target else f"controller:{target}")
    pkt = bytearray(32)
    pkt[0:4] = [0x07, 0x13, 0x01, 0x01]
    pkt[4] = button_index
    pkt[5] = step_index
    pkt[6] = macro_type
    pkt[7] = 0x01 if loop else 0x00
    pkt[8], pkt[9] = (loop_ms >> 8) & 0xFF, loop_ms & 0xFF
    pkt[10], pkt[11] = report[0], report[1]
    pkt[12:16] = payload[:4]
    pkt[16], pkt[17] = (press_ms >> 8) & 0xFF, press_ms & 0xFF
    pkt[18], pkt[19] = (release_ms >> 8) & 0xFF, release_ms & 0xFF
    return bytes(pkt)


def apply_macro(btn: str, steps: list[tuple[str, int, int]],
                macro_type: int = 0x01, loop: bool = False, loop_ms: int = 0):
    """Apply a macro to a button: the button becomes "vacant" with up to 12 timed steps.

    steps: (target, press_ms, release_ms); a macro uses one kind of target (controller, key
    or mouse), like the official app.
    """
    if len(steps) > MAX_MACRO_STEPS:
        raise ValueError(f"A macro has at most {MAX_MACRO_STEPS} steps")
    packets = [build_macro_step_packet(0, i, t, p, r, macro_type, loop, loop_ms)
               for i, (t, p, r) in enumerate(steps)]
    if len({pkt[10] for pkt in packets}) > 1:
        raise ValueError("A macro can't mix controller, keyboard and mouse steps")
    button_index = resolve_button_index(btn)
    send_raw_bytes(build_macro_init_packet(button_index))
    send_raw_bytes(turbo_enable_packet(button_index))  # clear existing steps (index 0xFF)
    for pkt in packets:
        pkt = bytearray(pkt)
        pkt[4] = button_index
        send_raw_bytes(bytes(pkt))
    send_raw_bytes(SAVE_CONFIG_PAGE)


def set_turbo(btn: str, target: str, rate: int | None, continuous: bool = False):
    """Map btn -> target with turbo (rate Hz; None = no turbo) and/or toggle, then save."""
    index = resolve_button_index(btn)
    remap = resolve_target_packet(index, target)
    send_raw_bytes(apply_turbo(remap, rate or 1, continuous, turbo=rate is not None))
    send_raw_bytes(turbo_enable_packet(index))
    send_raw_bytes(SAVE_CONFIG_PAGE)
