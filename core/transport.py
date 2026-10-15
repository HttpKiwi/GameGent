# core/transport.py
import os
import glob
import time
import fcntl
import threading

# One HID conversation at a time (Flask threads + game watcher share the fd).
# Re-entrant so a thread holding an open fd can still call send_raw_bytes.
_DEVICE_LOCK = threading.RLock()

VENDOR_ID = "3537"
# Wireless dongle and wired USB-C use the same protocol; the app lists both for the T3Pro.
PRODUCT_IDS = ("103e", "1050")
PRODUCT_ID = PRODUCT_IDS[0]


def _has_config_reports(sysfs_path: str) -> bool:
    """Config interface = report descriptor with report IDs 06 (input) and 07 (output)."""
    try:
        with open(os.path.join(sysfs_path, "device", "report_descriptor"), "rb") as f:
            desc = f.read()
    except OSError:
        return False
    return b"\x85\x06" in desc and b"\x85\x07" in desc


def find_dongle_path():
    """hidraw node of the controller (wireless dongle preferred, then wired) that carries the
    config reports; falls back to the first node of a matching device."""
    found = []
    for sysfs_path in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        real_path = os.path.realpath(sysfs_path).lower()
        for rank, pid in enumerate(PRODUCT_IDS):
            if f"{VENDOR_ID}:{pid}" in real_path:
                found.append((rank, not _has_config_reports(sysfs_path), sysfs_path))
    if not found:
        return None
    return "/dev/" + os.path.basename(min(found)[2])


class DeviceError(RuntimeError):
    """Device rejected a write (non-zero status) or never acknowledged it."""


def read_reply(fd, obj, op, timeout=0.5):
    """Next input report 06 [len] [obj] [op] …, skipping state reports; None on timeout.
    Match on obj/op only: the length byte differs between firmware versions."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            d = os.read(fd, 128)
        except (BlockingIOError, OSError):
            time.sleep(0.005)
            continue
        if len(d) > 4 and d[0] == 0x06 and d[2] == obj and d[3] == op:
            return d
    return None


def _wait_ack(fd, obj, op, timeout):
    """Status byte of the SET reply 06 04 [obj] [op] [status], or None on timeout."""
    reply = read_reply(fd, obj, op, timeout)
    return None if reply is None else reply[4]


def send_raw_bytes(payload, timeout=0.5):
    """Write one 32-byte report. Config writes (report 0x07) wait for the device's
    status reply (the official DLL also waits 500 ms) and raise DeviceError on failure."""
    device_path = find_dongle_path()
    if not device_path:
        raise FileNotFoundError("GameSir Dongle not found in system topologies.")

    packet = bytes(payload).ljust(32, b"\x00")

    with _DEVICE_LOCK:
        fd = os.open(device_path, os.O_RDWR | os.O_NONBLOCK)
        try:
            os.write(fd, packet)
            if packet[0] != 0x07:
                return
            status = _wait_ack(fd, packet[2], packet[3], timeout)
        finally:
            os.close(fd)
    if status is None:
        raise DeviceError(f"No reply to {packet[:4].hex(' ')} within {timeout}s")
    if status != 0:
        raise DeviceError(f"Device rejected {packet[:4].hex(' ')} with status 0x{status:02x}")


def open_device():
    """Open hidraw fd and take the device lock. Always pair with close_device(fd)."""
    path = find_dongle_path()
    if not path:
        raise FileNotFoundError("GameSir Dongle not found.")
    _DEVICE_LOCK.acquire()
    try:
        fd = os.open(path, os.O_RDWR)
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    except BaseException:
        _DEVICE_LOCK.release()
        raise
    return fd


def close_device(fd):
    try:
        os.close(fd)
    finally:
        _DEVICE_LOCK.release()


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
    """Unknown report-1 write, then GetDeviceInfo (07 03 0a 01) twice. Not a mode switch."""
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
