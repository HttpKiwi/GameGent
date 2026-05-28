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
    "joystick_left": {
        "is_circle": True,
        "deadzone_min": 5,
        "antideadzone_min": 0,
        "deadzone_max": 100,
        "antideadzone_max": 100,
        "curve_preset": "linear",
        "curve_intensity": 50
    },
    "joystick_right": {
        "is_circle": True,
        "deadzone_min": 5,
        "antideadzone_min": 0,
        "deadzone_max": 100,
        "antideadzone_max": 100,
        "curve_preset": "linear",
        "curve_intensity": 50
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
            # Ensure all default keys exist and nested dicts are populated
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
            if updated:
                save_config(config)
            return config
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(config_data: dict):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)
