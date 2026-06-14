# core/read_state.py — full controller state read
import os
from .transport import open_device, init_session, read_typed_register, read_page_register, drain, read_response
from .rumble import read_rumble_level


def read_lighting():
    fd = open_device()
    try:
        drain(fd)
        d = read_typed_register(fd, 0x06, 0x07, 0x02)
        if d and d[1] == 0x06 and d[2] == 0x07 and d[3] == 0x02:
            return (d[4], d[5], d[6])
    finally:
        os.close(fd)
    return (0, 0, 0)


def read_color():
    fd = open_device()
    try:
        drain(fd)
        d = read_typed_register(fd, 0x10, 0x07, 0x04)
        if d and d[1] == 0x10 and d[2] == 0x07 and d[3] == 0x04:
            return (d[5], d[6], d[7])
    finally:
        os.close(fd)
    return (0, 0, 0)


def read_stick_targeting(stick_id=0):
    import time
    fd = open_device()
    try:
        drain(fd)
        cmd = bytes([0x07, 0x0f, 0x02, 0x04, stick_id & 1]) + b"\x00" * 27
        os.write(fd, cmd)
        time.sleep(0.05)
        d = read_response(fd)
        if d and d[1] == 0x0f and d[2] == 0x02 and d[3] == 0x04:
            return d
    finally:
        os.close(fd)
    return None


def read_stick_geometry(stick_id=0):
    import time
    fd = open_device()
    try:
        drain(fd)
        if stick_id == 0:
            cmd = bytes([0x07, 0x18, 0x02, 0x02]) + b"\x00" * 28
        else:
            cmd = bytes([0x07, 0x18, 0x02, 0x02, 0x01, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00]) + b"\x00" * 21
        os.write(fd, cmd)
        time.sleep(0.05)
        d = read_response(fd)
        if d and d[1] == 0x18 and d[2] == 0x02 and d[3] == 0x02:
            return d
    finally:
        os.close(fd)
    return None


def read_trigger(trigger_id=0):
    """Read trigger config via 07 05 03 02 [id] [00]. Returns raw bytes or None."""
    fd = open_device()
    try:
        drain(fd)
        d = read_page_register(fd, 0x05, 0x03, trigger_id)
        if d and d[1] == 0x13 and d[2] == 0x03 and d[3] == 0x02:
            return d
    finally:
        os.close(fd)
    return None


def read_layout():
    """Read ABXY layout via 07 05 09 02. Returns 'xbox', 'switch', or None."""
    fd = open_device()
    try:
        drain(fd)
        d = read_page_register(fd, 0x05, 0x09, 0)
        if d and d[1] == 0x07 and d[2] == 0x09 and d[3] == 0x02:
            return "xbox" if d[6] == 0x01 else "switch"
    finally:
        os.close(fd)
    return None


def read_state():
    state = {}
    fd = open_device()
    try:
        drain(fd)
        init_session(fd)
        page0502 = {}
        for off in range(0x2e):
            d = read_page_register(fd, 0x05, 0x05, off)
            if d and d[1] == 0x13:
                page0502[off] = bytes(d[4:])
        if page0502:
            state["page_05_02"] = {k: v.hex() for k, v in page0502.items()}
        page0202 = {}
        for off in range(2):
            d = read_page_register(fd, 0x05, 0x02, off)
            if d and d[1] == 0x13:
                page0202[off] = bytes(d[4:])
        if page0202:
            state["page_02_02"] = {k: v.hex() for k, v in page0202.items()}
    finally:
        os.close(fd)

    rumble = read_rumble_level()
    lighting = read_lighting()
    color = read_color()

    state["rumble"] = {"left": rumble[0], "right": rumble[1]}
    state["lighting"] = {"brightness": lighting[0], "speed": lighting[1], "mode": lighting[2]}
    state["color"] = {"hue": color[0], "saturation": color[1], "lightness": color[2]}

    for sid, name in [(0, "left"), (1, "right")]:
        t = read_stick_targeting(sid)
        g = read_stick_geometry(sid)
        stick = {}
        if t:
            stick["mode"] = t[10]
            stick["x_sensitivity"] = t[5]
            stick["y_sensitivity"] = t[6]
            stick["mouse_dpi"] = t[12]
        if g:
            stick["is_circle"] = bool(g[11])
            stick["deadzone_min"] = g[13]
            stick["antideadzone_min"] = g[14]
            stick["deadzone_max"] = g[21]
            stick["antideadzone_max"] = g[22]
            stick["curve_type"] = g[23]
            stick["curve_intensity"] = g[24]
            stick["curve_coords"] = list(g[15:21])
        if stick:
            state[f"stick_{name}"] = stick

    # Read triggers
    for tid, name in [(0, "left"), (1, "right")]:
        tr = read_trigger(tid)
        if tr:
            state[f"trigger_{name}"] = {
                "hair_mode": tr[5],
                "hair_begin": tr[6],
                "hair_end": tr[7],
                "deadzone_begin": tr[8],
                "antideadzone_begin": tr[9],
                "curve_coords": list(tr[10:16]),
                "deadzone_end": tr[16],
                "antideadzone_end": tr[17],
                "curve_type": tr[18],
                "curve_intensity": tr[19],
            }

    # Read layout
    layout = read_layout()
    if layout:
        state["layout"] = layout

    return state
