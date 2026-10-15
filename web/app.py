#!/usr/bin/env python3
"""GameGent Web Interface — Flask app for controller configuration."""

import sys
import os
import threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from urllib.parse import urlsplit

from flask import Flask, Response, jsonify, request, send_from_directory

from core import (
    set_hardware_state, LIGHTING_MODES,
    set_color, set_abxy_layout, set_led_color, set_face_button_color, set_face_colors,
    set_stick_config, StickConfig, KeyboardMapping,
    STICK_MODES, CURVE_PRESETS,
    set_rumble_level, fire_rumble,
    GyroConfig, GYRO_OUTPUT_MODES, GYRO_MOTION_MODES, GYRO_METHODS, GYRO_AXIS_MODES,
    set_gyro_config,
    apply_mapping,
    apply_combo,
    apply_macro,
    TriggerConfig, HAIR_MODES, set_trigger_config,
    load_config, save_config,
    read_button_mappings,
)
from core.read_remap import read_button_mappings_detailed
from core.hid_keycodes import CONTROLLER_BUTTON, CONTROLLER_SOURCE
from core.remap import set_turbo, parse_macro_step
from core.transport import find_dongle_path
from core.device_info import read_device_info
from core.profiles import (
    list_profiles, save_profile, delete_profile, activate_profile, get_active_profile,
    save_working_config, autosave_config, reset_config, ProfileChanged,
)
from core.apply_config import apply_config_to_device
from core.game_watcher import (
    load_game_rules,
    save_game_rules,
    get_watcher_status,
    start_game_watcher,
    tick as game_watcher_tick,
    list_pickable_processes,
)

app = Flask(__name__)


@app.before_request
def reject_foreign_host():
    """Local-only API: refuse other Host headers so a web page can't reach it via DNS rebinding."""
    host = urlsplit("//" + request.host).hostname
    if host not in ("127.0.0.1", "localhost", "::1"):
        return jsonify({"error": "forbidden host"}), 403

# Auto-switch profiles when a linked game process is detected.
# Skips if `gamegent daemon` (or another host) already holds the watcher lock.
if not start_game_watcher():
    import sys
    print(
        "GameGent: profile watcher not started (another watcher holds the lock).",
        file=sys.stderr,
    )

REACT_DIST = os.path.join(os.path.dirname(__file__), 'react-app', 'dist')
USE_REACT = os.path.exists(os.path.join(REACT_DIST, 'index.html'))


@app.route('/')
def index():
    if USE_REACT:
        response = send_from_directory(REACT_DIST, 'index.html')
        response.headers['Cache-Control'] = 'no-store'
        return response
    return send_from_directory('templates', 'index.html')


@app.route('/assets/<path:path>')
def serve_react_assets(path):
    assets_dir = os.path.join(REACT_DIST, 'assets')
    response = send_from_directory(assets_dir, path)
    # Hashed filenames are immutable; keep short cache for html-driven reloads
    response.headers['Cache-Control'] = 'public, max-age=60'
    return response


@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


@app.route('/api/status', methods=['GET'])
def device_status():
    """Dongle connection status."""
    path = find_dongle_path()
    return jsonify({'connected': path is not None, 'path': path})


@app.route('/api/device', methods=['GET'])
def get_device_info():
    """Battery, charging state, controller/dongle firmware, MAC."""
    if not find_dongle_path():
        return jsonify({'error': 'GameSir Dongle not found'}), 503
    try:
        return jsonify(read_device_info())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _gamepad_snapshot() -> dict:
    """Live controller state for the in-app tester.

    Prefers the dongle's vendor state report (includes L4/R4/T1-T3/C1-C4 and works with or
    without mappings); falls back to /dev/input/js* (skips mouse/keyboard passthrough nodes,
    WebKitGTK's Gamepad API collapses trigger/hat axes into stick axes).
    """
    from core.raw_state import vendor_gamepad_state
    vendor = vendor_gamepad_state()
    if vendor:
        return vendor
    from core.gamepad_read import read_gamepad_state
    return {**read_gamepad_state(), 'source': 'js'}


