# core/trigger.py — trigger config (deadzones, hair trigger, curves)
from dataclasses import dataclass
from .transport import send_raw_bytes
from .stick import CURVE_PRESETS


@dataclass
class TriggerConfig:
    trigger_id: int = 0
    hair_mode: str | None = "off"
    hair_trigger_begin: int | None = None   # None = use trigger default (10 for left, 20 for right)
    hair_trigger_end: int | None = None     # None = use trigger default (30 for left, 5 for right)
    deadzone_begin: int | None = 0
    deadzone_end: int | None = 100
    antideadzone_begin: int | None = 0
    antideadzone_end: int | None = 100
    curve_preset: str | None = "linear"
    curve_intensity: int | None = 50

    def __post_init__(self):
        self.trigger_id = max(0, min(1, self.trigger_id or 0))
        self.hair_mode = (self.hair_mode or "off").lower()
        self.deadzone_begin = max(0, min(100, self.deadzone_begin or 0))
        self.deadzone_end = max(0, min(100, self.deadzone_end or 100))
        self.antideadzone_begin = max(0, min(100, self.antideadzone_begin or 0))
        self.antideadzone_end = max(0, min(100, self.antideadzone_end or 100))
        self.curve_preset = (self.curve_preset or "linear").lower().replace("_", "-")
        if self.curve_preset not in CURVE_PRESETS:
            self.curve_preset = "linear"
        self.curve_intensity = max(0, min(100, self.curve_intensity or 50))
        if self.hair_trigger_begin is not None:
            self.hair_trigger_begin = max(0, min(100, self.hair_trigger_begin))
        if self.hair_trigger_end is not None:
            self.hair_trigger_end = max(0, min(100, self.hair_trigger_end))


HAIR_MODES = {"off": 0x00, "adaptive": 0x01, "fixed": 0x02}


def build_trigger_packet(config: TriggerConfig) -> bytes:
    """Build trigger config packet (Header: 07 13 03 01)."""
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x13, 0x03, 0x01]
    packet[4] = config.trigger_id & 1
    packet[5] = HAIR_MODES.get(config.hair_mode, 0)

    # Hair trigger begin/end (default per trigger)
    defaults = {0: (0x0a, 0x1e), 1: (0x14, 0x05)}
    c6, c7 = defaults.get(config.trigger_id, (0x0a, 0x1e))
    packet[6] = config.hair_trigger_begin if config.hair_trigger_begin is not None else c6
    packet[7] = config.hair_trigger_end if config.hair_trigger_end is not None else c7

    packet[8] = config.deadzone_begin
    packet[9] = config.antideadzone_begin

    preset = CURVE_PRESETS.get(config.curve_preset, CURVE_PRESETS["linear"])
    packet[10:16] = preset["coords"]

    packet[16] = config.deadzone_end
    packet[17] = config.antideadzone_end
    packet[18] = preset["curve_type"]
    packet[19] = config.curve_intensity
    return bytes(packet)


def set_trigger_config(left: TriggerConfig, right: TriggerConfig):
    """Send both trigger configs + commit."""
    import time
    left.trigger_id = 0
    right.trigger_id = 1
    send_raw_bytes(build_trigger_packet(left))
    time.sleep(0.03)
    send_raw_bytes(build_trigger_packet(right))
    time.sleep(0.03)
    commit = bytearray(32)
    commit[0:4] = [0x07, 0x03, 0x08, 0x03]
    send_raw_bytes(commit)
