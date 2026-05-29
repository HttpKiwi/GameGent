# core/lighting.py — lighting mode, color, hue control
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
