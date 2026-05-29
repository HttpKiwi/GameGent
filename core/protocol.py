# core/protocol.py
import os
from dataclasses import dataclass
from typing import List
from .transport import send_raw_bytes, open_device, init_session, read_typed_register, read_page_register, read_response, drain
from .hid_keycodes import (
    KEYBOARD_USAGE, MOUSE_BUTTON, MOUSE_SCROLL,
    CONTROLLER_BUTTON, CONTROLLER_SOURCE,
    keyboard_packet, mouse_button_packet, mouse_scroll_packet,
    controller_packet, unbind_packet,
    REPORT_KEYBOARD, REPORT_MOUSE, REPORT_CONTROLLER, REPORT_UNBIND,
    build_remap_packet,
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
    # Commit to persist
    commit = bytearray(32)
    commit[0:4] = [0x07, 0x03, 0x08, 0x03]
    send_raw_bytes(commit)


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


STICK_MODES = {
    "native": 0x00,
    "mouse": 0x01,
    "keyboard": 0x02,
    "clone": 0x03
}

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

KEYBOARD_ZONE_INDEX = {
    "left": 0x10,
    "right": 0x11,
    "up": 0x12,
    "down": 0x13,
    "overlap_left": 0x18,
    "overlap_right": 0x19,
    "overlap_up": 0x1a,
    "overlap_down": 0x1b
}

KEYBOARD_ZONE_STRUCT = [0x00, 0x00, 0x01, 0x02, 0x02, 0x00]
KEYBOARD_OVERLAP_STRUCT = [0x00, 0x00, 0x01, 0x02, 0x01, 0x02]

DEFAULT_HID_SCANCODES = {
    "w": 0x1a, "a": 0x04, "s": 0x16, "d": 0x07,
    "up": 0x1a, "left": 0x04, "down": 0x16, "right": 0x07,
    "arrowup": 0x1a, "arrowleft": 0x04, "arrowdown": 0x16, "arrowright": 0x07
}


@dataclass
class KeyboardMapping:
    left: int = 0x04
    right: int = 0x07
    up: int = 0x1a
    down: int = 0x16
    overlap_left: int = 0x01
    overlap_right: int = 0x01
    overlap_up: int = 0x01
    overlap_down: int = 0x01
    left_outer: int = 0x00
    right_outer: int = 0x00
    up_outer: int = 0x00
    down_outer: int = 0x00


@dataclass
class GyroConfig:
    output_mode: str = "mouse"           # keyboard, right_stick, mouse, left_stick
    motion_mode: str = "aim"             # aim (joycon-style), tilt (wheel-style)
    axis_mode: str = "global"            # global, yaw, roll (only in aim mode)
    activate_button: int = 0x29          # C1 default
    activate_method: str = "hold"        # hold, press, always, off
    x_sensitivity: int = 50
    y_sensitivity: int = 50
    overlap_percent: int = 50            # keyboard mode overlap threshold
    deadzone_min: int = 0
    antideadzone_min: int = 0
    deadzone_max: int = 100
    antideadzone_max: int = 100
    curve_preset: str = "linear"
    curve_intensity: int = 50
    # Keyboard direction mappings: each is a target string (key:x, mouse:scroll_up, controller:lt, unbind)
    kb_up: str = "key:w"
    kb_down: str = "key:s"
    kb_left: str = "key:a"
    kb_right: str = "key:d"

    def __post_init__(self):
        self.output_mode = self.output_mode.lower() if isinstance(self.output_mode, str) else "mouse"
        self.motion_mode = self.motion_mode.lower() if isinstance(self.motion_mode, str) else "aim"
        self.axis_mode = self.axis_mode.lower() if isinstance(self.axis_mode, str) else "global"
        self.activate_method = self.activate_method.lower() if isinstance(self.activate_method, str) else "hold"
        self.x_sensitivity = max(0, min(100, self.x_sensitivity))
        self.y_sensitivity = max(0, min(100, self.y_sensitivity))
        self.overlap_percent = max(0, min(100, self.overlap_percent))
        self.deadzone_min = max(0, min(100, self.deadzone_min))
        self.antideadzone_min = max(0, min(100, self.antideadzone_min))
        self.deadzone_max = max(0, min(100, self.deadzone_max))
        self.antideadzone_max = max(0, min(100, self.antideadzone_max))
        self.curve_preset = self.curve_preset.lower().replace("_", "-")
        if self.curve_preset not in CURVE_PRESETS:
            self.curve_preset = "linear"
        self.curve_intensity = max(0, min(100, self.curve_intensity))


GYRO_OUTPUT_MODES = {"keyboard": 0x03, "right_stick": 0x01, "mouse": 0x00, "left_stick": 0x02}
GYRO_MOTION_MODES = {"aim": 0x00, "tilt": 0x01}
GYRO_METHODS = {"off": 0x00, "hold": 0x04, "press": 0x04, "always": 0x04}
GYRO_AXIS_MODES = {"global": 0x00, "yaw": 0x02, "roll": 0x01}


@dataclass
class StickConfig:
    stick_id: int = 0
    mode: str = "native"
    x_sensitivity: int = 50
    y_sensitivity: int = 50
    overlap_percent: int = 50
    mouse_x_dpi: int = 50
    mouse_y_dpi: int = 50
    is_circle: bool = True
    deadzone_min: int = 5
    antideadzone_min: int = 0
    deadzone_max: int = 100
    antideadzone_max: int = 100
    curve_preset: str = "linear"
    curve_intensity: int = 50
    keyboard: KeyboardMapping = None

    def __post_init__(self):
        self.stick_id = max(0, min(1, self.stick_id))
        self.mode = self.mode.lower() if self.mode.lower() in STICK_MODES else "native"
        self.x_sensitivity = max(0, min(100, self.x_sensitivity))
        self.y_sensitivity = max(0, min(100, self.y_sensitivity))
        self.overlap_percent = max(0, min(100, self.overlap_percent))
        self.mouse_x_dpi = max(0, min(100, self.mouse_x_dpi))
        self.mouse_y_dpi = max(0, min(100, self.mouse_y_dpi))
        self.is_circle = bool(self.is_circle)
        self.deadzone_min = max(0, min(100, self.deadzone_min))
        self.antideadzone_min = max(0, min(100, self.antideadzone_min))
        self.deadzone_max = max(0, min(100, self.deadzone_max))
        self.antideadzone_max = max(0, min(100, self.antideadzone_max))
        self.curve_preset = self.curve_preset.lower().replace("_", "-")
        if self.curve_preset not in CURVE_PRESETS:
            self.curve_preset = "linear"
        self.curve_intensity = max(0, min(100, self.curve_intensity))
        if self.keyboard is None:
            self.keyboard = KeyboardMapping()
        elif not isinstance(self.keyboard, KeyboardMapping):
            kbd = self.keyboard
            self.keyboard = KeyboardMapping(
                left=kbd.get("left", 0x04),
                right=kbd.get("right", 0x07),
                up=kbd.get("up", 0x1a),
                down=kbd.get("down", 0x16),
                overlap_left=kbd.get("overlap_left", 1),
                overlap_right=kbd.get("overlap_right", 1),
                overlap_up=kbd.get("overlap_up", 1),
                overlap_down=kbd.get("overlap_down", 1),
                left_outer=kbd.get("left_outer", 0x00),
                right_outer=kbd.get("right_outer", 0x00),
                up_outer=kbd.get("up_outer", 0x00),
                down_outer=kbd.get("down_outer", 0x00)
            )


def build_targeting_packet(config: StickConfig) -> bytes:
    """Build Targeting & Mode Control packet (Header: 07 0f 02 03)."""
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x0f, 0x02, 0x03]
    packet[4] = config.stick_id & 0x01
    packet[5] = config.overlap_percent if config.mode == "keyboard" else config.x_sensitivity
    packet[6] = config.y_sensitivity
    packet[7] = 0x50
    packet[8:10] = [0x00, 0x00]
    packet[10] = STICK_MODES.get(config.mode, 0x00)
    packet[11] = 0x01
    packet[12] = config.mouse_x_dpi if config.mode == "mouse" else 0x00
    packet[13] = config.mouse_y_dpi if config.mode == "mouse" else 0x00
    return bytes(packet)


