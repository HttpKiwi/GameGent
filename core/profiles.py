"""Local software profiles — named configs under ~/.config/gamegent/profiles/."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

from .config import CONFIG_DIR, load_config, save_config

PROFILES_DIR = os.path.join(CONFIG_DIR, "profiles")
ACTIVE_FILE = os.path.join(CONFIG_DIR, "active_profile")

_NAME_RE = re.compile(r"^[\w][\w \-]{0,63}$", re.UNICODE)


def sanitize_profile_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        raise ValueError("Profile name is required")
    if not _NAME_RE.match(name):
        raise ValueError(
            "Profile name must start with a letter/number and use only "
            "letters, numbers, spaces, hyphens, or underscores (max 64 chars)"
        )
    return name


def _profile_path(name: str) -> str:
    return os.path.join(PROFILES_DIR, f"{sanitize_profile_name(name)}.json")


def ensure_profiles_dir() -> None:
    os.makedirs(PROFILES_DIR, exist_ok=True)


def get_active_profile() -> str | None:
    if not os.path.exists(ACTIVE_FILE):
        return None
    try:
        with open(ACTIVE_FILE, "r", encoding="utf-8") as f:
            name = f.read().strip()
        return name or None
    except OSError:
        return None


def set_active_profile(name: str | None) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not name:
        if os.path.exists(ACTIVE_FILE):
            os.remove(ACTIVE_FILE)
        return
    name = sanitize_profile_name(name)
    with open(ACTIVE_FILE, "w", encoding="utf-8") as f:
        f.write(name)


def _appearance_summary(config: dict) -> dict:
    """Compact lighting preview for the Profiles UI."""
    face = config.get("face_leds") or []
    home = config.get("home_led")

    def face_css(idx: int) -> str | None:
        if idx >= len(face) or not face[idx] or len(face[idx]) < 3:
            return None
        h = round((int(face[idx][0]) / 255) * 360)
        s = int(face[idx][1])
        l = int(face[idx][2])
        return f"hsl({h}, {s}%, {l}%)"

    panel_h = int(config.get("color_hue", 0) or 0)
    panel_s = int(config.get("color_saturation", 100) or 100)
    panel_l = int(config.get("color_lightness", 50) or 50)
    home_css = None
    if home and len(home) >= 3:
        home_css = (
            f"hsl({round((int(home[0]) / 255) * 360)}, {int(home[1])}%, {int(home[2])}%)"
        )

    return {
        "lighting_mode": config.get("lighting_mode", "static"),
        "brightness": config.get("brightness", 100),
        "panel": f"hsl({panel_h}, {panel_s}%, {panel_l}%)",
        "home": home_css,
        "face": {
            "a": face_css(0),
            "b": face_css(1),
            "x": face_css(2),
            "y": face_css(3),
        },
    }


def list_profiles() -> list[dict]:
    ensure_profiles_dir()
    active = get_active_profile()
    profiles = []
    for entry in sorted(os.listdir(PROFILES_DIR)):
        if not entry.endswith(".json"):
            continue
        name = entry[:-5]
        path = os.path.join(PROFILES_DIR, entry)
        try:
            st = os.stat(path)
            updated_at = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
        except OSError:
            updated_at = None
        appearance = None
        try:
            cfg = load_profile(name)
            appearance = _appearance_summary(cfg)
        except Exception:
            appearance = None
        profiles.append({
            "name": name,
            "updated_at": updated_at,
            "active": name == active,
            "appearance": appearance,
        })
    return profiles


def profile_exists(name: str) -> bool:
    return os.path.isfile(_profile_path(name))


def load_profile(name: str) -> dict:
    path = _profile_path(name)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Profile not found: {name}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid profile file: {name}")
    # Support wrapped {name, config} or raw config
    if "config" in data and isinstance(data["config"], dict):
        return data["config"]
    return data


def save_profile(name: str, config: dict | None = None, *, make_active: bool = True) -> dict:
    name = sanitize_profile_name(name)
    ensure_profiles_dir()
    if config is None:
        config = load_config()
    if not isinstance(config, dict):
        raise ValueError("Config must be an object")

    payload = {
        "name": name,
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
        "config": config,
    }
    path = _profile_path(name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)

    if make_active:
        set_active_profile(name)
    return {"name": name, "updated_at": payload["updated_at"]}


def delete_profile(name: str) -> None:
    name = sanitize_profile_name(name)
    path = _profile_path(name)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Profile not found: {name}")
    os.remove(path)
    if get_active_profile() == name:
        set_active_profile(None)


def activate_profile(name: str, *, apply: bool = True) -> dict:
    """Load a profile into the working config; optionally push to hardware."""
    from .apply_config import apply_config_to_device

    config = load_profile(name)
    save_config(config)
    set_active_profile(sanitize_profile_name(name))
    result = {"name": name, "config": config, "applied": None}
    if apply:
        result["applied"] = apply_config_to_device(config)
    return result


def save_working_config(config: dict, *, expected_profile: str | None = None) -> str | None:
    """Persist the working config and mirror it into the active profile so edits
    survive a profile switch. Returns the active profile name (None if none)."""
    active = get_active_profile()
    if expected_profile is not None and expected_profile != active:
        raise ProfileChanged(active)
    save_config(config)
    if active and profile_exists(active):
        save_profile(active, config, make_active=False)
    return active


class ProfileChanged(Exception):
    """The active profile changed (e.g. game auto-switch) since the client loaded it."""


def autosave_config(config: dict, *, expected_profile: str | None = None) -> dict:
    """Save to working config + active profile, then push only what changed to hardware."""
    from .apply_config import apply_config_to_device

    previous = load_config()
    active = save_working_config(config, expected_profile=expected_profile)
    return {"profile": active, "applied": apply_config_to_device(config, previous=previous)}


def reset_config(sections: list[str] | None = None) -> dict:
    """Factory-reset sections (default all) of the working config; saved to the active profile
    and pushed to the controller like any other edit. Returns {config, profile, applied}."""
    from .defaults import reset_sections

    config = reset_sections(load_config(), sections)
    return {"config": config, **autosave_config(config)}
