"""Physical button state from the vendor state report (06 1a 0a 03 ...).

The XInput interface has no slot for L4/R4/T1-T3/C1-C4. After SetGamepadStateReport
(07 04 0a 02 [mode]) the dongle streams its own state frames on the config hidraw node:
mode 1 = physical switches before mapping, 2 = after mapping, 0 = off (default).
Verified on hardware (V0241221A): raw mode does not change what games see on XInput.

Frame bytes: 4-7 LX LY RX RY (128 = centre), 8-9 LT RT (0-255), 10-14 button bits,
15+ motion sensor data (ignored).
"""
from __future__ import annotations

import atexit
import os
import select
import signal
import threading
import time

from .transport import find_dongle_path, send_raw_bytes

HEADER = bytes([0x06, 0x1A, 0x0A, 0x03])

# byte -> button name per bit (GameSir names: view=back, menu=start, capture=screenshot)
BUTTON_BITS = {
    10: ["b", "a", "y", "x", "lb", "lt", "l3", "rb"],
    11: ["rt", "r3", "back", "start", "dpad_left", "dpad_right", "dpad_up", "dpad_down"],
    12: ["home", "screenshot", "m"],
    13: ["l4", "r4", "t1", "t2", "t3", "c1", "c2", "c3"],
    14: ["c4"],
}

MODE_OFF, MODE_RAW, MODE_MAPPED = 0, 1, 2
IDLE_STOP = 3.0   # stop (and switch reports off again) this long after the last poll
STALE = 1.0       # no frame for this long -> re-send the mode packet


def mode_packet(mode: int) -> bytes:
    """SetGamepadStateReport: 07 04 0a 02 [mode]."""
    return bytes([0x07, 0x04, 0x0A, 0x02, mode])


DISPLAY_DEADZONE = 0.08  # raw sticks rest a unit or two off-centre; don't report that as movement


def _axis(v: int) -> float:
    x = max(-1.0, min(1.0, (v - 128) / 127))
    return 0.0 if abs(x) < DISPLAY_DEADZONE else round(x, 2)


def decode_state_report(data: bytes) -> dict | None:
    """Decoded frame, or None if `data` is not a state report."""
    if len(data) < 15 or bytes(data[:4]) != HEADER:
        return None
    pressed = [
        name
        for byte, names in BUTTON_BITS.items()
        for bit, name in enumerate(names)
        if data[byte] >> bit & 1
    ]
    return {
        "pressed": pressed,
        "leftStick": {"x": _axis(data[4]), "y": _axis(data[5])},
        "rightStick": {"x": _axis(data[6]), "y": _axis(data[7])},
        "lt": round(data[8] / 255, 2),
        "rt": round(data[9] / 255, 2),
        "raw": bytes(data[:15]).hex(" "),  # byte 15+ is motion data
    }


class RawStateReader:
    """Background reader that keeps the dongle in raw mode only while it is being polled."""

    def __init__(self, open_fd=None, send_mode=None):
        self._open_fd = open_fd or self._open_state_fd
        self._send_mode = send_mode or (lambda mode: send_raw_bytes(mode_packet(mode)))
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._touched = 0.0
        self._state: dict | None = None
        self._state_time = 0.0

    @staticmethod
    def _open_state_fd():
        path = find_dongle_path()
        if not path:
            raise FileNotFoundError("GameSir Dongle not found")
        return os.open(path, os.O_RDONLY | os.O_NONBLOCK)

    def touch(self) -> None:
        """Called on every poll: starts the reader and keeps it alive for IDLE_STOP seconds."""
        with self._lock:
            self._touched = time.monotonic()
            if self._thread is None or not self._thread.is_alive():
                self._stop.clear()
                self._thread = threading.Thread(target=self._run, name="raw-state", daemon=True)
                self._thread.start()

    def snapshot(self) -> tuple[dict | None, float]:
        """(latest decoded frame, its age in seconds)."""
        with self._lock:
            if self._state is None:
                return None, float("inf")
            return self._state, time.monotonic() - self._state_time

    def stop(self) -> None:
        """Stop the thread and switch state reports off again."""
        self._stop.set()
        thread = self._thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=2)

    def _set_mode(self, mode: int) -> None:
        try:
            self._send_mode(mode)
        except Exception:  # dongle unplugged or busy; retried by the watchdog
            pass

    def _run(self) -> None:
        fd = None
        last_frame = 0.0
        last_mode_sent = 0.0
        try:
            while not self._stop.is_set() and time.monotonic() - self._touched < IDLE_STOP:
                now = time.monotonic()
                if fd is None:
                    try:
                        fd = self._open_fd()
                    except OSError:
                        time.sleep(0.5)
                        continue
                    last_frame = 0.0
                if now - last_frame > STALE and now - last_mode_sent > STALE:
                    self._set_mode(MODE_RAW)  # also covers reconnects and sleep
                    last_mode_sent = now
                if not select.select([fd], [], [], 0.1)[0]:
                    continue
                try:
                    data = os.read(fd, 128)
                except BlockingIOError:
                    continue
                except OSError:  # node vanished: reopen
                    os.close(fd)
                    fd = None
                    continue
                state = decode_state_report(data)
                if state:
                    last_frame = time.monotonic()
                    with self._lock:
                        self._state, self._state_time = state, last_frame
        finally:
            if fd is not None:
                os.close(fd)
            with self._lock:
                self._state = None
            self._set_mode(MODE_OFF)  # the power-up default; mode 2 would keep streaming


READER = RawStateReader()


def install_exit_hooks() -> None:
    """Switch reports off on normal exit and SIGTERM (call from the main thread)."""
    atexit.register(READER.stop)

    def _term(signum, _frame):
        READER.stop()
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)

    try:
        if signal.getsignal(signal.SIGTERM) is signal.SIG_DFL:
            signal.signal(signal.SIGTERM, _term)
    except ValueError:  # not the main thread
        pass


def vendor_gamepad_state() -> dict | None:
    """Gamepad state in the /api/gamepad shape from the vendor stream, or None to fall back."""
    if not find_dongle_path():
        return None
    READER.touch()
    state, age = READER.snapshot()
    if state is None or age > STALE:
        return None
    return {
        "connected": True,
        "id": "GameSir (vendor report)",
        "source": "vendor",
        "layout": "vendor",
        "pressed": state["pressed"],
        "leftStick": state["leftStick"],
        "rightStick": state["rightStick"],
        "lt": state["lt"],
        "rt": state["rt"],
        "axes": [],
        "buttons": [],
        "raw": state["raw"],
    }
