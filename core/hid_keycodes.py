# core/hid_keycodes.py
"""USB HID Keyboard Usage IDs (HID Usage Tables §10, page 0x07)."""

# Standard USB HID keyboard usage IDs — published spec, no capture needed
KEYBOARD_USAGE = {
    # Reserve/system
    "reserved": 0x00, "error_rollover": 0x01, "post_fail": 0x02, "error_undefined": 0x03,
    # Letters
    "a": 0x04, "b": 0x05, "c": 0x06, "d": 0x07, "e": 0x08, "f": 0x09,
    "g": 0x0a, "h": 0x0b, "i": 0x0c, "j": 0x0d, "k": 0x0e, "l": 0x0f,
    "m": 0x10, "n": 0x11, "o": 0x12, "p": 0x13, "q": 0x14, "r": 0x15,
    "s": 0x16, "t": 0x17, "u": 0x18, "v": 0x19, "w": 0x1a, "x": 0x1b,
    "y": 0x1c, "z": 0x1d,
    # Numbers
    "1": 0x1e, "2": 0x1f, "3": 0x20, "4": 0x21, "5": 0x22,
    "6": 0x23, "7": 0x24, "8": 0x25, "9": 0x26, "0": 0x27,
    # Navigation / editing
    "enter": 0x28, "escape": 0x29, "backspace": 0x2a, "tab": 0x2b,
    "space": 0x2c,
    # Symbols
    "minus": 0x2d, "equal": 0x2e, "bracket_left": 0x2f, "bracket_right": 0x30,
    "backslash": 0x31, "hash_non_us": 0x32, "semicolon": 0x33, "quote": 0x34,
    "grave": 0x35, "comma": 0x36, "period": 0x37, "slash": 0x38,
    # Lock
    "caps_lock": 0x39,
    # Function keys
    "f1": 0x3a, "f2": 0x3b, "f3": 0x3c, "f4": 0x3d,
    "f5": 0x3e, "f6": 0x3f, "f7": 0x40, "f8": 0x41,
    "f9": 0x42, "f10": 0x43, "f11": 0x44, "f12": 0x45,
    "f13": 0x68, "f14": 0x69, "f15": 0x6a, "f16": 0x6b,
    "f17": 0x6c, "f18": 0x6d, "f19": 0x6e, "f20": 0x6f,
    "f21": 0x70, "f22": 0x71, "f23": 0x72, "f24": 0x73,
    # System
    "print_screen": 0x46, "scroll_lock": 0x47, "pause": 0x48,
    "insert": 0x49, "home": 0x4a, "page_up": 0x4b,
    "delete": 0x4c, "end": 0x4d, "page_down": 0x4e,
    # Arrows
    "right": 0x4f, "left": 0x50, "down": 0x51, "up": 0x52,
    # Numpad
    "num_lock": 0x53,
    "kp_divide": 0x54, "kp_multiply": 0x55, "kp_minus": 0x56,
    "kp_plus": 0x57, "kp_enter": 0x58,
    "kp_1": 0x59, "kp_2": 0x5a, "kp_3": 0x5b,
    "kp_4": 0x5c, "kp_5": 0x5d, "kp_6": 0x5e,
    "kp_7": 0x5f, "kp_8": 0x60, "kp_9": 0x61,
    "kp_0": 0x62, "kp_dot": 0x63,
    "backslash_non_us": 0x64,
    "application": 0x65, "power": 0x66, "kp_equal": 0x67,
    # Modifiers
    "left_ctrl": 0xe0, "left_shift": 0xe1, "left_alt": 0xe2, "left_gui": 0xe3,
    "right_ctrl": 0xe4, "right_shift": 0xe5, "right_alt": 0xe6, "right_gui": 0xe7,
}

# Standard USB HID mouse button bitfield values
MOUSE_BUTTON = {
    "left_click": 0x01,
    "right_click": 0x02,
    "middle_click": 0x04,
    "button_4": 0x10,
    "button_5": 0x08,
}
MOUSE_SCROLL = {
    "scroll_up": 0x01,
    "scroll_down": 0xff,
}

# GameSir controller button IDs (target — when remapping a physical button to
# another controller button)
CONTROLLER_BUTTON = {
    "b":          0x00,
    "a":          0x01,
    "y":          0x02,
    "x":          0x03,
    "lb":         0x04,
    "lt":         0x05,
    "l3":         0x06,
    "rb":         0x07,
    "rt":         0x08,
    "r3":         0x09,
    "back":       0x0a,
    "start":      0x0b,
    "dpad_left":  0x0c,
    "dpad_right": 0x0d,
    "dpad_up":    0x0e,
    "dpad_down":  0x0f,
    "screenshot": 0x2d,
}

# GameSir physical remappable buttons (sources)
CONTROLLER_SOURCE = {
    "c1": 0x29,
    "c2": 0x2a,
    "c3": 0x2b,
    "c4": 0x2c,
    "t1": 0x26,
    "t2": 0x27,
    "t3": 0x28,
    "l4": 0x24,
    "r4": 0x25,
}


