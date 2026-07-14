# core/transport.py
import os
import glob
import time
import fcntl

VENDOR_ID = "3537"
PRODUCT_ID = "103e"


def find_dongle_path():
    """Scans sysfs directory topology to locate the correct hidraw node"""
    for sysfs_path in glob.glob("/sys/class/hidraw/hidraw*"):
        try:
            real_path = os.path.realpath(sysfs_path)
            if f"{VENDOR_ID}:{PRODUCT_ID}" in real_path.lower():
                dev_name = os.path.basename(sysfs_path)
                return f"/dev/{dev_name}"
        except Exception:
            continue
    return None


def send_raw_bytes(payload):
    """Injects a 32-byte payload straight into the kernel"""
    device_path = find_dongle_path()
    if not device_path:
        raise FileNotFoundError("GameSir Dongle not found in system topologies.")

    if isinstance(payload, (bytes, bytearray)):
        payload = list(payload)

    padded_payload = payload + [0x00] * (32 - len(payload))

    fd = os.open(device_path, os.O_RDWR | os.O_NONBLOCK)
    try:
        os.write(fd, bytes(padded_payload))
    finally:
        os.close(fd)


def open_device():
    """Open persistent hidraw fd for read operations."""
    path = find_dongle_path()
    if not path:
        raise FileNotFoundError("GameSir Dongle not found.")
    fd = os.open(path, os.O_RDWR)
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    return fd


def drain(fd, max_reads=30):
    """Drain pending input reports."""
    for _ in range(max_reads):
        try:
            os.read(fd, 128)
        except (BlockingIOError, OSError):
            break


def send_cmd(fd, data):
    """Send 32-byte command and wait."""
    if len(data) < 32:
        data = bytes(data) + b'\x00' * (32 - len(data))
    os.write(fd, data)
    time.sleep(0.03)


def read_response(fd, timeout=0.5, header=None):
    """Read next HID input report with report ID 0x06.

    If header is set (e.g. bytes([0x13, 0x05, 0x02])), only return matching responses.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            d = os.read(fd, 128)
            if d[0] != 6:
                continue
            if header is not None:
                if len(d) < 1 + len(header) or d[1:1 + len(header)] != header:
                    continue
            elif not any(b != 0 for b in d[1:12]):
                continue
            return d
        except (BlockingIOError, OSError):
            time.sleep(0.01)
    return None


def init_session(fd):
    """Initialize config session: mode switch + 07 03 0a 01 x2."""
    send_cmd(fd, bytes([0x01, 0x00]))
    time.sleep(0.04)
    send_cmd(fd, bytes([0x07, 0x03, 0x0a, 0x01]) + b'\x00' * 28)
    time.sleep(0.03)
    send_cmd(fd, bytes([0x07, 0x03, 0x0a, 0x01]) + b'\x00' * 28)
    time.sleep(0.05)
    drain(fd)


def read_page_register(fd, class_byte, subtype, register=0):
    """Read a single register from a page: 07 [class] [subtype] 02 [reg_lo] [reg_hi]."""
    cmd = bytes([0x07, class_byte, subtype, 0x02, register & 0xFF, (register >> 8) & 0xFF])
    send_cmd(fd, cmd)
    time.sleep(0.04)
    return read_response(fd)


def read_button_remap_register(fd, button_index):
    """Read one button remap: 07 05 05 02 00 [button_index].

    GameSir uses a leading zero byte before the button index (not little-endian 16-bit).
    """
    cmd = bytes([0x07, 0x05, 0x05, 0x02, 0x00, button_index & 0xFF]) + b"\x00" * 26
    send_cmd(fd, cmd)
    time.sleep(0.04)
    return read_response(fd, header=bytes([0x13, 0x05, 0x02]))


def read_typed_register(fd, class_byte, subtype, param=0):
    """Read using feature-specific header: 07 [class] [subtype] [read_cmd] [param]."""
    cmd = bytes([0x07, class_byte, subtype, param])
    send_cmd(fd, cmd)
    time.sleep(0.04)
    return read_response(fd)
