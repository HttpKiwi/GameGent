# core/protocol.py
from .transport import send_raw_bytes
from .hid_keycodes import (
    KEYBOARD_USAGE, MOUSE_BUTTON, MOUSE_SCROLL,
    CONTROLLER_BUTTON, CONTROLLER_SOURCE,
    keyboard_packet, mouse_button_packet, mouse_scroll_packet,
    controller_packet, unbind_packet,
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
    
    if btn in CONTROLLER_SOURCE:
        return CONTROLLER_SOURCE[btn]

    raise ValueError(f"Unknown button identifier: {btn}")


def resolve_target_packet(button_index: int, target: str) -> bytes:
    """Helper to parse a target and return the corresponding HID packet bytes."""
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
    """Resolve and apply mapping for a controller button."""
    button_index = resolve_button_index(btn)
    pkt = resolve_target_packet(button_index, target)
    send_raw_bytes(pkt)