def build_geometry_packet(config: StickConfig) -> bytes:
    """Build Geometry Curve packet (Header: 07 18 02 01)."""
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x18, 0x02, 0x01]

    if config.stick_id == 1:
        packet[4:11] = [0x01, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00]
    else:
        packet[4:11] = [0x00] * 7

    packet[11] = 0x01 if config.is_circle else 0x00
    packet[12] = 0x32
    packet[13] = config.deadzone_min
    packet[14] = config.antideadzone_min

    preset = CURVE_PRESETS.get(config.curve_preset, CURVE_PRESETS["linear"])
    packet[15:21] = preset["coords"]
    packet[21] = config.deadzone_max
    packet[22] = config.antideadzone_max
    packet[23] = preset["curve_type"]
    packet[24] = config.curve_intensity
    return bytes(packet)


def build_keyboard_packet(zone_index: int, struct: List[int], scancode: int) -> bytes:
    """Build Keyboard Directional Remapping packet (Header: 07 13 05 01)."""
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x13, 0x05, 0x01]
    packet[4:10] = [0x00] * 6
    packet[10] = zone_index
    packet[11:17] = struct
    if isinstance(scancode, str):
        sc = scancode.strip().lower()
        try:
            if sc.startswith("0x"):
                scancode = int(sc, 16)
            else:
                try:
                    scancode = int(sc, 16)
                except ValueError:
                    scancode = int(sc, 10)
        except ValueError:
            scancode = 0
    packet[17] = scancode & 0xFF
    return bytes(packet)


