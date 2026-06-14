# core/gyro.py — gyro/motion aim config, packet builders, read/write
import os
from dataclasses import dataclass
from .transport import send_raw_bytes, open_device, read_response, drain
from .hid_keycodes import (
    KEYBOARD_USAGE, MOUSE_BUTTON, MOUSE_SCROLL,
    CONTROLLER_BUTTON,
    REPORT_KEYBOARD, REPORT_MOUSE, REPORT_CONTROLLER,
    build_remap_packet,
)
from .stick import CURVE_PRESETS


GYRO_OUTPUT_MODES = {"left_stick": 0x01, "right_stick": 0x02, "keyboard": 0x03, "mouse": 0x04}
GYRO_MOTION_MODES = {"aim": 0x00, "tilt": 0x01}
GYRO_METHODS = {"off": 0x00, "press": 0x01, "hold": 0x02, "always": 0x03}
GYRO_AXIS_MODES = {"global": 0x02, "yaw": 0x00, "roll": 0x01}
GYRO_KB_ZONES = {"left": 0x20, "right": 0x21, "up": 0x22, "down": 0x23}


@dataclass
class GyroConfig:
    output_mode: str = "mouse"
    motion_mode: str = "aim"
    axis_mode: str = "yaw"
    activate_button: int = 0x29
    activate_method: str = "hold"
    invert_x: bool = False
    invert_y: bool = False
    x_sensitivity: int = 50
    y_sensitivity: int = 50
    overlap_percent: int = 50
    deadzone_min: int = 0
    antideadzone_min: int = 0
    deadzone_max: int = 100
    antideadzone_max: int = 100
    curve_preset: str = "linear"
    curve_intensity: int = 50
    kb_up: str = "key:w"
    kb_down: str = "key:s"
    kb_left: str = "key:a"
    kb_right: str = "key:d"

    def __post_init__(self):
        self.output_mode = self.output_mode.lower() if isinstance(self.output_mode, str) else "mouse"
        self.motion_mode = self.motion_mode.lower() if isinstance(self.motion_mode, str) else "aim"
        self.axis_mode = self.axis_mode.lower() if isinstance(self.axis_mode, str) else "yaw"
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


def build_gyro_geometry(config: GyroConfig) -> bytes:
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x16, 0x04, 0x01]
    packet[4:10] = [0x00] * 6
    packet[10] = config.x_sensitivity
    packet[11] = config.deadzone_min
    packet[12] = config.antideadzone_min
    preset = CURVE_PRESETS.get(config.curve_preset, CURVE_PRESETS["linear"])
    packet[13:19] = preset["coords"]
    packet[19] = config.deadzone_max
    packet[20] = config.antideadzone_max
    packet[21] = preset["curve_type"]
    packet[22] = config.curve_intensity
    return bytes(packet)


def build_gyro_targeting(config: GyroConfig) -> bytes:
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x0e, 0x04, 0x03]
    packet[4] = config.x_sensitivity
    packet[5] = config.y_sensitivity
    packet[6] = GYRO_OUTPUT_MODES.get(config.output_mode, 0)
    packet[7] = GYRO_MOTION_MODES.get(config.motion_mode, 0)
    packet[8] = GYRO_AXIS_MODES.get(config.axis_mode, 0)
    packet[9] = config.activate_button
    packet[10] = GYRO_METHODS.get(config.activate_method, 0)
    packet[11] = 0x32
    packet[12] = 0x32
    packet[13] = 0x01 if config.invert_x else 0x00
    packet[14] = 0x01 if config.invert_y else 0x00
    return bytes(packet)


def resolve_gyro_direction_packet(zone: int, target: str) -> bytes | None:
    target = target.lower().strip()
    if target in ("unbind", "none"):
        return bytes([0x07, 0x13, 0x05, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, zone, 0x00, 0x00, 0x01, 0x00, 0x00]) + b"\x00" * 16

    report_type = REPORT_KEYBOARD
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
        if target in KEYBOARD_USAGE:
            report_type = REPORT_KEYBOARD
            payload = bytes([0x00, KEYBOARD_USAGE[target]]) + b"\x00" * 14
        elif target in CONTROLLER_BUTTON:
            report_type = REPORT_CONTROLLER
            payload = bytes([CONTROLLER_BUTTON[target]]) + b"\x00" * 15
        else:
            return None

    return build_remap_packet(zone, report_type, payload)


def build_gyro_keyboard_packets(config: GyroConfig) -> list:
    packets = []
    directions = [("up", config.kb_up), ("down", config.kb_down), ("left", config.kb_left), ("right", config.kb_right)]
    for direction, target in directions:
        zone = GYRO_KB_ZONES[direction]
        pkt = resolve_gyro_direction_packet(zone, target)
        if pkt:
            packets.append(pkt)
    return packets


def set_gyro_config(config: GyroConfig):
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
    import time
    fd = open_device()
    try:
        drain(fd)
        cmd = bytes([0x07, 0x0e, 0x04, 0x02]) + b"\x00" * 28
        os.write(fd, cmd)
        time.sleep(0.05)
        d = read_response(fd)
        if d and d[1] == 0x16 and d[2] == 0x04 and d[3] == 0x02:
            return d
    finally:
        os.close(fd)
    return None


def read_gyro_targeting() -> None | bytes:
    import time
    fd = open_device()
    try:
        drain(fd)
        cmd = bytes([0x07, 0x0e, 0x04, 0x04]) + b"\x00" * 28
        os.write(fd, cmd)
        time.sleep(0.05)
        d = read_response(fd)
        if d and d[1] == 0x0e and d[2] == 0x04 and d[3] == 0x04:
            return d
    finally:
        os.close(fd)
    return None
