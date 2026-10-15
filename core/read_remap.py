# core/read_remap.py — read button remap configuration from hardware
from __future__ import annotations

import time

from .hid_keycodes import (
    CONTROLLER_BUTTON,
    CONTROLLER_SOURCE,
    KEYBOARD_USAGE,
    MOUSE_BUTTON,
    MOUSE_SCROLL,
    REPORT_UNBIND,
)
from .targets import decode_target as decode_report_target
from .transport import close_device, open_device, init_session, send_cmd, read_response, drain

# Page gateway observed in GameSir app captures: OUT 07 05 05 02, IN 06 13 05 02
REMAP_RESPONSE_HEADER = bytes([0x13, 0x05, 0x02])
MACRO_RESPONSE_HEADER = bytes([0x13, 0x01, 0x02])

# Native / no custom remap (replaces flag+report at bytes 13–14)
REPORT_NATIVE = bytes([0x14, 0x01])

# Read response layout matches write packets (report ID 0x06 prefix):
#   byte 10: button index
#   bytes 11–12: turbo flags (continuous, turbo mode) when set
#   byte 13: 0x01 flag, or turbo rate when turbo is on, or start of native 14 01
#   bytes 14–15: report type (01 01 / 02 02 / 03 04 / 01 02 / 00 00 / …)
#   bytes 16+: payload
_REPORT_OFFSET = 14
_PAYLOAD_OFFSET = 16

REMAP_BUTTON_IDS = sorted(set(CONTROLLER_BUTTON.values()) | set(CONTROLLER_SOURCE.values()))

_USAGE_TO_KEY = {v: k for k, v in KEYBOARD_USAGE.items()}
_CONTROLLER_ID_TO_NAME = {v: k for k, v in CONTROLLER_BUTTON.items()}
_CONTROLLER_ID_TO_NAME.update({v: k for k, v in CONTROLLER_SOURCE.items()})
_MOUSE_BIT_TO_NAME = {v: k for k, v in MOUSE_BUTTON.items()}
_SCROLL_VALUE_TO_NAME = {v: k for k, v in MOUSE_SCROLL.items()}


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
    """Native slot: bytes 13–14 are 14 01 (not a normal flag+report).

    Byte 12 (turbo mode) must be off: a 20 Hz turbo on a controller target has the
    same bytes 13–14 (rate 0x14, joystick type 01).
    """
    return len(data) > 14 and bytes(data[13:15]) == REPORT_NATIVE and data[12] == 0


def _report_type(data: bytes) -> bytes | None:
    if len(data) < _PAYLOAD_OFFSET:
        return None
    return bytes(data[_REPORT_OFFSET:_PAYLOAD_OFFSET])


def _payload(data: bytes) -> bytes:
    return data[_PAYLOAD_OFFSET:_PAYLOAD_OFFSET + 16]


def _decode_report_payload(report: bytes, payload: bytes) -> str | None:
    if report in (REPORT_UNBIND, REPORT_NATIVE):
        return None
    return decode_report_target(report, payload)


def decode_turbo(data: bytes) -> dict | None:
    """Extract turbo flags from a remap read response, if enabled."""
    if len(data) < 14 or _is_native(data):
        return None
    continuous = data[11] == 0x01
    turbo_on = data[12] in (1, 2, 3)  # turbo modes A/B/C, picked by rate
    if not turbo_on and not continuous:
        return None
    rate = int(data[13]) if turbo_on else 10
    return {
        "rate": rate if turbo_on else 10,
        "continuous": continuous,
        "turbo": turbo_on,
    }


def decode_target(data: bytes, button_index: int | None = None) -> str | None:
    """Decode a remap read response into a GameGent target string, or None if native."""
    if len(data) < 18 or data[0] != 0x06:
        return None

    if _is_native(data):
        return None

    report = _report_type(data)
    if not report:
        return None

    # Macro / unbind share report 00 00 — caller may resolve macros separately.
    if report == REPORT_UNBIND:
        return None

    target = _decode_report_payload(report, _payload(data))
    if not target:
        return None

    # Identity mappings (a→a, r4→r4, screenshot→screenshot) mean "not remapped".
    if button_index is not None:
        source_name = button_index_to_name(button_index)
        if source_name and target == f"controller:{source_name}":
            return None

    return target


def _request_remap(fd, button_index: int) -> None:
    cmd = bytes([0x07, 0x05, 0x05, 0x02, 0x00, button_index & 0xFF]) + b"\x00" * 26
    send_cmd(fd, cmd)


def _collect_remap_responses(
    fd,
    wanted: set[int] | None = None,
    timeout: float = 1.2,
) -> dict[int, bytes]:
    """Read remap responses, keyed by button index at byte 10.

    The device often returns responses out of order / lagged relative to
    requests. Never discard a valid remap packet for a different button —
    buffer by id until we have what we need (or timeout).

    If wanted is None/empty, keep reading until timeout (straggler scoop).
    """
    pending: dict[int, bytes] = {}
    deadline = time.time() + timeout
    need = set(wanted) if wanted else None
    while time.time() < deadline:
        if need is not None and need.issubset(pending):
            break
        d = read_response(fd, header=REMAP_RESPONSE_HEADER, timeout=0.12)
        if not d or len(d) < 11:
            continue
        pending[d[10]] = bytes(d)
    return pending


def read_button_mapping(fd, button_index: int) -> bytes | None:
    """Read one button's remap packet. Returns raw response bytes or None."""
    drain(fd)
    _request_remap(fd, button_index)
    pending = _collect_remap_responses(fd, {button_index}, timeout=1.0)
    return pending.get(button_index)


