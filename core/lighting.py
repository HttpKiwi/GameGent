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
    # Copy only the fields the reply actually carries (length byte = data + 3); older
    # firmware sends 4 (type, swap, layout, auto on/off), newer adds calibration + macro key.
    n = max(0, min(6, dpad_params[1] - 3))
    packet[4:4 + n] = dpad_params[4:4 + n]
    packet[6] = 0x01 if layout == "xbox" else 0x02
    return bytes(packet)


def read_dpad_params() -> bytes | None:
    """GetDPadParam (07 03 09 02) reply, or None."""
    from .transport import open_device, close_device, drain, send_cmd, read_reply
    fd = open_device()
    try:
        drain(fd)
        send_cmd(fd, bytes([0x07, 0x03, 0x09, 0x02]))
        return read_reply(fd, 0x09, 0x02)
    finally:
        close_device(fd)


def set_abxy_layout(layout: str):
    """Change only the layout byte; the packet also carries D-pad/auto-calibration settings."""
    current = read_dpad_params()
    if current is None:
        raise RuntimeError("Could not read D-pad params; not writing layout (would reset them)")
    send_raw_bytes(build_layout_packet(layout, current))


LIGHT_NAMES = {"home": 0x00, "panel": 0x04, "abxy": 0x05, "bayx": 0x06}


def _hsv_bytes(hue: int, saturation: int, value: int) -> list[int]:
    """Device HSV: hue 0-360 degrees -> 0-255, saturation and value 0-100."""
    return [(max(0, min(360, hue)) * 255) // 360, max(0, min(100, saturation)), max(0, min(100, value))]


def build_light_color_packet(name: str, colors: list[tuple[int, int, int]]) -> bytes:
    """SetLightColor 07 10 07 03: [name] + 4 x (hue byte, saturation, value).

    Colours are (hue degrees, saturation, value) with value 0-100 (HSV, not HSL).
    Unused LEDs are zero-padded like the official app does.
    """
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x10, 0x07, 0x03]
    packet[4] = LIGHT_NAMES[name]
    for i, (h, s, v) in enumerate(colors[:4]):
        packet[5 + i * 3:8 + i * 3] = _hsv_bytes(h, s, v)
    return bytes(packet)


def set_led_color(target: str, hue: int, saturation: int = 100, value: int = 50):
    """Panel or home LED colour (HSV). The official app sets the panel's value to the
    lighting brightness, so callers pass brightness as `value` for the panel."""
    target = target.lower().strip()
    if target not in ("home", "panel"):
        raise ValueError(f"Unknown LED target: {target}. Use 'panel' or 'home'.")
    send_raw_bytes(build_light_color_packet(target, [(hue, saturation, value)]))


def set_face_button_color(button: str, hue: int, saturation: int = 100, lightness: int = 50):
    """Set individual button LED color (a, b, x, y, home). Uses persisted cache for A/B/X/Y."""
    button = button.lower().strip()
    if button == "home":
        set_led_color("home", hue, saturation, lightness)
        return
    positions = {"a": 0, "b": 1, "x": 2, "y": 3}
    if button not in positions:
        raise ValueError(f"Unknown button: {button}. Use 'a', 'b', 'x', 'y', or 'home'.")
    config = load_config()
    colors = config.get("face_leds") or []
    colors = [list(c) if c else [0, 100, 50] for c in (colors + [None] * 4)[:4]]
    colors[positions[button]] = _hsv_bytes(hue, saturation, lightness)
    config["face_leds"] = colors
    save_config(config)
    _send_face_packet_from(colors)


def set_face_colors(a_hsv: tuple, b_hsv: tuple, x_hsv: tuple, y_hsv: tuple, name: str = "abxy"):
    """All 4 face LEDs of one layout set ("abxy" Xbox / "bayx" Switch). Each: (hue, sat, value)."""
    send_raw_bytes(build_light_color_packet(name, [a_hsv, b_hsv, x_hsv, y_hsv]))


def _send_face_packet_from(colors: list):
    """colors: 4 x [hue byte, saturation, value] as stored in the config."""
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x10, 0x07, 0x03]
    packet[4] = LIGHT_NAMES["abxy"]
    for i, (h, s, v) in enumerate(colors[:4]):
        packet[5 + i * 3:8 + i * 3] = [h, s, v]
    send_raw_bytes(packet)
