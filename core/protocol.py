# core/protocol.py
from dataclasses import dataclass
from typing import List
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


def generate_color_packet(hue: int) -> bytes:
    """
    Accepts a hue integer (0-360), handles boundary clipping,
    performs the 8-bit scaling math, and returns a 32-byte bytes object.
    Supported across breathing, radar, and static lighting modes.
    
    Mathematical Conversion:
      The hardware compresses a 0-360° Hue angle into a single 8-bit byte (0-255).
      Formula: Byte_Value = (Hue_Angle * 255) // 360
    """
    # Boundary clipping
    hue = max(0, min(360, hue))
    
    # 8-bit scaling math matching verified hardware vectors
    compressed_hue = (hue * 255) // 360
    
    # Construct 32-byte packet
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x10, 0x07, 0x03]
    packet[4] = 0x04
    packet[5] = compressed_hue
    packet[6] = 0x64  # Saturation (100% / 0x64)
    packet[7] = 0x32  # Lightness (50% / 0x32)
    
    return bytes(packet)


def set_color(hue: int):
    """Generates and sends the HSL custom color packet to the MCU."""
    pkt = generate_color_packet(hue)
    send_raw_bytes(pkt)


# Verification test assertions using hardware vectors
def test_color_assertions():
    # Hue 0°   -> Byte 5: 0x00
    assert generate_color_packet(0)[5] == 0x00
    # Hue 124° -> Byte 5: 0x57
    assert generate_color_packet(124)[5] == 0x57
    # Hue 242° -> Byte 5: 0xAB
    assert generate_color_packet(242)[5] == 0xAB
    # Hue 297° -> Byte 5: 0xD2
    assert generate_color_packet(297)[5] == 0xD2
    # Hue 360° -> Byte 5: 0xFF
    assert generate_color_packet(360)[5] == 0xFF


@dataclass
class JoystickConfig:
    is_circle: bool = True
    deadzone_min: int = 5
    antideadzone_min: int = 0
    deadzone_max: int = 100
    antideadzone_max: int = 100
    curve_preset: str = "linear"
    curve_intensity: int = 50


# Verified Curve Preset Node Constants
CURVE_PRESETS = {
    "linear": {
        "coords": [0x14, 0x10, 0x35, 0x32, 0x55, 0x54],
        "curve_type": 0x00
    },
    "expo": {
        "coords": [0x1b, 0x17, 0x35, 0x32, 0x4e, 0x4d],
        "curve_type": 0x01
    },
    "s-curve": {
        "coords": [0x0e, 0x1e, 0x2c, 0x32, 0x4a, 0x46],
        "curve_type": 0x02
    }
}


def build_joystick_packet(config: JoystickConfig, is_right: bool = False) -> bytes:
    """
    Compiles a single 32-byte geometry payload using the correct node constants
    based on the chosen curve preset.
    """
    packet = bytearray(32)
    
    # Bytes 0-3: [0x07, 0x18, 0x02, 0x01]
    packet[0:4] = [0x07, 0x18, 0x02, 0x01]
    
    # Bytes 4-10: [0x00] * 7 for Left Stick, and sets byte 4 to 0x01 and byte 6 to 0x01 for Right Stick.
    if is_right:
        packet[4:11] = [0x01, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00]
    else:
        packet[4:11] = [0x00] * 7
        
    # Byte 11: Outer Boundary Mode (0x00 = Raw/Square, 0x01 = Circle)
    packet[11] = 0x01 if config.is_circle else 0x00
    
    # Byte 12: Fixed at 0x32
    packet[12] = 0x32
    
    # Clip settings to 0-100 range
    dz_min = max(0, min(100, config.deadzone_min))
    adz_min = max(0, min(100, config.antideadzone_min))
    dz_max = max(0, min(100, config.deadzone_max))
    adz_max = max(0, min(100, config.antideadzone_max))
    intensity = max(0, min(100, config.curve_intensity))
    
    # Byte 13: Dead Zone Minimum
    packet[13] = dz_min
    
    # Byte 14: Anti-Dead Zone Minimum
    packet[14] = adz_min
    
    # Resolve curve preset (case-insensitive, handling hyphens and underscores)
    preset_key = config.curve_preset.lower().replace("_", "-")
    if preset_key not in CURVE_PRESETS:
        # Graceful fallback to linear
        preset_info = CURVE_PRESETS["linear"]
    else:
        preset_info = CURVE_PRESETS[preset_key]
        
    coords = preset_info["coords"]
    curve_type = preset_info["curve_type"]
    
    # Bytes 15-20: Points 1, 2, and 3 (X, Y)
    packet[15:21] = coords
    
    # Byte 21: Dead Zone Maximum
    packet[21] = dz_max
    
    # Byte 22: Anti-Dead Zone Maximum
    packet[22] = adz_max
    
    # Byte 23: Curve Profile Preset Type (0x00=Linear, 0x01=Expo, 0x02=S-Curve)
    packet[23] = curve_type
    
    # Byte 24: Curve Intensity Slider
    packet[24] = intensity
    
    # Bytes 25-31: [0x00] * 7 (already initialized to 0 in bytearray)
    return bytes(packet)


def generate_full_joystick_handshake(left_config: JoystickConfig, right_config: JoystickConfig) -> List[bytes]:
    """
    Pieces together the full 5-packet transaction array.
    """
    p0 = bytes.fromhex("070f020300312850000000013232000000000000000000000000000000000000")
    p1 = build_joystick_packet(left_config, is_right=False)
    p2 = bytes.fromhex("070f020301282850000000013232000000000000000000000000000000000000")
    p3 = build_joystick_packet(right_config, is_right=True)
    p4 = bytes.fromhex("0703080300000000000000000000000000000000000000000000000000000000")
    
    return [p0, p1, p2, p3, p4]


def set_joystick_state(left_config: JoystickConfig, right_config: JoystickConfig):
    """
    Generates and pushes the 5-packet joystick configuration sequence to the MCU.
    """
    packets = generate_full_joystick_handshake(left_config, right_config)
    for pkt in packets:
        send_raw_bytes(pkt)


def test_joystick_assertions():
    """
    Validates that two default linear configs generate the exact 5-packet baseline sequence.
    """
    left = JoystickConfig(
        is_circle=True,
        deadzone_min=5,
        antideadzone_min=0,
        deadzone_max=100,
        antideadzone_max=100,
        curve_preset="linear",
        curve_intensity=50
    )
    right = JoystickConfig(
        is_circle=True,
        deadzone_min=5,
        antideadzone_min=0,
        deadzone_max=100,
        antideadzone_max=100,
        curve_preset="linear",
        curve_intensity=50
    )
    packets = generate_full_joystick_handshake(left, right)
    
    expected = [
        "070f020300312850000000013232000000000000000000000000000000000000",
        "0718020100000000000000013205001410353255546464003200000000000000",
        "070f020301282850000000013232000000000000000000000000000000000000",
        "0718020101000100000000013205001410353255546464003200000000000000",
        "0703080300000000000000000000000000000000000000000000000000000000"
    ]
    
    assert len(packets) == 5, f"Expected 5 packets, got {len(packets)}"
    for i, (pkt, exp) in enumerate(zip(packets, expected)):
        assert pkt.hex() == exp, f"Packet {i} mismatch:\nExpected: {exp}\nGot:      {pkt.hex()}"



