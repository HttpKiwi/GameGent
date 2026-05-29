# core/rumble.py — grip rumble set/fire/read
import os
from .transport import send_raw_bytes, open_device, read_typed_register, drain


def set_rumble_level(left_pct: int, right_pct: int):
    left = max(0, min(100, left_pct))
    right = max(0, min(100, right_pct))
    packet = bytearray(32)
    packet[0:4] = [0x07, 0x09, 0x06, 0x01]
    packet[4] = left
    packet[5] = right
    send_raw_bytes(packet)
    commit = bytearray(32)
    commit[0:4] = [0x07, 0x03, 0x08, 0x03]
    send_raw_bytes(commit)


def fire_rumble(left_pct: int, right_pct: int, duration_ms: int = 500):
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
    fd = open_device()
    try:
        drain(fd)
        d = read_typed_register(fd, 0x09, 0x06, 0x02)
        if d and d[1] == 0x09 and d[2] == 0x06 and d[3] == 0x02:
            return (d[4], d[5])
    finally:
        os.close(fd)
    return (0, 0)