def _build_keyboard_sequence(config: StickConfig) -> List[bytes]:
    """Build 8-packet keyboard directional sequence for a stick."""
    packets = []
    kbd = config.keyboard
    zones = [
        # Inner ring (partial tilt) - indices 0x10-0x13
        (KEYBOARD_ZONE_INDEX["left"], KEYBOARD_ZONE_STRUCT, kbd.left),
        (KEYBOARD_ZONE_INDEX["right"], KEYBOARD_ZONE_STRUCT, kbd.right),
        (KEYBOARD_ZONE_INDEX["up"], KEYBOARD_ZONE_STRUCT, kbd.up),
        (KEYBOARD_ZONE_INDEX["down"], KEYBOARD_ZONE_STRUCT, kbd.down),
        # Outer ring (full tilt asymmetric modifiers) - indices 0x18-0x1b
        (KEYBOARD_ZONE_INDEX["overlap_left"], KEYBOARD_OVERLAP_STRUCT, kbd.left_outer),
        (KEYBOARD_ZONE_INDEX["overlap_right"], KEYBOARD_OVERLAP_STRUCT, kbd.right_outer),
        (KEYBOARD_ZONE_INDEX["overlap_up"], KEYBOARD_OVERLAP_STRUCT, kbd.up_outer),
        (KEYBOARD_ZONE_INDEX["overlap_down"], KEYBOARD_OVERLAP_STRUCT, kbd.down_outer),
    ]
    for zone_idx, struct, scancode in zones:
        packets.append(build_keyboard_packet(zone_idx, struct, scancode))
    return packets


