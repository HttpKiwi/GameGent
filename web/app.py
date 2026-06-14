#!/usr/bin/env python3
"""GameGent Web Interface — Flask app for controller configuration."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

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
)
from core.hid_keycodes import CONTROLLER_BUTTON, CONTROLLER_SOURCE, apply_turbo, turbo_enable_packet
from core.remap import resolve_button_index, resolve_target_packet
from core.transport import open_device

app = Flask(__name__)
CORS(app)

REACT_DIST = os.path.join(os.path.dirname(__file__), 'react-app', 'dist')
USE_REACT = os.path.exists(os.path.join(REACT_DIST, 'index.html'))


@app.route('/')
def index():
    if USE_REACT:
        return send_from_directory(REACT_DIST, 'index.html')
    return send_from_directory('templates', 'index.html')


@app.route('/assets/<path:path>')
def serve_react_assets(path):
    assets_dir = os.path.join(REACT_DIST, 'assets')
    return send_from_directory(assets_dir, path)


@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


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
    """Save config.json."""
    try:
        config = request.json
        save_config(config)
        return jsonify({'success': True})
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


@app.route('/api/stick', methods=['POST'])
def set_stick_endpoint():
    """Configure stick."""
    try:
        data = request.json
        
        # Support both single stick and dual stick configuration
        if 'left' in data and 'right' in data:
            # Dual stick configuration
            left_data = data['left']
            right_data = data['right']
            
            left_cfg = StickConfig(
                stick_id=0,
                mode=left_data.get('mode', 'native'),
                x_sensitivity=left_data.get('x_sens', 50),
                y_sensitivity=left_data.get('y_sens', 50),
                overlap_percent=left_data.get('overlap', 50),
                mouse_dpi=left_data.get('mouse_dpi', 50),
                is_circle=not left_data.get('square', False),
                deadzone_min=left_data.get('deadzone_min', 5),
                antideadzone_min=left_data.get('antideadzone_min', 0),
                deadzone_max=left_data.get('deadzone_max', 100),
                antideadzone_max=left_data.get('antideadzone_max', 100),
                curve_preset=left_data.get('curve', 'linear'),
                curve_intensity=left_data.get('curve_intensity', 50),
            )
            
            right_cfg = StickConfig(
                stick_id=1,
                mode=right_data.get('mode', 'native'),
                x_sensitivity=right_data.get('x_sens', 50),
                y_sensitivity=right_data.get('y_sens', 50),
                overlap_percent=right_data.get('overlap', 50),
                mouse_dpi=right_data.get('mouse_dpi', 50),
                is_circle=not right_data.get('square', False),
                deadzone_min=right_data.get('deadzone_min', 5),
                antideadzone_min=right_data.get('antideadzone_min', 0),
                deadzone_max=right_data.get('deadzone_max', 100),
                antideadzone_max=right_data.get('antideadzone_max', 100),
                curve_preset=right_data.get('curve', 'linear'),
                curve_intensity=right_data.get('curve_intensity', 50),
            )
            
            if left_data.get('mode') == 'keyboard':
                kbd = KeyboardMapping(
                    left=left_data.get('kbd_left', 0x04),
                    right=left_data.get('kbd_right', 0x07),
                    up=left_data.get('kbd_up', 0x1a),
                    down=left_data.get('kbd_down', 0x16),
                    overlap_left=left_data.get('kbd_ol_left', 1),
                    overlap_right=left_data.get('kbd_ol_right', 1),
                    overlap_up=left_data.get('kbd_ol_up', 1),
                    overlap_down=left_data.get('kbd_ol_down', 1),
                )
                left_cfg.keyboard = kbd
            
            if right_data.get('mode') == 'keyboard':
                kbd = KeyboardMapping(
                    left=right_data.get('kbd_left', 0x04),
                    right=right_data.get('kbd_right', 0x07),
                    up=right_data.get('kbd_up', 0x1a),
                    down=right_data.get('kbd_down', 0x16),
                    overlap_left=right_data.get('kbd_ol_left', 1),
                    overlap_right=right_data.get('kbd_ol_right', 1),
                    overlap_up=right_data.get('kbd_ol_up', 1),
                    overlap_down=right_data.get('kbd_ol_down', 1),
                )
                right_cfg.keyboard = kbd
            
            set_stick_config(left_cfg, right_cfg)
        else:
            # Single stick configuration (legacy support)
            stick = data.get('stick', 'left')
            mode = data.get('mode', 'native')
            
            cfg = StickConfig(
                stick_id=0 if stick == 'left' else 1,
                mode=mode,
                x_sensitivity=data.get('x_sens', 50),
                y_sensitivity=data.get('y_sens', 50),
                overlap_percent=data.get('overlap', 50),
                mouse_dpi=data.get('mouse_dpi', 50),
                is_circle=not data.get('square', False),
                deadzone_min=data.get('deadzone_min', 5),
                antideadzone_min=data.get('antideadzone_min', 0),
                deadzone_max=data.get('deadzone_max', 100),
                antideadzone_max=data.get('antideadzone_max', 100),
                curve_preset=data.get('curve', 'linear'),
                curve_intensity=data.get('curve_intensity', 50),
            )
            
            if mode == 'keyboard':
                kbd = KeyboardMapping(
                    left=data.get('kbd_left', 0x04),
                    right=data.get('kbd_right', 0x07),
                    up=data.get('kbd_up', 0x1a),
                    down=data.get('kbd_down', 0x16),
                    overlap_left=data.get('kbd_ol_left', 1),
                    overlap_right=data.get('kbd_ol_right', 1),
                    overlap_up=data.get('kbd_ol_up', 1),
                    overlap_down=data.get('kbd_ol_down', 1),
                )
                cfg.keyboard = kbd
            
            other = StickConfig(stick_id=1 if stick == 'left' else 0, mode='native')
            left_cfg = cfg if stick == 'left' else other
            right_cfg = cfg if stick == 'right' else other
            
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
        
        parsed_steps = []
        for spec in steps:
            parts = spec.split(':')
            if len(parts) != 3:
                return jsonify({'error': f'Invalid step format: {spec}'}), 400
            btn, press, release = parts
            parsed_steps.append((btn, int(press), int(release)))
        
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
        import time
        data = request.json
        
        button = data.get('button')
        target = data.get('target')
        rate = data.get('rate')
        continuous = data.get('continuous', False)
        
        btn = resolve_button_index(button)
        remap = resolve_target_packet(btn, target)
        turbo_enabled = rate is not None
        rate_val = rate if turbo_enabled else 1
        turbo = apply_turbo(remap, rate_val, continuous, turbo=turbo_enabled)
        enable = turbo_enable_packet(btn)
        commit = bytearray(32)
        commit[0:4] = [0x07, 0x03, 0x08, 0x03]
        
        fd = open_device()
        try:
            os.write(fd, turbo)
            time.sleep(0.03)
            os.write(fd, enable)
            time.sleep(0.03)
            os.write(fd, commit)
            time.sleep(0.03)
        finally:
            os.close(fd)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
