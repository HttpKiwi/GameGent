# core/stick.py — stick config, curve presets, packet builders
from dataclasses import dataclass
from typing import List
from .transport import send_raw_bytes

CURVE_PRESETS = {
    "linear":  {"coords": [0x14, 0x10, 0x35, 0x32, 0x55, 0x54], "curve_type": 0x00},
    "expo":    {"coords": [0x1b, 0x17, 0x35, 0x32, 0x4e, 0x4d], "curve_type": 0x01},
    "s-curve": {"coords": [0x0e, 0x1e, 0x2c, 0x32, 0x4a, 0x46], "curve_type": 0x02},
}

STICK_MODES = {"native": 0x00, "mouse": 0x01, "wheel": 0x02, "clone": 0x03}

KEYBOARD_ZONE_INDEX = {
    "left": 0x10, "right": 0x11, "up": 0x12, "down": 0x13,
    "overlap_left": 0x18, "overlap_right": 0x19,
    "overlap_up": 0x1a, "overlap_down": 0x1b,
}

KEYBOARD_ZONE_STRUCT = [0x00, 0x00, 0x01, 0x02, 0x02, 0x00]
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
    x_sensitivity: int = 50
    y_sensitivity: int = 50
    overlap_percent: int = 50
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
        self.x_sensitivity = max(0, min(100, self.x_sensitivity))
        self.y_sensitivity = max(0, min(100, self.y_sensitivity))
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
    packet[5] = config.overlap_percent if config.mode == "wheel" else config.x_sensitivity
    packet[6] = 0x28
    packet[7] = 0x50
    packet[8:10] = [0x00, 0x00]
    packet[10] = STICK_MODES.get(config.mode, 0x00)
    packet[11] = 0x01
    packet[12] = config.mouse_dpi if config.mode == "mouse" else 0x00
    packet[13] = 0x00
    print(f"[DEBUG] build_targeting: mode={config.mode} x_sens={config.x_sensitivity} y_sens={config.y_sensitivity} dpi={config.mouse_dpi}")
    return bytes(packet)


def build_geometry_packet(config: StickConfig) -> bytes:
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x18, 0x02, 0x01]
    if config.stick_id == 1:
        packet[4:11] = [0x01, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00]
    else:
        packet[4:11] = [0x00] * 7
    packet[11] = 0x01 if config.is_circle else 0x00
    packet[12] = config.y_sensitivity
    packet[13] = config.deadzone_min
    packet[14] = config.antideadzone_min
    preset = CURVE_PRESETS.get(config.curve_preset, CURVE_PRESETS["linear"])
    packet[15:21] = preset["coords"]
    packet[21] = config.deadzone_max
    packet[22] = config.antideadzone_max
    packet[23] = preset["curve_type"]
    packet[24] = config.curve_intensity
    print(f"[DEBUG] build_geometry_packet: stick_id={config.stick_id} y_sensitivity={config.y_sensitivity} -> byte12={config.y_sensitivity}")
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
        packets.append(build_keyboard_packet(zone_idx, struct, scancode))
    return packets


def generate_hardware_stream(left_cfg: StickConfig, right_cfg: StickConfig) -> List[bytes]:
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
    for pkt in generate_hardware_stream(left_cfg, right_cfg):
        send_raw_bytes(pkt)