@app.route('/api/gamepad', methods=['GET'])
def gamepad_state():
    try:
        return jsonify(_gamepad_snapshot())
    except Exception as e:
        return jsonify({'connected': False, 'error': str(e)}), 500


@app.route('/api/gamepad/stream', methods=['GET'])
def gamepad_stream():
    """Server-sent events: one connection pushes the tester state whenever it changes
    (about 50 Hz max) instead of the UI issuing a request every frame."""
    import json
    import time

    def events():
        last, since_write = None, 0.0
        while True:
            try:
                state = _gamepad_snapshot()
            except Exception as e:
                state = {'connected': False, 'error': str(e)}
            # `raw` includes motion-sensor bytes that change every frame: not a reason to send
            key = json.dumps({k: v for k, v in state.items() if k != 'raw'}, sort_keys=True)
            if key != last:
                yield f"data: {json.dumps(state)}\n\n"
                last, since_write = key, 0.0
            elif since_write >= 1.0:
                yield ": keep-alive\n\n"  # a failed write is how a closed tab is noticed
                since_write = 0.0
            time.sleep(0.02)
            since_write += 0.02

    return Response(events(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current config.json."""
    try:
        config = load_config()
        return jsonify(config)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/config', methods=['POST'])
def save_config_endpoint():
    """Save config.json and mirror it into the active profile."""
    try:
        save_working_config(request.json)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/config/autosave', methods=['POST'])
def autosave_config_endpoint():
    """Save to working config + active profile and push only the changed sections.

    Body: {config, profile}. `profile` is the profile the client believes is active;
    409 if it changed meanwhile (e.g. game auto-switch) so a stale edit can't overwrite it.
    """
    try:
        data = request.json or {}
        return jsonify({'success': True, **autosave_config(data['config'], expected_profile=data.get('profile'))})
    except ProfileChanged as e:
        return jsonify({'error': 'active profile changed', 'active': str(e.args[0])}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reset', methods=['POST'])
def reset_endpoint():
    """Factory-reset config sections: {sections: [sticks|triggers|gyro|mappings|lighting|rumble|all]}."""
    try:
        data = request.json or {}
        return jsonify({'success': True, **reset_config(data.get('sections'))})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/config/apply', methods=['POST'])
def apply_config_endpoint():
    """Push current (or provided) config to the controller."""
    try:
        data = request.json or {}
        config = data.get('config') or load_config()
        applied = apply_config_to_device(config)
        return jsonify({'success': True, 'applied': applied})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/profiles', methods=['GET'])
def get_profiles():
    """List software profiles."""
    try:
        return jsonify({
            'profiles': list_profiles(),
            'active': get_active_profile(),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/profiles', methods=['POST'])
def create_or_update_profile():
    """Save current or provided config as a named software profile."""
    try:
        data = request.json or {}
        name = data.get('name')
        if not name:
            return jsonify({'error': 'name is required'}), 400
        config = data.get('config')
        make_active = data.get('make_active', True)
        meta = save_profile(name, config, make_active=make_active)
        return jsonify({'success': True, **meta, 'active': get_active_profile()})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/profiles/activate', methods=['POST'])
def activate_profile_endpoint():
    """Load a profile into working config; optionally apply to hardware."""
    try:
        data = request.json or {}
        name = data.get('name')
        if not name:
            return jsonify({'error': 'name is required'}), 400
        apply = data.get('apply', True)
        result = activate_profile(name, apply=apply)
        return jsonify({
            'success': True,
            'name': result['name'],
            'active': get_active_profile(),
            'config': result['config'],
            'applied': result['applied'],
        })
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/profiles/<name>', methods=['DELETE'])
def delete_profile_endpoint(name):
    """Delete a software profile."""
    try:
        delete_profile(name)
        return jsonify({'success': True, 'active': get_active_profile()})
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/game-rules', methods=['GET'])
def get_game_rules():
    """Get game→profile auto-switch rules."""
    try:
        return jsonify(load_game_rules())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/game-rules', methods=['POST'])
def set_game_rules():
    """Replace game→profile auto-switch rules."""
    try:
        data = request.json or {}
        saved = save_game_rules(data)
        return jsonify({'success': True, **saved})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/game-rules/status', methods=['GET'])
def game_rules_status():
    """Watcher status: active game, last match, errors."""
    try:
        return jsonify(get_watcher_status())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/game-rules/processes', methods=['GET'])
def game_rules_processes():
    """List running processes for the portal-style binder picker."""
    try:
        return jsonify({'processes': list_pickable_processes()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/game-rules/tick', methods=['POST'])
def game_rules_tick():
    """Force one watcher tick (debug / immediate apply)."""
    try:
        data = request.json or {}
        apply = data.get('apply', True)
        status = game_watcher_tick(apply=bool(apply))
        return jsonify({'success': True, **status})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/lighting', methods=['POST'])
def set_lighting():
    """Set lighting mode, brightness, speed."""
    try:
        data = request.json
        mode = data.get('mode', 'static')
        brightness = data.get('brightness', 100)
        speed = data.get('speed', 100)
        
        if mode not in LIGHTING_MODES:
            return jsonify({'error': f'Unknown mode: {mode}'}), 400
        
        set_hardware_state(mode, brightness, speed)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/color', methods=['POST'])
def set_color_endpoint():
    """Set lighting hue."""
    try:
        data = request.json
        hue = data.get('hue', 0)
        set_color(hue)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/layout', methods=['POST'])
def set_layout_endpoint():
    """Set ABXY layout."""
    try:
        data = request.json
        layout = data.get('layout', 'xbox')
        set_abxy_layout(layout)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/led', methods=['POST'])
def set_led_endpoint():
    """Set LED color (panel or home)."""
    try:
        data = request.json
        target = data.get('target', 'panel')
        hue = data.get('hue', 0)
        saturation = data.get('saturation', 100)
        lightness = data.get('lightness', 50)
        
        set_led_color(target, hue, saturation, lightness)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/face', methods=['POST'])
def set_face_endpoint():
    """Set face button colors."""
    try:
        data = request.json
        button = data.get('button', 'all')
        
        if button == 'all':
            set_face_colors(
                (data.get('a_hue', 0), data.get('a_sat', 100), data.get('a_light', 50)),
                (data.get('b_hue', 0), data.get('b_sat', 100), data.get('b_light', 50)),
                (data.get('x_hue', 0), data.get('x_sat', 100), data.get('x_light', 50)),
                (data.get('y_hue', 0), data.get('y_sat', 100), data.get('y_light', 50)),
            )
        else:
            hue = data.get('hue', 0)
            saturation = data.get('saturation', 100)
            lightness = data.get('lightness', 50)
            set_face_button_color(button, hue, saturation, lightness)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/trigger', methods=['POST'])
def set_trigger_endpoint():
    """Configure trigger deadzones and hair trigger."""
    try:
        data = request.json
        
        left = TriggerConfig(
            trigger_id=0,
            hair_mode=data.get('left_hair', data.get('hair', 'off')),
            hair_trigger_begin=data.get('left_hair_begin', data.get('hair_begin', 0)),
            hair_trigger_end=data.get('left_hair_end', data.get('hair_end', 100)),
            deadzone_begin=data.get('left_dz_begin', data.get('dz_begin', 0)),
            deadzone_end=data.get('left_dz_end', data.get('dz_end', 100)),
            antideadzone_begin=data.get('left_anti_begin', data.get('anti_begin', 0)),
            antideadzone_end=data.get('left_anti_end', data.get('anti_end', 100)),
            curve_preset=data.get('left_curve', data.get('curve', 'linear')),
            curve_intensity=data.get('left_intensity', data.get('curve_intensity', 50)),
        )
        
        right = TriggerConfig(
            trigger_id=1,
            hair_mode=data.get('right_hair', data.get('hair', 'off')),
            hair_trigger_begin=data.get('right_hair_begin', data.get('hair_begin', 0)),
            hair_trigger_end=data.get('right_hair_end', data.get('hair_end', 100)),
            deadzone_begin=data.get('right_dz_begin', data.get('dz_begin', 0)),
            deadzone_end=data.get('right_dz_end', data.get('dz_end', 100)),
            antideadzone_begin=data.get('right_anti_begin', data.get('anti_begin', 0)),
            antideadzone_end=data.get('right_anti_end', data.get('anti_end', 100)),
            curve_preset=data.get('right_curve', data.get('curve', 'linear')),
            curve_intensity=data.get('right_intensity', data.get('curve_intensity', 50)),
        )
        
        set_trigger_config(left, right)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _stick_from_request(stick_id: int, d: dict) -> StickConfig:
    cfg = StickConfig(
        stick_id=stick_id,
        mode=d.get('mode', 'native'),
        axis_ratio=d.get('axis_ratio', d.get('y_sens', 50)),
        overlap_percent=d.get('overlap', 50),
        mouse_dpi=d.get('mouse_dpi', 50),
        invert_x=d.get('invert_x', False),
        invert_y=d.get('invert_y', False),
        is_circle=not d.get('square', False),
        deadzone_min=d.get('deadzone_min', 5),
        antideadzone_min=d.get('antideadzone_min', 0),
        deadzone_max=d.get('deadzone_max', 100),
        antideadzone_max=d.get('antideadzone_max', 100),
        curve_preset=d.get('curve', 'linear'),
        curve_intensity=d.get('curve_intensity', 100),
        curve_points=d.get('curve_points'),
    )
    if isinstance(d.get('keyboard'), dict):
        known = KeyboardMapping.__dataclass_fields__
        cfg.keyboard = KeyboardMapping(**{k: v for k, v in d['keyboard'].items() if k in known})
    return cfg


@app.route('/api/stick', methods=['POST'])
def set_stick_endpoint():
    """Configure one stick ({stick, ...}) or both ({left, right})."""
    try:
        data = request.json
        if 'left' in data and 'right' in data:
            left_cfg = _stick_from_request(0, data['left'])
            right_cfg = _stick_from_request(1, data['right'])
        else:
            stick = data.get('stick', 'left')
            cfg = _stick_from_request(0 if stick == 'left' else 1, data)
            other = StickConfig(stick_id=1 if stick == 'left' else 0, mode='native')
            left_cfg, right_cfg = (cfg, other) if stick == 'left' else (other, cfg)
        set_stick_config(left_cfg, right_cfg)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/gyro', methods=['POST'])
def set_gyro_endpoint():
    """Configure gyro/motion aim."""
    try:
        data = request.json
        
        cfg = GyroConfig(
            output_mode=data.get('mode', 'mouse'),
            motion_mode=data.get('motion', 'aim'),
            axis_mode=data.get('axis', 'global'),
            activate_method=data.get('method', 'hold'),
            activate_button=resolve_gyro_button(data.get('button', 'c1')),
            x_sensitivity=data.get('x_sens', 50),
            y_sensitivity=data.get('y_sens', 50),
            axis_ratio=data.get('axis_ratio', 50),
            overlap_percent=data.get('overlap', 50),
            deadzone_min=data.get('deadzone_min', 0),
            deadzone_max=data.get('deadzone_max', 100),
            antideadzone_min=data.get('antideadzone_min', 0),
            antideadzone_max=data.get('antideadzone_max', 100),
            invert_x=data.get('invert_x', False),
            invert_y=data.get('invert_y', False),
            curve_preset=data.get('curve', 'linear'),
            curve_intensity=data.get('curve_intensity', 50),
            kb_up=data.get('kb_up', 'key:w'),
            kb_down=data.get('kb_down', 'key:s'),
            kb_left=data.get('kb_left', 'key:a'),
            kb_right=data.get('kb_right', 'key:d'),
        )
        
        set_gyro_config(cfg)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def resolve_gyro_button(value):
    """Resolve button name or hex to index."""
    v = str(value).lower().strip()
    if v in CONTROLLER_SOURCE:
        return CONTROLLER_SOURCE[v]
    if v in CONTROLLER_BUTTON:
        return CONTROLLER_BUTTON[v]
    if v.startswith('0x'):
        return int(v, 16)
    return int(v, 10)


@app.route('/api/map', methods=['POST'])
def set_map_endpoint():
    """Remap button."""
    try:
        data = request.json
        button = data.get('button')
        target = data.get('target')
        apply_mapping(button, target)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


_remap_lock = threading.Lock()
_remap_cache: dict = {'time': 0.0, 'value': None}


def _read_remaps_shared(fresh: bool) -> dict:
    """Read remaps from the controller; overlapping polls share one read.

    A read takes ~2.5 s and holds the device lock, so a poll that arrives while one is running
    (or right after) gets the cached result instead of queueing another read; with nothing cached
    yet it waits for the running read. `fresh` (Pull from Device) always reads.
    """
    import time as _time

    def cached():
        return _remap_cache['value'] if _time.monotonic() - _remap_cache['time'] < 1.5 else None

    if not fresh:
        if cached():
            return cached()
        if _remap_lock.locked() and _remap_cache['value']:
            return _remap_cache['value']  # a read is running: serve the previous result
    with _remap_lock:
        if not fresh and cached():
            return cached()  # the read we waited for just finished
        value = read_button_mappings_detailed()
        _remap_cache.update(time=_time.monotonic(), value=value)
        return value


@app.route('/api/mappings/read', methods=['POST'])
def read_mappings_endpoint():
    """Read button remaps (and turbo) from controller hardware."""
    if not find_dongle_path():
        return jsonify({'error': 'GameSir Dongle not found'}), 503
    try:
        sync = bool(request.is_json and request.json and request.json.get('sync', False))
        detailed = _read_remaps_shared(fresh=sync)
        mappings = detailed.get('key_mappings', {})
        turbo_settings = detailed.get('turbo_settings', {})
        if sync:
            config = load_config()
            config['key_mappings'] = mappings
            if turbo_settings:
                config['turbo_settings'] = turbo_settings
            save_config(config)
        return jsonify({
            'key_mappings': mappings,
            'turbo_settings': turbo_settings,
        })
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/combo', methods=['POST'])
def set_combo_endpoint():
    """Set combo keys."""
    try:
        data = request.json
        button = data.get('button')
        keys = data.get('keys', [])
        
        if len(keys) not in (2, 3):
            return jsonify({'error': 'Combo requires 2 or 3 keys'}), 400
        
        apply_combo(button, keys)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/macro', methods=['POST'])
def set_macro_endpoint():
    """Set macro."""
    try:
        data = request.json
        button = data.get('button')
        steps = data.get('steps', [])
        hold = data.get('hold', False)
        loop = data.get('loop', False)
        
        parsed_steps = [parse_macro_step(spec) for spec in steps]
        macro_type = 0x02 if hold else 0x01
        apply_macro(button, parsed_steps, macro_type=macro_type, loop=loop)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rumble', methods=['POST'])
def set_rumble_endpoint():
    """Set rumble level or fire rumble."""
    try:
        data = request.json
        
        if data.get('pct') is not None:
            pct = data.get('pct')
            right = data.get('right')
            set_rumble_level(pct, pct if right is None else right)
        
        if data.get('fire'):
            l = data.get('fire')
            r = data.get('fire_right', l)
            duration = data.get('duration', 500)
            fire_rumble(l, r, duration)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/turbo', methods=['POST'])
def set_turbo_endpoint():
    """Set turbo/continuous fire on a button."""
    try:
        data = request.json
        
        button = data.get('button')
        target = data.get('target')
        rate = data.get('rate')
        continuous = data.get('continuous', False)
        
        set_turbo(button, target, rate, continuous)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


from core.raw_state import install_exit_hooks
install_exit_hooks()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
