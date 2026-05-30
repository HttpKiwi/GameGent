# core/remap.py — button remapping
from .transport import send_raw_bytes
from .hid_keycodes import (
    KEYBOARD_USAGE, MOUSE_BUTTON, MOUSE_SCROLL,
    CONTROLLER_BUTTON, CONTROLLER_SOURCE,
    keyboard_packet, mouse_button_packet, mouse_scroll_packet,
    controller_packet, unbind_packet, combo_packet,
    build_macro_init_packet, build_macro_step_packet,
)


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
    target = target.lower().strip()
    if target.startswith("key:") or target.startswith("keyboard:"):
        key_name = target.split(":", 1)[1].strip()
        if key_name in KEYBOARD_USAGE:
            return keyboard_packet(button_index, KEYBOARD_USAGE[key_name])
        raise ValueError(f"Unknown keyboard key: {key_name}")
    if target.startswith("btn:") or target.startswith("button:") or target.startswith("controller:"):
        btn_name = target.split(":", 1)[1].strip()
        if btn_name in CONTROLLER_BUTTON:
            return controller_packet(button_index, CONTROLLER_BUTTON[btn_name])
        raise ValueError(f"Unknown controller button: {btn_name}")
    if target.startswith("mouse:"):
        mouse_name = target.split(":", 1)[1].strip()
        if mouse_name in MOUSE_BUTTON:
            return mouse_button_packet(button_index, MOUSE_BUTTON[mouse_name])
        if mouse_name in MOUSE_SCROLL:
            return mouse_scroll_packet(button_index, MOUSE_SCROLL[mouse_name])
        raise ValueError(f"Unknown mouse target: {mouse_name}")
    if target == "unbind":
        return unbind_packet(button_index)
    if target in MOUSE_BUTTON:
        return mouse_button_packet(button_index, MOUSE_BUTTON[target])
    if target in MOUSE_SCROLL:
        return mouse_scroll_packet(button_index, MOUSE_SCROLL[target])
    if target in KEYBOARD_USAGE:
        return keyboard_packet(button_index, KEYBOARD_USAGE[target])
    if target in CONTROLLER_BUTTON:
        return controller_packet(button_index, CONTROLLER_BUTTON[target])
    raise ValueError(f"Unknown mapping target: {target}")


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


def apply_macro(btn: str, steps: list[tuple[str, int, int]],
                macro_type: int = 0x01, loop: bool = False):
    """Apply a macro to a button.
    
    steps: list of (button_name_or_id, press_ms, release_ms)
    macro_type: 0x01=normal (fire on press), 0x02=hold (fire while held)
    loop: if True, macro repeats
    """
    button_index = resolve_button_index(btn)
    send_raw_bytes(build_macro_init_packet(button_index))
    enable = bytearray(32)
    enable[0:4] = [0x07, 0x13, 0x01, 0x01]
    enable[4] = button_index
    enable[5] = 0xff
    send_raw_bytes(enable)
    for i, (step_btn, press, release) in enumerate(steps):
        if step_btn in CONTROLLER_BUTTON:
            btn_id = CONTROLLER_BUTTON[step_btn]
        else:
            btn_id = resolve_button_index(step_btn)
        send_raw_bytes(build_macro_step_packet(
            button_index, i, btn_id, press, release, macro_type, loop))
    commit = bytearray(32)
    commit[0:4] = [0x07, 0x03, 0x08, 0x03]
    send_raw_bytes(commit)
