# core/lighting.py — lighting mode, color, hue, layout, per-LED, face button colors
from .transport import send_raw_bytes
from .config import load_config, save_config

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


def build_layout_packet(layout: str, dpad_params: bytes) -> bytes:
    """SetDPadParam 07 09 09 01: b4 type, b5 swap, b6 layout, b7 auto on/off, b8 trigger
    auto-calibration, b9 macro switch. Copies b4..b9 from a GetDPadParam reply, sets b6."""
    layout = layout.lower().strip()
    if layout not in ("xbox", "switch"):
        raise ValueError(f"Unknown layout: {layout}")
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x09, 0x09, 0x01]
    packet[4:10] = dpad_params[4:10]
    packet[6] = 0x01 if layout == "xbox" else 0x02
    return bytes(packet)


def read_dpad_params() -> bytes | None:
    """GetDPadParam (07 03 09 02) reply, or None."""
    from .transport import open_device, close_device, drain, send_cmd, read_response
    fd = open_device()
    try:
        drain(fd)
        send_cmd(fd, bytes([0x07, 0x03, 0x09, 0x02]))
        return read_response(fd, header=bytes([0x07, 0x09, 0x02]))
    finally:
        close_device(fd)


def set_abxy_layout(layout: str):
    """Change only the layout byte; the packet also carries D-pad/auto-calibration settings."""
    current = read_dpad_params()
    if current is None:
        raise RuntimeError("Could not read D-pad params; not writing layout (would reset them)")
    send_raw_bytes(build_layout_packet(layout, current))


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


def set_face_button_color(button: str, hue: int, saturation: int = 100, lightness: int = 50):
    """Set individual button LED color (a, b, x, y, home). Uses persisted cache for A/B/X/Y."""
    button = button.lower().strip()
    if button == "home":
        set_led_color("home", hue, saturation, lightness)
        return
    positions = {"a": 0, "b": 1, "x": 2, "y": 3}
    if button not in positions:
        raise ValueError(f"Unknown button: {button}. Use 'a', 'b', 'x', 'y', or 'home'.")
    hue = max(0, min(360, hue))
    compressed_hue = (hue * 255) // 360
    saturation = max(0, min(100, saturation))
    lightness = max(0, min(100, lightness))

    pos = positions[button]
    config = load_config()
    if "face_leds" not in config:
        config["face_leds"] = [[0, 100, 50], [0, 100, 50], [0, 100, 50], [0, 100, 50]]
    colors = config["face_leds"]
    if len(colors) < 4:
        colors = [[0, 100, 50]] * 4
    colors[pos] = [compressed_hue, saturation, lightness]
    save_config(config)
    _send_face_packet_from(colors)


def set_face_colors(a_hsl: tuple, b_hsl: tuple, x_hsl: tuple, y_hsl: tuple):
    """Set all 4 face button colors at once. Each: (hue, saturation, lightness)."""
    colors = []
    for h, s, l in [a_hsl, b_hsl, x_hsl, y_hsl]:
        h = max(0, min(360, h))
        ch = (h * 255) // 360
        s = max(0, min(100, s))
        l = max(0, min(100, l))
        colors.append([ch, s, l])
    config = load_config()
    config["face_leds"] = colors
    save_config(config)
    _send_face_packet_from(colors)


def _send_face_packet_from(colors: list):
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x10, 0x07, 0x03]
    packet[4] = 0x05
    for i, (h, s, l) in enumerate(colors):
        offset = 5 + i * 3
        packet[offset] = h
        packet[offset + 1] = s
        packet[offset + 2] = l
    send_raw_bytes(packet)