def generate_hardware_stream(left_cfg: StickConfig, right_cfg: StickConfig) -> List[bytes]:
    """
    Master builder: compiles full burst sequence based on mode requirements.
    Standard Analog: 5 packets [targetL, geomL, targetR, geomR, commit]
    Keyboard Mode: 13 packets [targetL, geomL, 8x kbd, targetR, geomR, commit]
    """
    left_cfg.stick_id = 0
    right_cfg.stick_id = 1

    p0 = build_targeting_packet(left_cfg)
    p1 = build_geometry_packet(left_cfg)

    if left_cfg.mode == "keyboard":
        kbd_seq = _build_keyboard_sequence(left_cfg)
        p2 = build_targeting_packet(right_cfg)
        p3 = build_geometry_packet(right_cfg)
        commit = bytes.fromhex("0703080300000000000000000000000000000000000000000000000000000000")
        return [p0, p1] + kbd_seq + [p2, p3, commit]

    p2 = build_targeting_packet(right_cfg)
    p3 = build_geometry_packet(right_cfg)
    p4 = bytes.fromhex("0703080300000000000000000000000000000000000000000000000000000000")
    return [p0, p1, p2, p3, p4]


def set_stick_config(left_cfg: StickConfig, right_cfg: StickConfig):
    """Send full hardware stream to MCU."""
    for pkt in generate_hardware_stream(left_cfg, right_cfg):
        send_raw_bytes(pkt)


def test_stick_config_baseline():
    """Validate default native mode generates correct stream structure."""
    left = StickConfig(stick_id=0, mode="native")
    right = StickConfig(stick_id=1, mode="native")
    stream = generate_hardware_stream(left, right)
    assert len(stream) == 5
    assert stream[0][0:4] == b'\x07\x0f\x02\x03'
    assert stream[0][4] == 0x00
    assert stream[0][10] == 0x00
    assert stream[1][0:4] == b'\x07\x18\x02\x01'
    assert stream[1][15:21] == b'\x14\x10\x35\x32\x55\x54'
    assert stream[2][0:4] == b'\x07\x0f\x02\x03'
    assert stream[2][4] == 0x01
    assert stream[3][0:4] == b'\x07\x18\x02\x01'
    assert stream[3][23] == 0x00
    assert stream[4][0:4] == b'\x07\x03\x08\x03'


def test_stick_config_mouse_mode():
    """Validate mouse emulation mode targeting packets."""
    left = StickConfig(stick_id=0, mode="mouse", mouse_x_dpi=75, mouse_y_dpi=60)
    pkt = build_targeting_packet(left)
    assert pkt[0:4] == b'\x07\x0f\x02\x03'
    assert pkt[4] == 0x00
    assert pkt[10] == 0x01
    assert pkt[12] == 75
    assert pkt[13] == 60
    assert pkt[5] == 50
    assert pkt[6] == 50


def test_stick_config_keyboard_mode():
    """Validate keyboard mode generates 13-packet stream with 8 scancode packets."""
    left = StickConfig(stick_id=0, mode="keyboard", keyboard=KeyboardMapping(up=0x1a, left=0x04))
    right = StickConfig(stick_id=1, mode="native")
    stream = generate_hardware_stream(left, right)
    assert len(stream) == 13
    assert stream[0][10] == 0x02
    assert stream[2][10] == 0x10
    assert stream[2][17] == 0x04
    assert stream[4][10] == 0x12
    assert stream[4][17] == 0x1a


def test_stick_config_clone_mode():
    """Validate clone mode."""
    left = StickConfig(stick_id=0, mode="clone")
    pkt = build_targeting_packet(left)
    assert pkt[10] == 0x03


def test_keyboard_mapping_custom_scancodes():
    """Validate custom scancodes in keyboard mode."""
    kbd = KeyboardMapping(left=0x50, right=0x4F, up=0x52, down=0x51)
    left = StickConfig(stick_id=0, mode="keyboard", keyboard=kbd)
    stream = generate_hardware_stream(left, StickConfig(stick_id=1))
    scancode_packets = stream[2:10]
    assert scancode_packets[0][17] == 0x50
    assert scancode_packets[1][17] == 0x4F
    assert scancode_packets[2][17] == 0x52
    assert scancode_packets[3][17] == 0x51


