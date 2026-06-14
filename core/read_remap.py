# core/read_remap.py — read button remap configuration
import os
from .transport import open_device, init_session, read_page_register, drain

# Button ID to name mapping
BUTTON_NAMES = {
    0x01: "A", 0x02: "B", 0x03: "X", 0x04: "Y",
    0x05: "LB", 0x06: "RB", 0x07: "LT", 0x08: "RT",
    0x09: "View", 0x0a: "Menu",
    0x0c: "L3", 0x0d: "R3",
    0x0e: "D-Up", 0x0f: "D-Down", 0x10: "D-Left", 0x11: "D-Right",
    0x12: "Capture", 0x13: "Home",
    0x20: "M1", 0x21: "M2", 0x22: "M3", 0x23: "M4",
    0x24: "L4", 0x25: "R4", 0x26: "L5", 0x27: "R5",
    0x28: "M5", 0x29: "M6",
    0x30: "C1", 0x31: "C2", 0x32: "C3", 0x33: "C4",
}


def read_remap_state():
    """Read full remap configuration from controller.

    Returns dict: {btn_id: {name, identity, raw_hex}}
    Page 0x1a/0x0a register per button contains calibration + identity data.
    The 3-byte value at bytes 28-30 encodes button identity (versioned).
    """
    fd = open_device()
    try:
        drain(fd)
        init_session(fd)
        drain(fd)

        state = {}
        for bid in sorted(BUTTON_NAMES.keys()):
            d = read_page_register(fd, 0x1a, 0x0a, bid)
            if d and any(b != 0 for b in bytes(d)[4:12]):
                data = bytes(d)
                identity = data[28:31]
                state[bid] = {
                    "name": BUTTON_NAMES.get(bid, f"0x{bid:02x}"),
                    "identity": identity.hex(),
                    "raw": data.hex(),
                }
            drain(fd)
        return state
    finally:
        os.close(fd)


def get_button_identities():
    """Return dict of {btn_id: identity_3bytes_hex} for all mappable buttons."""
    state = read_remap_state()
    return {bid: info["identity"] for bid, info in state.items()}


if __name__ == "__main__":
    import json
    state = read_remap_state()
    print(json.dumps(state, indent=2))
