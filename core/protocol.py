# core/protocol.py
from .transport import send_raw_bytes
from .hid_keycodes import (
    KEYBOARD_USAGE, MOUSE_BUTTON, MOUSE_SCROLL,
    keyboard_packet, mouse_button_packet, mouse_scroll_packet
)

# The absolute, verified hardware mode IDs
LIGHTING_MODES = {
    "off":       0x00,
    "static":    0x01,
    "breathing": 0x02,
    "colorful":  0x03,
    "rainbow":   0x04,
    "radar":     0x05
}

def set_hardware_state(mode: str, brightness: int, speed: int):
    """
    Constructs and pushes the precise 32-byte state payload to the MCU.
    Byte 4 is Brightness (0-100), Byte 5 is Speed (0-100).
    """
    if mode not in LIGHTING_MODES:
        raise ValueError(f"Unknown lighting mode: {mode}")

    # Map human percentages (0-100) safely to linear hex bytes
    brightness_hex = max(0, min(100, brightness))
    speed_hex = max(0, min(100, speed))
    mode_byte = LIGHTING_MODES[mode]

    # Build the exact frame layout verified by manual telemetry
    payload = [
        0x07, 0x06, 0x07, 0x01,  # Header Block
        brightness_hex,          # Byte 4: Brightness Slider (0-100)
        speed_hex,               # Byte 5: Animation Speed Slider (0-100)
        mode_byte,               # Byte 6: The Mode Selector
        0x00,                    # Byte 7: Pure zero padding
        0x00                     # Byte 8: Pure zero padding
    ]

    # Pad out the remainder of the 32-byte packet
    payload += [0x00] * (32 - len(payload))
    
    send_raw_bytes(payload)


def resolve_button_index(btn: str) -> int:
    """Resolve button name or hex string to index byte."""
    btn = btn.lower().strip()
    
    button_map = {
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
    if btn in button_map:
        return button_map[btn]

    raise ValueError(f"Unknown button identifier: {btn}")


def apply_mapping(btn: str, target: str):
    """Resolve and apply mapping for a controller button."""
    button_index = resolve_button_index(btn)
    target = target.lower().strip()

    if target in MOUSE_BUTTON:
        pkt = mouse_button_packet(button_index, MOUSE_BUTTON[target])
    elif target in MOUSE_SCROLL:
        pkt = mouse_scroll_packet(button_index, MOUSE_SCROLL[target])
    elif target in KEYBOARD_USAGE:
        pkt = keyboard_packet(button_index, KEYBOARD_USAGE[target])
    else:
        raise ValueError(f"Unknown mapping target: {target}")

    send_raw_bytes(pkt)