# Report type markers
REPORT_KEYBOARD   = b"\x02\x02"
REPORT_MOUSE      = b"\x03\x04"
REPORT_CONTROLLER = b"\x01\x01"
REPORT_UNBIND     = b"\x00\x00"
REPORT_COMBO_2KEY = b"\x01\x02"
REPORT_COMBO_3KEY = b"\x01\x03"
REPORT_TURBO      = b"\x04\x04"


def build_remap_packet(button_index: int, report_type: bytes, payload: bytes) -> bytes:
    """Build a 32-byte remapping HID packet for a given controller button."""
    assert len(report_type) == 2
    assert len(payload) == 16

    header = bytes([
        0x07, 0x13, 0x05, 0x01,   # bytes 0-3: command
        0x00, 0x00, 0x00, 0x00,   # bytes 4-7: padding
        0x00, 0x00,               # bytes 8-9: padding
        button_index,             # byte 10: physical button
        0x00, 0x00,               # bytes 11-12: padding
        0x01,                     # byte 13: flag
    ])
    header += report_type          # bytes 14-15

    assert len(header) == 16
    return header + payload


def keyboard_packet(button_index: int, usage_id: int) -> bytes:
    """Build remap packet that sends a keyboard key."""
    payload = bytes([0x00, usage_id]) + b"\x00" * 14
    return build_remap_packet(button_index, REPORT_KEYBOARD, payload)


def mouse_button_packet(button_index: int, button_bitfield: int) -> bytes:
    """Build remap packet for a mouse click."""
    payload = bytes([0x00, 0x00, 0x00, button_bitfield]) + b"\x00" * 12
    return build_remap_packet(button_index, REPORT_MOUSE, payload)


def mouse_scroll_packet(button_index: int, scroll_value: int) -> bytes:
    """Build remap packet for scroll wheel (0x01 = up, 0xff = down)."""
    payload = bytes([0x00, 0x00, scroll_value, 0x00]) + b"\x00" * 12
    return build_remap_packet(button_index, REPORT_MOUSE, payload)


def controller_packet(button_index: int, target_button_id: int) -> bytes:
    """Build remap packet that maps to another controller button."""
    payload = bytes([target_button_id]) + b"\x00" * 15
    return build_remap_packet(button_index, REPORT_CONTROLLER, payload)


def unbind_packet(button_index: int) -> bytes:
    """Build remap packet that unbinds (disables) a physical button."""
    payload = b"\x00" * 16
    return build_remap_packet(button_index, REPORT_UNBIND, payload)


def apply_turbo(remap_packet: bytes, rate_hz: int = 10, continuous: bool = False, turbo: bool = True) -> bytes:
    """Inject turbo/continuous flags into a remap packet at bytes 11-13.
    
    byte 11: continuous toggle (0x00=off, 0x01=on)
    byte 12: turbo mode (0x02=on, 0x00=off)
    byte 13: rate Hz (when turbo on) or 0x01
    """
    rate = max(1, min(255, rate_hz))
    pkt = bytearray(remap_packet)
    pkt[11] = 0x01 if continuous else 0x00
    pkt[12] = 0x02 if turbo else 0x00
    pkt[13] = rate if turbo else 0x01
    return bytes(pkt)


def resolve_combo_report_type(keys: list[int], key_types: list[str]) -> bytes:
    """Determine combo report type bytes.
    
    byte14: 01=controller, 02=keyboard, 03=mouse
    byte15: payload byte count
      ctrl: N keys
      kbd:  1 (modifier) + N keys
      mouse: 4 (always fixed: 3 zeros + bitfield byte)
    """
    assert len(keys) in (2, 3)
    types = set(key_types)
    if types == {"ctrl"}:
        return bytes([0x01, len(keys)])
    if types == {"kbd"}:
        return bytes([0x02, 1 + len(keys)])
    if types == {"mouse"}:
        return bytes([0x03, 0x04])
    raise ValueError(f"Mixed key types not supported for combos: {types}")


def combo_packet(button_index: int, keys: list[int], key_types: list[str]) -> bytes:
    """Build remap packet for a combo (2 or 3 keys, all same type)."""
    assert len(keys) in (2, 3)
    assert len(keys) == len(key_types)
    report_type = resolve_combo_report_type(keys, key_types)
    if key_types[0] == "kbd":
        payload = bytes([0x00] + keys)
    elif key_types[0] == "mouse":
        bitfield = 0
        for k in keys:
            bitfield |= k
        payload = bytes([0x00, 0x00, 0x00, bitfield])
    else:
        payload = bytes(keys)
    payload += b"\x00" * (16 - len(payload))
    return build_remap_packet(button_index, report_type, payload)


def turbo_enable_packet(button_index: int) -> bytes:
    """Build turbo enable/commit packet (07 13 01 01)."""
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x13, 0x01, 0x01]
    packet[4] = button_index
    packet[5] = 0xff
    return bytes(packet)
