# core/config.py
import os
import json

CONFIG_DIR = os.path.expanduser("~/.config/gamegent")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "brightness": 100,
    "lighting_mode": "static",
    "lighting_speed": 100,
    "color_hue": 0,
    "lighting_zone": 1,
    "inner_deadzone": 0,
    "outer_deadzone": 100,
    "key_mappings": {},
    "stick_left": {
        "mode": "native",
        "is_circle": True,
        "x_sensitivity": 50,
        "y_sensitivity": 50,
        "overlap_percent": 50,
        "mouse_x_dpi": 50,
        "mouse_y_dpi": 50,
        "deadzone_min": 5,
        "antideadzone_min": 0,
        "deadzone_max": 100,
        "antideadzone_max": 100,
        "curve_preset": "linear",
        "curve_intensity": 50,
        "keyboard": {
            "left": 4, "right": 7, "up": 26, "down": 22,
            "overlap_left": 1, "overlap_right": 1, "overlap_up": 1, "overlap_down": 1,
            "left_outer": 0, "right_outer": 0, "up_outer": 0, "down_outer": 0
        }
    },
    "stick_right": {
        "mode": "native",
        "is_circle": True,
        "x_sensitivity": 50,
        "y_sensitivity": 50,
        "overlap_percent": 50,
        "mouse_x_dpi": 50,
        "mouse_y_dpi": 50,
        "deadzone_min": 5,
        "antideadzone_min": 0,
        "deadzone_max": 100,
        "antideadzone_max": 100,
        "curve_preset": "linear",
        "curve_intensity": 50,
        "keyboard": {
            "left": 4, "right": 7, "up": 26, "down": 22,
            "overlap_left": 1, "overlap_right": 1, "overlap_up": 1, "overlap_down": 1,
            "left_outer": 0, "right_outer": 0, "up_outer": 0, "down_outer": 0
        }
    }
}

def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG.copy()
        
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            updated = False
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
                    updated = True
                elif isinstance(v, dict) and isinstance(config[k], dict):
                    for sub_k, sub_v in v.items():
                        if sub_k not in config[k]:
                            config[k][sub_k] = sub_v
                            updated = True
            # Migrate legacy joystick_left/joystick_right to stick_left/stick_right
            if "joystick_left" in config and "stick_left" not in config:
                config["stick_left"] = config["joystick_left"].copy()
                updated = True
            if "joystick_right" in config and "stick_right" not in config:
                config["stick_right"] = config["joystick_right"].copy()
                updated = True
            if updated:
                save_config(config)
            return config
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(config_data: dict):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)
