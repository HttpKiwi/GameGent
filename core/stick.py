# core/stick.py — stick config, curve presets, packet builders
from dataclasses import dataclass
from typing import List
from .hid_keycodes import KEYBOARD_USAGE, REPORT_UNBIND, build_remap_packet
from .targets import encode_target
from .transport import send_raw_bytes

_USAGE_TO_KEY = {v: k for k, v in KEYBOARD_USAGE.items()}

# Curve types (SAPJoyUniCurve): 0 linear, 1 concave/convex ("expo"), 2 S / inverse-S, 3 custom.
# The official app writes (type, curvature, 3 points); for types 0-2 the points keep their
# default values and only type + curvature shape the response, for "custom" they are the curve.
DEFAULT_CURVE_POINTS = [(30, 30), (50, 50), (70, 70)]
CURVE_PRESETS = {
    "linear":  {"curve_type": 0x00},
    "expo":    {"curve_type": 0x01},
    "s-curve": {"curve_type": 0x02},
    "custom":  {"curve_type": 0x03},
}


def curve_coords(preset: str, points=None) -> list[int]:
    """The 6 curve bytes (3 x/y points) for a preset; custom uses `points` if given."""
    pts = points if preset == "custom" and points else DEFAULT_CURVE_POINTS
    if len(pts) != 3:
        raise ValueError("A custom curve needs exactly 3 points")
    return [max(0, min(100, int(v))) for pt in pts for v in pt]


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



@dataclass
class KeyboardMapping:
    """Wheel-mode targets: inner zones (up/down/left/right) and the outer ring (`outline`).

    Values are mapping targets ("key:w", "key:ctrl+a", "mouse:left_click", "controller:a",
    "none"); ints are legacy HID key usage codes. `*_outer` override one outer zone.
    """
    left: int | str = 0x04
    right: int | str = 0x07
    up: int | str = 0x1a
    down: int | str = 0x16
    outline: str = "key:left_shift"   # captured default for the outer ring
    left_outer: int | str = 0
    right_outer: int | str = 0
    up_outer: int | str = 0
    down_outer: int | str = 0
    # legacy fields, ignored
    overlap_left: int = 1
    overlap_right: int = 1
    overlap_up: int = 1
    overlap_down: int = 1


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
    curve_intensity: int = 100
    curve_points: list | None = None
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
            known = KeyboardMapping.__dataclass_fields__
            self.keyboard = KeyboardMapping(**{k: v for k, v in self.keyboard.items() if k in known})


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
    packet[15:21] = curve_coords(config.curve_preset, config.curve_points)
    packet[21] = config.deadzone_max
    packet[22] = config.antideadzone_max
    packet[23] = preset["curve_type"]
    packet[24] = config.curve_intensity
    return bytes(packet)


def _target(value) -> str:
    """Target string for a wheel entry; ints are legacy HID usage codes, 0/""/None = none."""
    if isinstance(value, int):
        name = _USAGE_TO_KEY.get(value) if value else None
        return f"key:{name}" if name else "none"
    return (value or "none").strip() or "none"


def build_zone_packet(zone_id: int, target: str) -> bytes:
    """SetKeyMapping for a stick/gyro wheel zone (a key whose source id is the zone)."""
    if target.lower() in ("none", "nc", "unbind"):
        return build_remap_packet(zone_id, REPORT_UNBIND, bytes(16))
    report, payload = encode_target(target)
    return build_remap_packet(zone_id, report, payload)


def _build_keyboard_sequence(config: StickConfig) -> List[bytes]:
    kbd = config.keyboard
    off = RIGHT_STICK_ZONE_OFFSET if config.stick_id == 1 else 0
    inner = {"left": kbd.left, "right": kbd.right, "up": kbd.up, "down": kbd.down}
    outer = {"left": kbd.left_outer, "right": kbd.right_outer, "up": kbd.up_outer, "down": kbd.down_outer}
    packets = []
    for name, value in inner.items():
        packets.append(build_zone_packet(KEYBOARD_ZONE_INDEX[name] + off, _target(value)))
    for name, value in outer.items():
        target = _target(value) if value else _target(kbd.outline)
        packets.append(build_zone_packet(KEYBOARD_ZONE_INDEX["overlap_" + name] + off, target))
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
