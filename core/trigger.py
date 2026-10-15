# core/trigger.py — trigger config (deadzones, hair trigger, curves)
from dataclasses import dataclass
from .transport import send_raw_bytes
from .stick import CURVE_PRESETS, curve_coords


@dataclass
class TriggerConfig:
    trigger_id: int = 0
    hair_mode: str | None = "off"
    hair_trigger_begin: int | None = None   # None = official default (10)
    hair_trigger_end: int | None = None     # None = official default (20)
    deadzone_begin: int | None = 0
    deadzone_end: int | None = 95       # official default
    antideadzone_begin: int | None = 0
    antideadzone_end: int | None = 100
    curve_preset: str | None = "linear"
    curve_intensity: int | None = 100
    curve_points: list | None = None

    def __post_init__(self):
        def pct(v, default):
            return max(0, min(100, default if v is None else v))

        self.trigger_id = max(0, min(1, self.trigger_id or 0))
        self.hair_mode = (self.hair_mode or "off").lower()
        self.deadzone_begin = pct(self.deadzone_begin, 0)
        self.deadzone_end = pct(self.deadzone_end, 95)
        self.antideadzone_begin = pct(self.antideadzone_begin, 0)
        self.antideadzone_end = pct(self.antideadzone_end, 100)
        self.curve_preset = (self.curve_preset or "linear").lower().replace("_", "-")
        if self.curve_preset not in CURVE_PRESETS:
            self.curve_preset = "linear"
        self.curve_intensity = pct(self.curve_intensity, 100)
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

    # Hair trigger begin/end; official defaults 10 / 20 for both triggers
    packet[6] = config.hair_trigger_begin if config.hair_trigger_begin is not None else 10
    packet[7] = config.hair_trigger_end if config.hair_trigger_end is not None else 20

    packet[8] = config.deadzone_begin
    packet[9] = config.antideadzone_begin

    preset = CURVE_PRESETS.get(config.curve_preset, CURVE_PRESETS["linear"])
    packet[10:16] = curve_coords(config.curve_preset, config.curve_points)

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