def test_asymmetric_macro_mapping():
    """Validate dual-stage asymmetric macro mapping (inner + outer scancodes per direction)."""
    kbd = KeyboardMapping(
        up=0x1a, down=0x16, left=0x04, right=0x07,
        up_outer=0xe1, down_outer=0xe0, left_outer=0x14, right_outer=0x08
    )
    left = StickConfig(stick_id=0, mode="keyboard", keyboard=kbd, overlap_percent=80)
    stream = generate_hardware_stream(left, StickConfig(stick_id=1))
    scancode_packets = stream[2:10]

    assert scancode_packets[0][10] == 0x10  # left inner
    assert scancode_packets[0][17] == 0x04  # A
    assert scancode_packets[1][10] == 0x11  # right inner
    assert scancode_packets[1][17] == 0x07  # D
    assert scancode_packets[2][10] == 0x12  # up inner
    assert scancode_packets[2][17] == 0x1a  # W
    assert scancode_packets[3][10] == 0x13  # down inner
    assert scancode_packets[3][17] == 0x16  # S

    assert scancode_packets[4][10] == 0x18  # left outer
    assert scancode_packets[4][17] == 0x14  # Q (left outer modifier)
    assert scancode_packets[5][10] == 0x19  # right outer
    assert scancode_packets[5][17] == 0x08  # E (right outer modifier)
    assert scancode_packets[6][10] == 0x1a  # up outer
    assert scancode_packets[6][17] == 0xe1  # left shift (up outer modifier)
    assert scancode_packets[7][10] == 0x1b  # down outer
    assert scancode_packets[7][17] == 0xe0  # left ctrl (down outer modifier)


def run_all_tests():
    test_stick_config_baseline()
    test_stick_config_mouse_mode()
    test_stick_config_keyboard_mode()
    test_stick_config_clone_mode()
    test_keyboard_mapping_custom_scancodes()
    test_asymmetric_macro_mapping()
    print("All StickConfig assertions passed.")


def set_rumble_level(left_pct: int, right_pct: int):
    """Set persistent grip rumble level (0-100%). Header: 07 09 06 01."""
    left = max(0, min(100, left_pct))
    right = max(0, min(100, right_pct))
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x09, 0x06, 0x01]
    packet[4] = left
    packet[5] = right
    send_raw_bytes(packet)
    # Commit
    commit = bytearray(32)
    commit[0:4] = [0x07, 0x03, 0x08, 0x03]
    send_raw_bytes(commit)


def fire_rumble(left_pct: int, right_pct: int, duration_ms: int = 500):
    """Activate grip rumble motors (0-100%). Header: 07 07 0a 04. Burst-fire."""
    import time
    left = max(0, min(100, left_pct))
    right = max(0, min(100, right_pct))
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x07, 0x0a, 0x04]
    packet[4] = left
    packet[5] = right
    deadline = time.time() + duration_ms / 1000.0
    while time.time() < deadline:
        send_raw_bytes(packet)
        time.sleep(0.025)
    packet[4] = 0
    packet[5] = 0
    send_raw_bytes(packet)


def read_rumble_level():
    """Read current grip rumble levels. Returns (left, right) in 0-100%."""
    fd = open_device()
    try:
        drain(fd)
        # No init needed for typed reads
        d = read_typed_register(fd, 0x09, 0x06, 0x02)
        if d and d[1] == 0x09 and d[2] == 0x06 and d[3] == 0x02:
            return (d[4], d[5])
    finally:
        os.close(fd)
    return (0, 0)


def read_lighting():
    """Read current lighting config. Returns (brightness, speed, mode)."""
    fd = open_device()
    try:
        drain(fd)
        d = read_typed_register(fd, 0x06, 0x07, 0x02)
        if d and d[1] == 0x06 and d[2] == 0x07 and d[3] == 0x02:
            return (d[4], d[5], d[6])
    finally:
        os.close(fd)
    return (0, 0, 0)


