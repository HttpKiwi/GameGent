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
        profiles.append({
            "name": name,
            "updated_at": updated_at,
            "active": name == active,
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
