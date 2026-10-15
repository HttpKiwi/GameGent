"""Battery, firmware and identity of the controller and its dongle (GetDeviceInfo / GetVersion)."""
from __future__ import annotations

from .transport import close_device, drain, open_device, read_reply, send_cmd

DEVICE_RX, DEVICE_DONGLE = 1, 2


def _firmware_version(b: bytes) -> str:
    """Controller firmware bytes (major, minor*10+patch) -> '2.0.6' (same as the app)."""
    return f"{b[0]}.{b[1] // 10}.{b[1] % 10}" if len(b) >= 2 else "0.0.0"


def parse_device_info(reply: bytes) -> dict:
    """GetDeviceInfo reply 06 0e 0a 01 [id][fw 2][mac 6][battery][type]."""
    battery = reply[13]
    return {
        "id": reply[4],
        "firmware": _firmware_version(reply[5:7]),
        "mac": ":".join(f"{b:02x}" for b in reply[7:13]),
        "charging": battery == 255,
        "battery": None if battery == 255 else min(battery, 100),
        "type": reply[14],
    }


def parse_version(reply: bytes) -> dict:
    """GetVersion reply 06 12 84 01 [device][engineer 3][protocol 3][firmware 4][hardware 3]."""
    return {
        "device": reply[4],
        "engineer": reply[5:8].hex(),
        "protocol": reply[8:11].hex(),
        "firmware": reply[11:15].hex().upper(),   # dongle: 0241221A -> V0241221A
        "hardware": reply[15:18].hex(),
    }


def read_device_info() -> dict:
    """Device info plus dongle version; one HID conversation."""
    fd = open_device()
    try:
        drain(fd)
        send_cmd(fd, bytes([0x07, 0x03, 0x0A, 0x01]))
        info = read_reply(fd, 0x0A, 0x01)
        if info is None:
            raise RuntimeError("No reply to GetDeviceInfo")
        out = parse_device_info(info)
        send_cmd(fd, bytes([0x07, 0x04, 0x84, 0x01, DEVICE_DONGLE]))
        ver = read_reply(fd, 0x84, 0x01)
        out["dongle"] = parse_version(ver) if ver else None
        return out
    finally:
        close_device(fd)