def read_stick_targeting(stick_id=0):
    """Read stick targeting/mode config. Returns raw bytes or None."""
    import time
    fd = open_device()
    try:
        drain(fd)
        cmd = bytes([0x07, 0x0f, 0x02, 0x04, stick_id & 1]) + b'\x00' * 27
        os.write(fd, cmd)
        time.sleep(0.05)
        d = read_response(fd)
        if d and d[1] == 0x0f and d[2] == 0x02 and d[3] == 0x04:
            return d
    finally:
        os.close(fd)
    return None


def read_stick_geometry(stick_id=0):
    """Read stick geometry/curve config. Returns raw bytes or None."""
    import time
    fd = open_device()
    try:
        drain(fd)
        if stick_id == 0:
            cmd = bytes([0x07, 0x18, 0x02, 0x02]) + b'\x00' * 28
        else:
            cmd = bytes([0x07, 0x18, 0x02, 0x02, 0x01, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00]) + b'\x00' * 21
        os.write(fd, cmd)
        time.sleep(0.05)
        d = read_response(fd)
        if d and d[1] == 0x18 and d[2] == 0x02 and d[3] == 0x02:
            return d
    finally:
        os.close(fd)
    return None


# Button source index → page 05 02 register mapping
_BUTTON_REGISTER_MAP = {
    0x24: 0x0d,  # L4
    0x25: 0x0e,  # R4
    0x26: 0x09,  # T1
    0x27: 0x0a,  # T2
    0x28: 0x0b,  # T3
    0x29: 0x1a,  # C1
    0x2a: 0x04,  # C2
    0x2b: 0x16,  # C3
    0x2c: 0x07,  # C4
}

_BUTTON_NAMES = {v: k for k, v in CONTROLLER_SOURCE.items()}


def read_remaps():
    """Read all button remappings. Returns dict {button_name: raw_value_byte}."""
    fd = open_device()
    try:
        drain(fd)
        init_session(fd)
        remaps = {}
        for btn_idx, reg in _BUTTON_REGISTER_MAP.items():
            d = read_page_register(fd, 0x05, 0x05, reg)
            if d and d[1] == 0x13:
                val = d[4]  # scancode or target button index
                if val != 0:
                    name = _BUTTON_NAMES.get(btn_idx, f"btn_{btn_idx:#04x}")
                    remaps[name] = val
        return remaps
    finally:
        os.close(fd)


def read_color():
    """Read current color config. Returns (hue, saturation, lightness)."""
    fd = open_device()
    try:
        drain(fd)
        d = read_typed_register(fd, 0x10, 0x07, 0x04)
        if d and d[1] == 0x10 and d[2] == 0x07 and d[3] == 0x04:
            return (d[5], d[6], d[7])
    finally:
        os.close(fd)
    return (0, 0, 0)


