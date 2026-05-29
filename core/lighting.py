# core/lighting.py — lighting mode, color, hue, layout, per-LED control
from .transport import send_raw_bytes

LIGHTING_MODES = {
    "off":       0x00,
    "static":    0x01,
    "breathing": 0x02,
    "colorful":  0x03,
    "rainbow":   0x04,
    "radar":     0x05
}


def set_hardware_state(mode: str, brightness: int, speed: int):
    if mode not in LIGHTING_MODES:
        raise ValueError(f"Unknown lighting mode: {mode}")
    brightness_hex = max(0, min(100, brightness))
    speed_hex = max(0, min(100, speed))
    mode_byte = LIGHTING_MODES[mode]
    payload = [
        0x07, 0x06, 0x07, 0x01,
        brightness_hex,
        speed_hex,
        mode_byte,
        0x00, 0x00
    ]
    payload += [0x00] * (32 - len(payload))
    send_raw_bytes(payload)


def generate_color_packet(hue: int) -> bytes:
    hue = max(0, min(360, hue))
    compressed_hue = (hue * 255) // 360
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x10, 0x07, 0x03]
    packet[4] = 0x04
    packet[5] = compressed_hue
    packet[6] = 0x64
    packet[7] = 0x32
    return bytes(packet)


def set_color(hue: int):
    pkt = generate_color_packet(hue)
    send_raw_bytes(pkt)


def set_abxy_layout(layout: str):
    """Set ABXY button layout. Header: 07 09 09 01. layout: 'xbox' or 'switch'."""
    layout = layout.lower().strip()
    if layout not in ("xbox", "switch"):
        raise ValueError(f"Unknown layout: {layout}")
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x09, 0x09, 0x01]
    packet[6] = 0x01 if layout == "xbox" else 0x02
    send_raw_bytes(packet)


def set_led_color(target: str, hue: int, saturation: int = 100, lightness: int = 50):
    """Set per-LED color via 07 10 07 03. target: 'panel' or 'home'."""
    target = target.lower().strip()
    selectors = {"home": 0x00, "panel": 0x04}
    if target not in selectors:
        raise ValueError(f"Unknown LED target: {target}. Use 'panel' or 'home'.")
    hue = max(0, min(360, hue))
    compressed_hue = (hue * 255) // 360
    saturation = max(0, min(100, saturation))
    lightness = max(0, min(100, lightness))
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x10, 0x07, 0x03]
    packet[4] = selectors[target]
    packet[5] = compressed_hue
    packet[6] = saturation
    packet[7] = lightness
    send_raw_bytes(packet)


# Per-button color cache (H, S, L for A, B, X, Y)
_face_colors = [[0, 100, 50], [0, 100, 50], [0, 100, 50], [0, 100, 50]]


def set_face_button_color(button: str, hue: int, saturation: int = 100, lightness: int = 50):
    """Set individual face button color (A, B, X, Y). Sends all 4 at once."""
    button = button.lower().strip()
    positions = {"a": 0, "b": 1, "x": 2, "y": 3}
    if button not in positions:
        raise ValueError(f"Unknown face button: {button}. Use 'a', 'b', 'x', or 'y'.")
    hue = max(0, min(360, hue))
    compressed_hue = (hue * 255) // 360
    saturation = max(0, min(100, saturation))
    lightness = max(0, min(100, lightness))

    pos = positions[button]
    _face_colors[pos] = [compressed_hue, saturation, lightness]

    packet = bytearray(32)
    packet[0:4] = [0x07, 0x10, 0x07, 0x03]
    packet[4] = 0x05
    for i, (h, s, l) in enumerate(_face_colors):
        offset = 5 + i * 3
        packet[offset] = h
        packet[offset + 1] = s
        packet[offset + 2] = l
    send_raw_bytes(packet)
