# core/config.py
import os
import json

CONFIG_DIR = os.path.expanduser("~/.config/gamegent")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "brightness": 100,
    "lighting_mode": "static",
    "lighting_speed": 100,
    "lighting_zone": 1,
    "inner_deadzone": 0,
    "outer_deadzone": 100,
    "key_mappings": {}
}

def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG.copy()
        
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(config_data: dict):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)