def _is_macro_slot(data: bytes) -> bool:
    """Remap slot uses report 00 00 — may be unbind or macro init."""
    return not _is_native(data) and _report_type(data) == REPORT_UNBIND


def _parse_macro_step(data: bytes) -> dict | None:
    """Parse one 06 13 01 02 macro step response. Returns None if empty/padding."""
    if len(data) < 20:
        return None
    if data[0] != 0x06 or data[1:4] != MACRO_RESPONSE_HEADER:
        return None
    # Empty steps have action bytes cleared (byte 10 == 0).
    if data[10] == 0:
        return None
    # Inactive / no-macro responses often have macro_type 0 and zero body.
    if data[6] == 0 and data[11] == 0:
        return None

    press_ms = (data[16] << 8) | data[17]
    release_ms = (data[18] << 8) | data[19]
    # byte 10/11 = mapping type / key count, 12-15 = code (same encoding as key mappings)
    target = decode_report_target(bytes(data[10:12]), bytes(data[12:16]))
    if target is None:
        target_id = data[12]
        target = f"controller:{_CONTROLLER_ID_TO_NAME.get(target_id, f'0x{target_id:02x}')}"
    return {
        "step": data[5],
        "macro_type": data[6],
        "loop": bool(data[7]),
        "target": target,
        "press_ms": press_ms,
        "release_ms": release_ms,
    }


def read_macro_steps(fd, button_index: int, max_steps: int = 16) -> list[dict]:
    """Read macro steps for a button via OUT 07 13 01 02 [btn] [step]."""
    steps: list[dict] = []
    for step in range(max_steps):
        drain(fd)
        cmd = bytes([0x07, 0x13, 0x01, 0x02, button_index & 0xFF, step]) + b"\x00" * 26
        send_cmd(fd, cmd)
        time.sleep(0.04)

        got = None
        deadline = time.time() + 0.35
        while time.time() < deadline:
            d = read_response(fd, timeout=0.08)
            if not d or len(d) < 20:
                continue
            if d[1:4] != MACRO_RESPONSE_HEADER:
                continue
            if d[4] != (button_index & 0xFF) or d[5] != step:
                continue
            got = bytes(d)
            break

        if not got:
            break
        parsed = _parse_macro_step(got)
        if not parsed:
            break
        steps.append(parsed)
    return steps


def format_macro_target(steps: list[dict]) -> str:
    """Compact target string for key_mappings, e.g. macro:controller:y+controller:dpad_up."""
    parts = [s["target"] for s in steps]
    return "macro:" + "+".join(parts)


def read_button_mappings() -> dict[str, str]:
    """Read all remapped buttons from the controller.

    Returns {source_name: target_string} matching config key_mappings format.
    Macros become ``macro:controller:…+controller:…``.
    """
    result = read_remap_state()
    mappings: dict[str, str] = {}
    for entry in result.values():
        name = entry.get("name")
        target = entry.get("target")
        if name and target:
            mappings[name] = target
    return mappings


def read_button_mappings_detailed() -> dict:
    """Read mappings plus turbo_settings (for API sync)."""
    state = read_remap_state()
    mappings: dict[str, str] = {}
    turbo_settings: dict[str, dict] = {}
    for entry in state.values():
        name = entry.get("name")
        if not name:
            continue
        if entry.get("target"):
            mappings[name] = entry["target"]
        if entry.get("turbo"):
            turbo = dict(entry["turbo"])
            turbo["target"] = entry.get("target") or turbo.get("target")
            turbo_settings[name] = {
                "target": turbo.get("target") or "",
                "rate": turbo.get("rate", 10),
                "continuous": bool(turbo.get("continuous", False)),
            }
    return {"key_mappings": mappings, "turbo_settings": turbo_settings}


def read_remap_state() -> dict[int, dict]:
    """Read remap state for every known button (debug / CLI).

    Responses are matched by button id (byte 10), not request order.
    Macro slots (report 00 00) additionally read step packets.
    """
    fd = open_device()
    try:
        drain(fd)
        init_session(fd)
        drain(fd)

        # Request all remap slots, buffering responses by button id.
        for button_index in REMAP_BUTTON_IDS:
            _request_remap(fd, button_index)
            time.sleep(0.02)

        pending = _collect_remap_responses(fd, set(REMAP_BUTTON_IDS), timeout=2.5)
        # Catch stragglers
        pending.update(_collect_remap_responses(fd, None, timeout=0.35))
        # Re-request misses individually
        missing = [b for b in REMAP_BUTTON_IDS if b not in pending]
        for button_index in missing:
            drain(fd)
            _request_remap(fd, button_index)
            pending.update(_collect_remap_responses(fd, {button_index}, timeout=0.8))

        state: dict[int, dict] = {}
        macro_candidates: list[int] = []

        for button_index in REMAP_BUTTON_IDS:
            data = pending.get(button_index)
            name = button_index_to_name(button_index) or f"0x{button_index:02x}"
            if not data:
                state[button_index] = {
                    "name": name,
                    "target": None,
                    "turbo": None,
                    "raw": None,
                }
                continue

            target = decode_target(data, button_index)
            turbo = decode_turbo(data)
            if turbo and target:
                turbo = {**turbo, "target": target}

            if target is None and _is_macro_slot(data):
                macro_candidates.append(button_index)

            state[button_index] = {
                "name": name,
                "target": target,
                "turbo": turbo,
                "raw": data.hex(),
            }

        for button_index in macro_candidates:
            steps = read_macro_steps(fd, button_index)
            if steps:
                state[button_index]["target"] = format_macro_target(steps)
                state[button_index]["macro_steps"] = steps

        return state
    finally:
        close_device(fd)


if __name__ == "__main__":
    import json
    print(json.dumps(read_button_mappings_detailed(), indent=2))