def read_state():
    """Read full controller state and return as dict."""
    import os  # ensure os is available in scope
    state = {}

    fd = open_device()
    try:
        drain(fd)
        init_session(fd)

        # Read page 05 02 (main config page, 46 registers)
        page0502 = {}
        for off in range(0x2e):
            d = read_page_register(fd, 0x05, 0x05, off)
            if d and d[1] == 0x13:
                page0502[off] = bytes(d[4:])
        if page0502:
            state["page_05_02"] = {k: v.hex() for k, v in page0502.items()}

        # Read page 02 02 (stick config, 2 registers)
        page0202 = {}
        for off in range(2):
            d = read_page_register(fd, 0x05, 0x02, off)
            if d and d[1] == 0x13:
                page0202[off] = bytes(d[4:])
        if page0202:
            state["page_02_02"] = {k: v.hex() for k, v in page0202.items()}

    finally:
        os.close(fd)

    # Read typed registers (no init needed)
    rumble = read_rumble_level()
    lighting = read_lighting()
    color = read_color()

    state["rumble"] = {"left": rumble[0], "right": rumble[1]}
    state["lighting"] = {"brightness": lighting[0], "speed": lighting[1], "mode": lighting[2]}
    state["color"] = {"hue": color[0], "saturation": color[1], "lightness": color[2]}

    # Read sticks
    for sid, name in [(0, "left"), (1, "right")]:
        t = read_stick_targeting(sid)
        g = read_stick_geometry(sid)
        stick = {}
        if t:
            stick["mode"] = t[10]
            stick["x_sensitivity"] = t[5]
            stick["y_sensitivity"] = t[6]
            stick["mouse_x_dpi"] = t[12]
            stick["mouse_y_dpi"] = t[13]
        if g:
            stick["is_circle"] = bool(g[11])
            stick["deadzone_min"] = g[13]
            stick["antideadzone_min"] = g[14]
            stick["deadzone_max"] = g[21]
            stick["antideadzone_max"] = g[22]
            stick["curve_type"] = g[23]
            stick["curve_intensity"] = g[24]
            stick["curve_coords"] = list(g[15:21])
        if stick:
            state[f"stick_{name}"] = stick

    return state



def build_gyro_geometry(config: GyroConfig) -> bytes:
    """Build gyro geometry/curve packet (Header: 07 16 04 01)."""
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x16, 0x04, 0x01]
    packet[4:10] = [0x00] * 6        # reserved
    packet[10] = 0x32                 # fixed
    packet[11] = 0x00                 # reserved
    packet[12] = 0x00                 # reserved
    packet[13] = config.deadzone_min
    packet[14] = config.antideadzone_min
    preset = CURVE_PRESETS.get(config.curve_preset, CURVE_PRESETS["linear"])
    packet[15:21] = preset["coords"]
    packet[21] = config.deadzone_max
    packet[22] = config.antideadzone_max
    packet[23] = preset["curve_type"]
    packet[24] = config.curve_intensity
    return bytes(packet)


# Gyro keyboard direction zones (from pcap)
GYRO_KB_ZONES = {"left": 0x20, "right": 0x21, "up": 0x22, "down": 0x23}


def build_gyro_keyboard_packets(config: GyroConfig) -> list:
    """Build 4 keyboard direction remap packets for gyro keyboard mode."""
    packets = []
    directions = [
        ("up", config.kb_up),
        ("down", config.kb_down),
        ("left", config.kb_left),
        ("right", config.kb_right),
    ]
    for direction, target in directions:
        zone = GYRO_KB_ZONES[direction]
        pkt = resolve_gyro_direction_packet(zone, target)
        if pkt:
            packets.append(pkt)
    return packets


def resolve_gyro_direction_packet(zone: int, target: str) -> bytes | None:
    """Build a gyro keyboard direction packet (07 13 05 01) from a target string."""
    target = target.lower().strip()
    if target == "unbind" or target == "none":
        return bytes([0x07, 0x13, 0x05, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, zone, 0x00, 0x00, 0x01, 0x00, 0x00]) + b"\x00" * 16

    report_type = REPORT_KEYBOARD       # default
    payload = bytearray(16)

    if target.startswith("key:") or target.startswith("keyboard:"):
        key_name = target.split(":", 1)[1].strip()
        if key_name in KEYBOARD_USAGE:
            usage = KEYBOARD_USAGE[key_name]
            report_type = REPORT_KEYBOARD
            payload = bytes([0x00, usage]) + b"\x00" * 14
        else:
            return None
    elif target.startswith("controller:") or target.startswith("btn:"):
        btn_name = target.split(":", 1)[1].strip()
        if btn_name in CONTROLLER_BUTTON:
            report_type = REPORT_CONTROLLER
            payload = bytes([CONTROLLER_BUTTON[btn_name]]) + b"\x00" * 15
        else:
            return None
    elif target.startswith("mouse:"):
        mouse_name = target.split(":", 1)[1].strip()
        if mouse_name in MOUSE_BUTTON:
            report_type = REPORT_MOUSE
            payload = bytes([0x00, 0x00, 0x00, MOUSE_BUTTON[mouse_name]]) + b"\x00" * 12
        elif mouse_name in MOUSE_SCROLL:
            report_type = REPORT_MOUSE
            payload = bytes([0x00, 0x00, MOUSE_SCROLL[mouse_name], 0x00]) + b"\x00" * 12
        else:
            return None
    else:
        # Try direct key name
        if target in KEYBOARD_USAGE:
            report_type = REPORT_KEYBOARD
            payload = bytes([0x00, KEYBOARD_USAGE[target]]) + b"\x00" * 14
        elif target in CONTROLLER_BUTTON:
            report_type = REPORT_CONTROLLER
            payload = bytes([CONTROLLER_BUTTON[target]]) + b"\x00" * 15
        else:
            return None

    return build_remap_packet(zone, report_type, payload)


