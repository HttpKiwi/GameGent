# core/stick.py — stick config, curve presets, packet builders
from dataclasses import dataclass
from typing import List
from .transport import send_raw_bytes

CURVE_PRESETS = {
    "linear":  {"coords": [0x14, 0x10, 0x35, 0x32, 0x55, 0x54], "curve_type": 0x00},
    "expo":    {"coords": [0x1b, 0x17, 0x35, 0x32, 0x4e, 0x4d], "curve_type": 0x01},
    "s-curve": {"coords": [0x0e, 0x1e, 0x2c, 0x32, 0x4a, 0x46], "curve_type": 0x02},
}

# "clone" = StickMapping: output as the other stick
STICK_MODES = {"native": 0x00, "mouse": 0x01, "wheel": 0x02, "clone": 0x03}

SAVE_CONFIG_PAGE = bytes([0x07, 0x03, 0x08, 0x03]) + bytes(28)

# Wheel-mode key zones (SAPJoyUniKey): inner L/R/U/D, outer L/R/U/D. Right stick = left + 4.
KEYBOARD_ZONE_INDEX = {
    "left": 0x10, "right": 0x11, "up": 0x12, "down": 0x13,
    "overlap_left": 0x18, "overlap_right": 0x19,
    "overlap_up": 0x1a, "overlap_down": 0x1b,
}
RIGHT_STICK_ZONE_OFFSET = 4

KEYBOARD_ZONE_STRUCT = [0x00, 0x00, 0x01, 0x02, 0x02, 0x00]
# Outer ring with no key set: keyboard type, count 1, code0 = 0x02 (Left Shift modifier bit),
# the behaviour captured from the official app. With a key set it is sent like an inner zone.
KEYBOARD_OVERLAP_STRUCT = [0x00, 0x00, 0x01, 0x02, 0x01, 0x02]


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
class StickConfig:
    stick_id: int = 0
    mode: str = "native"
    axis_ratio: int = 50          # SetStickCurve b12: X/Y ratio, 50 = equal
    overlap_percent: int = 50     # SetStickMapping b5: cross/diagonal angle
    invert_x: bool = False
    invert_y: bool = False
    mouse_dpi: int = 50
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
        self.axis_ratio = max(0, min(100, self.axis_ratio))
        self.overlap_percent = max(0, min(100, self.overlap_percent))
        self.mouse_dpi = max(0, min(100, self.mouse_dpi))
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
                left=kbd.get("left", 0x04), right=kbd.get("right", 0x07),
                up=kbd.get("up", 0x1a), down=kbd.get("down", 0x16),
                overlap_left=kbd.get("overlap_left", 1), overlap_right=kbd.get("overlap_right", 1),
                overlap_up=kbd.get("overlap_up", 1), overlap_down=kbd.get("overlap_down", 1),
                left_outer=kbd.get("left_outer", 0x00), right_outer=kbd.get("right_outer", 0x00),
                up_outer=kbd.get("up_outer", 0x00), down_outer=kbd.get("down_outer", 0x00),
            )


def build_targeting_packet(config: StickConfig) -> bytes:
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x0f, 0x02, 0x03]
    packet[4] = config.stick_id & 0x01
    packet[5] = config.overlap_percent
    packet[6] = 0x28  # innerTriggerRange (app: always 40)
    packet[7] = 0x50  # outerTriggerRange (app: always 80)
    packet[8] = int(config.invert_x)
    packet[9] = int(config.invert_y)
    packet[10] = STICK_MODES.get(config.mode, 0x00)
    packet[11] = 0x01
    dpi = config.mouse_dpi if config.mode == "mouse" else 0x00
    packet[12] = dpi
    packet[13] = dpi
    packet[14] = int(config.invert_x)
    packet[15] = int(config.invert_y)
    return bytes(packet)


def build_geometry_packet(config: StickConfig) -> bytes:
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x18, 0x02, 0x01]
    if config.stick_id == 1:
        packet[4:11] = [0x01, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00]
    else:
        packet[4:11] = [0x00] * 7
    packet[11] = 0x01 if config.is_circle else 0x00
    packet[12] = config.axis_ratio
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
                try: scancode = int(sc, 16)
                except ValueError: scancode = int(sc, 10)
        except ValueError:
            scancode = 0
    packet[17] = scancode & 0xFF
    return bytes(packet)


def _build_keyboard_sequence(config: StickConfig) -> List[bytes]:
    packets = []
    kbd = config.keyboard
    off = RIGHT_STICK_ZONE_OFFSET if config.stick_id == 1 else 0
    zones = [
        (KEYBOARD_ZONE_INDEX["left"], KEYBOARD_ZONE_STRUCT, kbd.left),
        (KEYBOARD_ZONE_INDEX["right"], KEYBOARD_ZONE_STRUCT, kbd.right),
        (KEYBOARD_ZONE_INDEX["up"], KEYBOARD_ZONE_STRUCT, kbd.up),
        (KEYBOARD_ZONE_INDEX["down"], KEYBOARD_ZONE_STRUCT, kbd.down),
        (KEYBOARD_ZONE_INDEX["overlap_left"], KEYBOARD_OVERLAP_STRUCT, kbd.left_outer),
        (KEYBOARD_ZONE_INDEX["overlap_right"], KEYBOARD_OVERLAP_STRUCT, kbd.right_outer),
        (KEYBOARD_ZONE_INDEX["overlap_up"], KEYBOARD_OVERLAP_STRUCT, kbd.up_outer),
        (KEYBOARD_ZONE_INDEX["overlap_down"], KEYBOARD_OVERLAP_STRUCT, kbd.down_outer),
    ]
    for zone_idx, struct, scancode in zones:
        if struct is KEYBOARD_OVERLAP_STRUCT and scancode:
            struct = KEYBOARD_ZONE_STRUCT
        packets.append(build_keyboard_packet(zone_idx + off, struct, scancode))
    return packets


def generate_hardware_stream(left_cfg: StickConfig, right_cfg: StickConfig) -> List[bytes]:
    left_cfg.stick_id = 0
    right_cfg.stick_id = 1
    packets = []
    for cfg in (left_cfg, right_cfg):
        packets += [build_targeting_packet(cfg), build_geometry_packet(cfg)]
        if cfg.mode == "wheel":
            packets += _build_keyboard_sequence(cfg)
    packets.append(SAVE_CONFIG_PAGE)
    return packets


def set_stick_config(left_cfg: StickConfig, right_cfg: StickConfig):
    for pkt in generate_hardware_stream(left_cfg, right_cfg):
        send_raw_bytes(pkt)
