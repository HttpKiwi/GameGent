# core/config.py
import os
import json

from .defaults import factory_defaults

CONFIG_DIR = os.path.expanduser("~/.config/gamegent")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = factory_defaults()
DEFAULT_CONFIG.update({"inner_deadzone": 0, "outer_deadzone": 100})


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
            # Wheel keys used to be HID usage codes; they are mapping targets now.
            from .hid_keycodes import KEYBOARD_USAGE
            names = {v: k for k, v in KEYBOARD_USAGE.items()}
            for side in ("stick_left", "stick_right"):
                kb = (config.get(side) or {}).get("keyboard")
                for key in ("left", "right", "up", "down"):
                    if isinstance(kb, dict) and isinstance(kb.get(key), int):
                        kb[key] = f"key:{names[kb[key]]}" if kb[key] in names else "none"
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
