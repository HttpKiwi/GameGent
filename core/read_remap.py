# core/read_remap.py — read button remap configuration from hardware
import os

from .hid_keycodes import (
    CONTROLLER_BUTTON,
    CONTROLLER_SOURCE,
    KEYBOARD_USAGE,
    MOUSE_BUTTON,
    MOUSE_SCROLL,
    REPORT_CONTROLLER,
    REPORT_KEYBOARD,
    REPORT_MOUSE,
    REPORT_UNBIND,
)
from .transport import open_device, init_session, read_button_remap_register, drain

# Page gateway observed in GameSir app captures: OUT 07 05 05 02, IN 06 13 05 02
REMAP_RESPONSE_CLASS = 0x13
REMAP_RESPONSE_SUBTYPE = 0x05

# Native / no custom remap (seen on unmapped face buttons)
REPORT_NATIVE = bytes([0x14, 0x01])

REMAP_BUTTON_IDS = sorted(set(CONTROLLER_BUTTON.values()) | set(CONTROLLER_SOURCE.values()))

_USAGE_TO_KEY = {v: k for k, v in KEYBOARD_USAGE.items()}
_CONTROLLER_ID_TO_NAME = {v: k for k, v in CONTROLLER_BUTTON.items()}
_CONTROLLER_ID_TO_NAME.update({v: k for k, v in CONTROLLER_SOURCE.items()})
_MOUSE_BIT_TO_NAME = {v: k for k, v in MOUSE_BUTTON.items()}
_SCROLL_VALUE_TO_NAME = {v: k for k, v in MOUSE_SCROLL.items()}

_KNOWN_REPORTS = (
    REPORT_CONTROLLER,
    REPORT_KEYBOARD,
    REPORT_MOUSE,
    REPORT_UNBIND,
)


def button_index_to_name(button_index: int) -> str | None:
    """Map hardware button index to GameGent source name."""
    for name, idx in CONTROLLER_SOURCE.items():
        if idx == button_index:
            return name
    for name, idx in CONTROLLER_BUTTON.items():
        if idx == button_index:
            return name
    return None


def _is_native(data: bytes) -> bool:
    return REPORT_NATIVE in data[10:20]


def _find_report(data: bytes) -> tuple[bytes, int] | None:
    """Locate a remap report type marker and the payload offset that follows it."""
    for offset in range(14, 20):
        if offset + 1 >= len(data):
            break
        report = bytes(data[offset:offset + 2])
        if report in _KNOWN_REPORTS:
            return report, offset + 2
        if report[0] == 0x01 and report[1] in (2, 3):
            return report, offset + 2
    return None


def _decode_report_payload(report: bytes, payload: bytes) -> str | None:
    if report in (REPORT_UNBIND, REPORT_NATIVE):
        return None

    if report == REPORT_CONTROLLER:
        target_id = payload[0]
        name = _CONTROLLER_ID_TO_NAME.get(target_id)
        return f"controller:{name}" if name else f"controller:0x{target_id:02x}"

    if report == REPORT_KEYBOARD:
        usage = payload[1]
        name = _USAGE_TO_KEY.get(usage)
        return f"key:{name}" if name else f"key:0x{usage:02x}"

    if report == REPORT_MOUSE:
        scroll_val = payload[2]
        if scroll_val in _SCROLL_VALUE_TO_NAME:
            return f"mouse:{_SCROLL_VALUE_TO_NAME[scroll_val]}"
        bitfield = payload[3]
        name = _MOUSE_BIT_TO_NAME.get(bitfield)
        return f"mouse:{name}" if name else f"mouse:0x{bitfield:02x}"

    if report[0] == 0x01 and report[1] in (2, 3):
        count = report[1]
        keys = [payload[i] for i in range(count) if payload[i] != 0]
        if keys:
            parts = []
            for key_id in keys:
                name = _CONTROLLER_ID_TO_NAME.get(key_id, f"0x{key_id:02x}")
                parts.append(f"controller:{name}")
            return "+".join(parts)

    return None


def decode_target(data: bytes, button_index: int | None = None) -> str | None:
    """Decode a remap read response into a GameGent target string, or None if native."""
    if len(data) < 18 or data[0] != 0x06:
        return None

    if _is_native(data):
        return None

    found = _find_report(data)
    if not found:
        return None

    report, payload_offset = found
    if len(data) <= payload_offset:
        return None

    payload = data[payload_offset:payload_offset + 16]
    target = _decode_report_payload(report, payload)
    if not target:
        return None

    # GameSir leaves face buttons at identity mappings when unconfigured.
    if button_index is not None:
        source_name = button_index_to_name(button_index)
        if source_name in CONTROLLER_BUTTON and target == f"controller:{source_name}":
            return None

    return target


def read_button_mapping(fd, button_index: int) -> bytes | None:
    """Read one button's remap packet. Returns raw response bytes or None."""
    d = read_button_remap_register(fd, button_index)
    if not d or len(d) < 18 or d[0] != 0x06:
        return None
    if d[1] != REMAP_RESPONSE_CLASS or d[2] != REMAP_RESPONSE_SUBTYPE or d[3] != 0x02:
        return None
    return bytes(d)


def read_button_mappings() -> dict[str, str]:
    """Read all remapped buttons from the controller.

    Returns {source_name: target_string} matching config key_mappings format.
    """
    fd = open_device()
    try:
        drain(fd)
        init_session(fd)
        drain(fd)

        mappings: dict[str, str] = {}
        for button_index in REMAP_BUTTON_IDS:
            data = read_button_mapping(fd, button_index)
            if not data:
                drain(fd)
                continue

            source = button_index_to_name(button_index)
            target = decode_target(data, button_index)
            if source and target:
                mappings[source] = target
            drain(fd)

        return mappings
    finally:
        os.close(fd)


def read_remap_state() -> dict[int, dict]:
    """Read raw remap state for every known button (debug / CLI)."""
    fd = open_device()
    try:
        drain(fd)
        init_session(fd)
        drain(fd)

        state: dict[int, dict] = {}
        for button_index in REMAP_BUTTON_IDS:
            data = read_button_mapping(fd, button_index)
            if not data:
                drain(fd)
                continue

            state[button_index] = {
                "name": button_index_to_name(button_index) or f"0x{button_index:02x}",
                "target": decode_target(data, button_index),
                "raw": data.hex(),
            }
            drain(fd)

        return state
    finally:
        os.close(fd)


if __name__ == "__main__":
    import json
    print(json.dumps(read_button_mappings(), indent=2))