def build_gyro_targeting(config: GyroConfig) -> bytes:
    """Build gyro mode/targeting packet (Header: 07 0e 04 03).
    
    Layout A (keyboard mode): byte 6 = output mode directly (0x03)
    Layout B (mouse/stick): byte 6 = method, byte 8 = output mode
    """
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x0e, 0x04, 0x03]
    if config.output_mode == "keyboard":
        packet[4] = config.overlap_percent                    # overlap
        packet[6] = 0x03                                      # keyboard output (Layout A)
        packet[8] = 0x00
    else:
        packet[4] = config.x_sensitivity
        packet[6] = GYRO_METHODS.get(config.activate_method, 0)  # method (Layout B)
        packet[8] = GYRO_OUTPUT_MODES.get(config.output_mode, 0)  # output (Layout B)
    packet[5] = config.y_sensitivity
    packet[7] = GYRO_MOTION_MODES.get(config.motion_mode, 0)
    packet[9] = config.activate_button
    packet[10] = GYRO_AXIS_MODES.get(config.axis_mode, 0)
    packet[11] = 0x32
    packet[12] = 0x32
    return bytes(packet)


def set_gyro_config(config: GyroConfig):
    """Send gyro geometry + targeting + keyboard packets + commit."""
    import time
    send_raw_bytes(build_gyro_geometry(config))
    time.sleep(0.03)
    send_raw_bytes(build_gyro_targeting(config))
    time.sleep(0.03)
    if config.output_mode == "keyboard":
        for pkt in build_gyro_keyboard_packets(config):
            send_raw_bytes(pkt)
            time.sleep(0.03)
    commit = bytearray(32)
    commit[0:4] = [0x07, 0x03, 0x08, 0x03]
    send_raw_bytes(commit)


def read_gyro_geometry() -> None | bytes:
    """Read gyro geometry/curve config. Returns raw bytes or None. Header: 07 0e 04 02."""
    import time
    fd = open_device()
    try:
        drain(fd)
        cmd = bytes([0x07, 0x0e, 0x04, 0x02]) + b'\x00' * 28
        os.write(fd, cmd)
        time.sleep(0.05)
        d = read_response(fd)
        if d and d[1] == 0x16 and d[2] == 0x04 and d[3] == 0x02:
            return d
    finally:
        os.close(fd)
    return None


def read_gyro_targeting() -> None | bytes:
    """Read gyro mode/targeting config. Returns raw bytes or None. Header: 07 0e 04 04."""
    import time
    fd = open_device()
    try:
        drain(fd)
        cmd = bytes([0x07, 0x0e, 0x04, 0x04]) + b'\x00' * 28
        os.write(fd, cmd)
        time.sleep(0.05)
        d = read_response(fd)
        if d and d[1] == 0x0e and d[2] == 0x04 and d[3] == 0x04:
            return d
    finally:
        os.close(fd)
    return None


if __name__ == "__main__":
    run_all_tests()

