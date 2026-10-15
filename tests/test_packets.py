"""Packet builder checks against doc/TARANTULA_PRO_PROTOCOL.md. No hardware needed.

Run: ./venv/bin/python -m pytest tests   (or ./venv/bin/python tests/test_packets.py)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.stick import StickConfig, KeyboardMapping, build_targeting_packet, build_geometry_packet, generate_hardware_stream
from core.gyro import GyroConfig, build_gyro_targeting, build_gyro_geometry
from core.trigger import TriggerConfig, build_trigger_packet
from core.hid_keycodes import apply_turbo
from core.lighting import build_layout_packet
import core.apply_config as apply_config


def test_stick_mapping_layout():
    p = build_targeting_packet(StickConfig(stick_id=1, mode="mouse", overlap_percent=40, mouse_dpi=70,
                                           invert_x=True, invert_y=False))
    assert p[:16] == bytes([0x07, 0x0f, 0x02, 0x03, 1, 40, 0x28, 0x50, 1, 0, 0x01, 0x01, 70, 70, 1, 0])


def test_stick_curve_ratio_byte():
    p = build_geometry_packet(StickConfig(stick_id=0, axis_ratio=80))
    assert p[:4] == bytes([0x07, 0x18, 0x02, 0x01]) and p[12] == 80


def test_wheel_keys_both_sticks():
    left = StickConfig(mode="wheel", keyboard=KeyboardMapping(left=0x04))
    right = StickConfig(mode="wheel")
    zones = [p[10] for p in generate_hardware_stream(left, right) if p[2:4] == bytes([0x05, 0x01])]
    assert zones == [0x10, 0x11, 0x12, 0x13, 0x18, 0x19, 0x1a, 0x1b,
                     0x14, 0x15, 0x16, 0x17, 0x1c, 0x1d, 0x1e, 0x1f]


def test_native_sends_no_keys_and_saves():
    pkts = generate_hardware_stream(StickConfig(), StickConfig())
    assert len(pkts) == 5 and pkts[-1][:4] == bytes([0x07, 0x03, 0x08, 0x03])


def test_gyro_mapping_layout():
    p = build_gyro_targeting(GyroConfig(overlap_percent=30, x_sensitivity=60, y_sensitivity=70,
                                        output_mode="mouse", axis_mode="yaw", activate_button=0x25,
                                        activate_method="hold"))
    assert p[:15] == bytes([0x07, 0x0e, 0x04, 0x03, 30, 40, 0x04, 0x00, 0x00, 0x25, 0x02, 60, 70, 0, 0])


def test_gyro_curve_ratio_byte():
    assert build_gyro_geometry(GyroConfig(axis_ratio=33))[10] == 33


def test_trigger_zero_values_kept():
    p = build_trigger_packet(TriggerConfig(deadzone_end=0, antideadzone_end=0, curve_intensity=0))
    assert (p[16], p[17], p[19]) == (0, 0, 0)


def test_trigger_hair_defaults_when_absent():
    cfg = apply_config._build_trigger(0, {})
    p = build_trigger_packet(cfg)
    assert (p[6], p[7]) == (10, 20)


def test_turbo_mode_thresholds():
    base = bytes(32)
    assert [apply_turbo(base, r)[12] for r in (1, 5, 12, 20)] == [0, 1, 2, 3]
    assert apply_turbo(base, 1)[13] == 1
    assert apply_turbo(base, 15, turbo=False)[12:14] == bytes([0, 1])


# Captured from the dongle (fw V0241221A): length byte 7 = 4 data bytes.
REAL_DPAD_REPLY = bytes.fromhex("06 07 09 02 00 00 01 00 00 00") + bytes(22)


def test_layout_keeps_other_dpad_fields_new_firmware():
    # Hypothetical newer reply: length 9 = 6 data bytes incl. calibration + macro key.
    reply = bytes([0x06, 0x09, 0x09, 0x02, 1, 3, 1, 1, 1, 0x29]) + bytes(22)
    assert build_layout_packet("switch", reply)[:10] == bytes([0x07, 0x09, 0x09, 0x01, 1, 3, 2, 1, 1, 0x29])


def test_layout_with_real_old_firmware_reply():
    assert build_layout_packet("switch", REAL_DPAD_REPLY)[4:10] == bytes([0, 0, 2, 0, 0, 0])
    # Only the 4 fields the reply carries are copied; bytes beyond must stay 0.
    odd = bytes([0x06, 0x07, 0x09, 0x02, 1, 3, 1, 1, 0xEE, 0xEE]) + bytes(22)
    assert build_layout_packet("xbox", odd)[8:10] == bytes([0, 0])


def test_read_reply_ignores_length_byte():
    import socket
    from core.transport import read_reply
    a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    a.setblocking(False)
    try:
        for length in (0x07, 0x09):
            b.send(bytes([0x06, length, 0x09, 0x02, 0, 0, 1]))
            assert read_reply(a.fileno(), 0x09, 0x02, 0.2)[1] == length
    finally:
        a.close()
        b.close()


def test_turbo_round_trips_through_read_decode():
    from core.hid_keycodes import controller_packet, keyboard_packet
    from core.read_remap import decode_turbo, _is_native
    for make in (lambda: controller_packet(0x24, 0x01), lambda: keyboard_packet(0x24, 0x08)):
        for rate in (5, 12, 20, 40):
            reply = b"\x06" + apply_turbo(make(), rate, continuous=False)[1:]
            assert not _is_native(reply), (rate,)
            assert decode_turbo(reply)["rate"] == rate
        assert decode_turbo(b"\x06" + apply_turbo(make(), 1, False, turbo=False)[1:]) is None


def test_remove_mapping_restores_factory_not_vacant():
    from core.hid_keycodes import reset_packet, REPORT_CONTROLLER
    for idx, expected in ((0x24, 0x24), (0x29, 0x0a), (0x2b, 0x0b), (0x28, 0x2d)):
        p = reset_packet(idx)
        assert p[14:16] == REPORT_CONTROLLER and p[16] == expected, hex(idx)
    sent = []
    orig = apply_config.apply_mapping
    apply_config.apply_mapping = lambda b, t: sent.append((b, t))
    try:
        apply_config._apply_mappings({"key_mappings": {}}, {"key_mappings": {"c1": "controller:a"}})
    finally:
        apply_config.apply_mapping = orig
    assert sent == [("c1", "reset")]


def test_wheel_outer_key_configurable():
    cfg = StickConfig(mode="wheel", keyboard=KeyboardMapping(left_outer=0x2c))
    pkts = {p[10]: p for p in generate_hardware_stream(cfg, StickConfig()) if p[2:4] == bytes([0x05, 0x01])}
    assert pkts[0x18][15:18] == bytes([2, 0, 0x2c])          # count 2, no modifier, key
    assert pkts[0x19][15:18] == bytes([1, 0x02, 0])          # unset: captured Left Shift


def test_foreign_host_rejected():
    from web.app import app
    c = app.test_client()
    assert c.get("/api/status", headers={"Host": "evil.example:5000"}).status_code == 403
    assert c.get("/api/status", headers={"Host": "localhost:5000"}).status_code != 403
    assert c.get("/api/status", headers={"Host": "[::1]:5000"}).status_code != 403


def test_face_leds_skipped_when_absent():
    sent = []
    orig = apply_config.set_face_colors
    apply_config.set_face_colors = lambda *a, **k: sent.append(a)
    try:
        assert _face_section({}) == "skipped" and sent == []
        assert _face_section({"face_leds": [[0, 100, 50]] * 4}) == "ok" and len(sent) == 1
    finally:
        apply_config.set_face_colors = orig


def _face_section(config):
    # Run apply_config_to_device with every other hardware call stubbed out.
    stubs = {}
    for name in ("set_hardware_state", "set_led_color", "set_abxy_layout", "set_stick_config",
                 "set_trigger_config", "set_gyro_config", "apply_mapping", "set_rumble_level"):
        stubs[name] = getattr(apply_config, name)
        setattr(apply_config, name, lambda *a, **k: None)
    try:
        return apply_config.apply_config_to_device(config)["face_leds"]
    finally:
        for name, fn in stubs.items():
            setattr(apply_config, name, fn)


def test_rumble_fire_single_value():
    import main
    calls = []
    orig = main.fire_rumble
    main.fire_rumble = lambda l, r, d: calls.append((l, r, d))
    try:
        main.cmd_rumble(type("A", (), dict(pct=None, right=None, fire=100, fire_right=None, duration=None))())
    finally:
        main.fire_rumble = orig
    assert calls == [(100, 100, 500)]


def test_wait_ack_skips_state_reports():
    import socket
    from core.transport import _wait_ack
    a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    a.setblocking(False)
    try:
        b.send(bytes([0x06, 0x1a, 0x0a, 0x03, 0x80]))   # gamepad state report
        b.send(bytes([0x06, 0x04, 0x02, 0x03, 0x05]))   # SET reply, status 5
        assert _wait_ack(a.fileno(), 0x02, 0x03, 0.2) == 5
        assert _wait_ack(a.fileno(), 0x02, 0x03, 0.05) is None
    finally:
        a.close()
        b.close()


def _sandbox(tmp):
    """Point config + profiles at a temp dir so tests never touch ~/.config/gamegent."""
    import core.config as cfgmod
    import core.profiles as prof
    cfgmod.CONFIG_DIR = tmp
    cfgmod.CONFIG_FILE = os.path.join(tmp, "config.json")
    prof.CONFIG_DIR = tmp
    prof.PROFILES_DIR = os.path.join(tmp, "profiles")
    prof.ACTIVE_FILE = os.path.join(tmp, "active_profile")
    return prof


def test_changed_sections_and_mapping_diff():
    old = {"brightness": 50, "key_mappings": {"l4": "controller:lb", "c1": "controller:back"}}
    new = {"brightness": 50, "key_mappings": {"l4": "controller:rb"}, "face_leds": [[0, 100, 50]]}
    assert apply_config.changed_sections(old, new) == {"mappings", "face_leds"}
    sent = []
    orig = apply_config.apply_mapping
    apply_config.apply_mapping = lambda b, t: sent.append((b, t))
    try:
        apply_config._apply_mappings(new, old)
    finally:
        apply_config.apply_mapping = orig
    assert sorted(sent) == [("c1", "reset"), ("l4", "controller:rb")]


def test_autosave_mirrors_active_profile_and_applies_only_changes():
    import tempfile
    prof = _sandbox(tempfile.mkdtemp())
    pushed = []
    import core.apply_config as ac
    orig = ac.apply_config_to_device
    ac.apply_config_to_device = lambda cfg, previous=None: pushed.append(ac.changed_sections(previous, cfg)) or {}
    try:
        base = prof.load_config()   # same shape the UI works on (defaults filled in)
        prof.save_profile("Game", base)
        edited = {**base, "brightness": 40}
        assert prof.autosave_config(edited, expected_profile="Game")["profile"] == "Game"
        assert prof.load_profile("Game")["brightness"] == 40      # survives a profile switch
        assert prof.load_config()["brightness"] == 40
        assert pushed == [{"lighting", "led"}]   # panel value follows brightness
        try:
            prof.autosave_config(edited, expected_profile="Other")
            assert False, "stale profile must be rejected"
        except prof.ProfileChanged:
            pass
        assert len(pushed) == 1
    finally:
        ac.apply_config_to_device = orig


def test_targets_round_trip():
    from core.targets import encode_target, decode_target
    cases = {
        "controller:a": "controller:a",
        "controller:x+controller:y": "controller:x+controller:y",
        "key:a": "key:a",
        "key:ctrl+shift+a": "key:left_ctrl+key:left_shift+key:a",
        "key:left_ctrl": "key:left_ctrl",
        "mouse:left_click+scroll_down": "mouse:left_click+mouse:scroll_down",
        "media:vol_up+media:mute": "media:mute+media:vol_up",
    }
    for target, expected in cases.items():
        report, payload = encode_target(target)
        assert decode_target(report, payload) == expected, target
        # decoded strings must be applicable again (read -> config -> apply)
        assert encode_target(expected) == (report, payload), target


def test_target_encoding_matches_official_app():
    from core.targets import encode_target
    assert encode_target("key:left_ctrl") == (bytes([2, 1]), bytes([0x01]).ljust(16, b"\0"))  # modifier bit, count 1
    assert encode_target("key:ctrl+a") == (bytes([2, 2]), bytes([0x01, 0x04]).ljust(16, b"\0"))
    assert encode_target("media:play") == (bytes([4, 4]), bytes([0, 0, 0, 0x10]).ljust(16, b"\0"))
    assert encode_target("mouse:button_4")[1][3] == 0x10 and encode_target("mouse:button_5")[1][3] == 0x08
    assert encode_target("mouse:scroll_up+scroll_down")[1][2] == 0x80


def test_none_and_reset_targets():
    from core.remap import resolve_target_packet
    assert resolve_target_packet(0x24, "none")[14:16] == bytes([0, 0])
    assert resolve_target_packet(0x24, "nc") == resolve_target_packet(0x24, "unbind")


def test_wheel_keys_accept_any_target():
    cfg = StickConfig(mode="wheel", stick_id=1, keyboard=KeyboardMapping(up="key:ctrl+w", left="mouse:left_click",
                                                                         down="none", right="controller:a"))
    pk = {p[10]: p for p in generate_hardware_stream(StickConfig(), cfg) if p[2:4] == bytes([0x05, 0x01])}
    assert pk[0x16][14:18] == bytes([2, 2, 0x01, 0x1a])      # right stick up = zone 0x12 + 4
    assert pk[0x14][14:16] == bytes([3, 4]) and pk[0x15][14:16] == bytes([1, 1])
    assert pk[0x17][14:16] == bytes([0, 0])                  # none
    assert all(pk[z][14:18] == bytes([2, 1, 0x02, 0]) for z in (0x1c, 0x1d, 0x1e, 0x1f))  # outline = Left Shift


def test_gyro_zones_use_same_encoder():
    from core.gyro import resolve_gyro_direction_packet
    p = resolve_gyro_direction_packet(0x22, "key:alt+f4")
    assert p[10] == 0x22 and p[14:18] == bytes([2, 2, 0x04, 0x3d])
    assert resolve_gyro_direction_packet(0x22, "bogus:x") is None


def test_curves_official_defaults_and_custom():
    g = build_geometry_packet(StickConfig())
    assert list(g[15:21]) == [30, 30, 50, 50, 70, 70] and g[23] == 0 and g[24] == 100
    c = build_geometry_packet(StickConfig(curve_preset="custom", curve_points=[[10, 5], [40, 60], [90, 95]]))
    assert list(c[15:21]) == [10, 5, 40, 60, 90, 95] and c[23] == 3
    t = build_trigger_packet(TriggerConfig(curve_preset="custom", curve_points=[[10, 5], [40, 60], [90, 95]]))
    assert list(t[10:16]) == [10, 5, 40, 60, 90, 95] and t[18] == 3
    try:
        build_geometry_packet(StickConfig(curve_preset="custom", curve_points=[[1, 1]]))
        assert False
    except ValueError:
        pass


def test_light_color_packets_hsv():
    from core.lighting import build_light_color_packet
    p = build_light_color_packet("panel", [(240, 100, 50)])
    assert list(p[:11]) == [7, 0x10, 7, 3, 4, 170, 100, 50, 0, 0, 0]
    abxy = build_light_color_packet("abxy", [(120, 100, 6), (0, 100, 6), (240, 100, 6), (59, 100, 6)])
    assert abxy[4] == 5 and list(abxy[5:17]) == [85, 100, 6, 0, 100, 6, 170, 100, 6, 41, 100, 6]
    assert build_light_color_packet("bayx", [(0, 0, 6)] * 4)[4] == 6


def test_apply_writes_abxy_and_bayx_and_panel_follows_brightness():
    import core.apply_config as ac
    calls = []
    orig = (ac.set_face_colors, ac.set_led_color)
    ac.set_face_colors = lambda *a, **k: calls.append(("face", k.get("name", "abxy")))
    ac.set_led_color = lambda *a: calls.append(("led", a))
    try:
        cfg = {"face_leds": [[0, 100, 6]] * 4, "bayx_leds": [[0, 0, 6]] * 4, "brightness": 30, "color_hue": 100,
               "color_saturation": 90, "color_lightness": 77, "lighting_zone": 1}
        assert ac._apply_face_leds(cfg) == "ok"
        ac.apply_config_to_device(cfg, previous={"brightness": 99, "color_hue": 100, "color_saturation": 90,
                                                 "color_lightness": 77, "lighting_zone": 1})
    finally:
        ac.set_face_colors, ac.set_led_color = orig
    assert ("face", "abxy") in calls and ("face", "bayx") in calls
    assert ("led", ("panel", 100, 90, 30)) in calls     # value = brightness, not color_lightness


def test_factory_reset_sections_and_mapping_unbinding():
    import tempfile
    prof = _sandbox(tempfile.mkdtemp())
    import core.apply_config as ac
    sent = []
    orig = (ac.apply_mapping, ac.set_stick_config)
    ac.apply_mapping = lambda b, t: sent.append((b, t))
    ac.set_stick_config = lambda *a: sent.append("sticks")
    try:
        cfg = {**prof.load_config(), "key_mappings": {"c1": "controller:a"},
               "stick_left": {"mode": "mouse", "axis_ratio": 80}}
        prof.save_config(cfg)
        out = prof.reset_config(["mappings", "sticks"])
    finally:
        ac.apply_mapping, ac.set_stick_config = orig
    assert out["config"]["key_mappings"] == {} and out["config"]["stick_left"]["mode"] == "native"
    assert ("c1", "reset") in sent and "sticks" in sent     # removed binding restores factory mapping
    try:
        prof.reset_config(["nope"])
        assert False
    except ValueError:
        pass


def test_device_info_parsing_matches_captured_replies():
    from core.device_info import parse_device_info, parse_version
    info = parse_device_info(bytes.fromhex("06 0e 0a 01 00 02 06 12 94 90 5e 5a a0 64 00") + bytes(17))
    assert (info["firmware"], info["battery"], info["charging"], info["mac"]) == ("2.0.6", 100, False, "12:94:90:5e:5a:a0")
    assert parse_device_info(bytes.fromhex("06 0e 0a 01 00 02 06 12 94 90 5e 5a a0 ff 00") + bytes(17))["charging"]
    ver = parse_version(bytes.fromhex("06 12 84 01 02 76 04 02 03 00 00 02 41 22 1a 01 00 00") + bytes(14))
    assert ver["firmware"] == "0241221A"


def test_macro_steps_any_target_and_limits():
    from core.remap import build_macro_step_packet, parse_macro_step, apply_macro
    from core.read_remap import _parse_macro_step
    assert parse_macro_step("key:a:100:150") == ("key:a", 100, 150) and parse_macro_step("lb:0:50") == ("lb", 0, 50)
    pkt = build_macro_step_packet(0x24, 2, "key:ctrl+a", 100, 150, macro_type=2, loop=True, loop_ms=300)
    assert list(pkt[4:8]) == [0x24, 2, 2, 1] and list(pkt[8:10]) == [1, 0x2c]
    assert list(pkt[10:16]) == [2, 2, 0x01, 0x04, 0, 0] and list(pkt[16:20]) == [0, 100, 0, 150]
    read = _parse_macro_step(b"\x06" + pkt[1:3] + b"\x02" + pkt[4:])   # reply header 06 13 01 02
    assert read["target"] == "key:left_ctrl+key:a" and (read["press_ms"], read["release_ms"]) == (100, 150)
    legacy = build_macro_step_packet(0x24, 0, "lb", 0, 50)
    assert list(legacy[10:13]) == [1, 1, 0x04]
    for bad in ([("lb", 0, 1)] * 13, [("lb", 0, 1), ("key:a", 0, 1)]):
        try:
            apply_macro("l4", bad)
            assert False
        except ValueError:
            pass


def test_toggle_only_does_not_turn_turbo_on():
    from core.hid_keycodes import controller_packet
    from core.read_remap import decode_turbo
    import core.apply_config as ac
    pkt = apply_turbo(controller_packet(0x24, 1), 1, True, turbo=False)
    assert (pkt[11], pkt[12], pkt[13]) == (1, 0, 1)
    assert decode_turbo(b"\x06" + pkt[1:])["turbo"] is False
    sent = []
    orig = (ac.apply_mapping, ac.set_turbo)
    ac.apply_mapping = lambda b, t: None
    ac.set_turbo = lambda b, t, rate, cont: sent.append((rate, cont))
    try:
        ac._apply_mappings({"key_mappings": {"l4": "controller:a"},
                            "turbo_settings": {"l4": {"rate": 10, "continuous": True, "turbo": False}}}, None)
    finally:
        ac.apply_mapping, ac.set_turbo = orig
    assert sent == [(None, True)]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
