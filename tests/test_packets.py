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
    assert (p[6], p[7]) == (0x0a, 0x1e)


def test_turbo_mode_thresholds():
    base = bytes(32)
    assert [apply_turbo(base, r)[12] for r in (1, 5, 12, 20)] == [0, 1, 2, 3]
    assert apply_turbo(base, 1)[13] == 1
    assert apply_turbo(base, 15, turbo=False)[12:14] == bytes([0, 1])


def test_layout_keeps_other_dpad_fields():
    reply = bytes([0x06, 0x07, 0x09, 0x02, 1, 3, 1, 1, 1, 0x29]) + bytes(22)
    assert build_layout_packet("switch", reply)[:10] == bytes([0x07, 0x09, 0x09, 0x01, 1, 3, 2, 1, 1, 0x29])


def test_face_leds_skipped_when_absent():
    sent = []
    orig = apply_config.set_face_colors
    apply_config.set_face_colors = lambda *a: sent.append(a)
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
    assert sorted(sent) == [("c1", "unbind"), ("l4", "controller:rb")]


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
        assert pushed == [{"lighting"}]
        try:
            prof.autosave_config(edited, expected_profile="Other")
            assert False, "stale profile must be rejected"
        except prof.ProfileChanged:
            pass
        assert len(pushed) == 1
    finally:
        ac.apply_config_to_device = orig


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
