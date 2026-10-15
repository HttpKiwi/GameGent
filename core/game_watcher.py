"""Game-linked auto profiles — match running processes to software profiles."""

from __future__ import annotations

import json
import os
import re
import threading
import time
from typing import Any

from .config import CONFIG_DIR
from .profiles import activate_profile, get_active_profile, profile_exists
from .transport import find_dongle_path

RULES_FILE = os.path.join(CONFIG_DIR, "game_rules.json")
WATCHER_LOCK_FILE = os.path.join(CONFIG_DIR, "watcher.lock")

DEFAULT_RULES: dict[str, Any] = {
    "enabled": False,
    "default_profile": None,
    "poll_seconds": 2,
    "rules": [],
}

_STATUS_LOCK = threading.Lock()
_WATCHER_STOP = threading.Event()
_WATCHER_THREAD: threading.Thread | None = None
_WATCHER_LOCK_FD: int | None = None

_STATUS: dict[str, Any] = {
    "enabled": False,
    "active_game": None,
    "active_profile": None,
    "last_match": None,
    "last_applied_profile": None,
    "last_error": None,
    "running": False,
}


def _default_rules() -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_RULES))


def load_game_rules() -> dict[str, Any]:
    if not os.path.exists(RULES_FILE):
        return _default_rules()
    try:
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _default_rules()
        out = _default_rules()
        out.update({k: data[k] for k in out if k in data})
        rules = data.get("rules", [])
        out["rules"] = rules if isinstance(rules, list) else []
        return out
    except (OSError, json.JSONDecodeError):
        return _default_rules()


def save_game_rules(data: dict[str, Any]) -> dict[str, Any]:
    """Validate and persist game rules. Returns normalized rules."""
    normalized = normalize_game_rules(data)
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=4)
    with _STATUS_LOCK:
        _STATUS["enabled"] = bool(normalized.get("enabled"))
    return normalized


def normalize_game_rules(data: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Rules payload must be an object")

    out = _default_rules()
    out["enabled"] = bool(data.get("enabled", False))
    default_profile = data.get("default_profile")
    if default_profile is not None and default_profile != "":
        out["default_profile"] = str(default_profile).strip()
    else:
        out["default_profile"] = None

    try:
        poll = int(data.get("poll_seconds", 2))
    except (TypeError, ValueError) as e:
        raise ValueError("poll_seconds must be an integer") from e
    out["poll_seconds"] = max(1, min(60, poll))

    rules_in = data.get("rules", [])
    if not isinstance(rules_in, list):
        raise ValueError("rules must be a list")

    rules: list[dict[str, Any]] = []
    for i, raw in enumerate(rules_in):
        if not isinstance(raw, dict):
            raise ValueError(f"rules[{i}] must be an object")
        profile = str(raw.get("profile") or "").strip()
        if not profile:
            raise ValueError(f"rules[{i}].profile is required")
        name = str(raw.get("name") or profile).strip()
        match = raw.get("match") or {}
        if not isinstance(match, dict):
            raise ValueError(f"rules[{i}].match must be an object")

        processes = match.get("process") or []
        appids = match.get("steam_appid") or []
        if not isinstance(processes, list) or not isinstance(appids, list):
            raise ValueError(f"rules[{i}].match process/steam_appid must be lists")

        proc_list = [str(p).strip() for p in processes if str(p).strip()]
        appid_list = [str(a).strip() for a in appids if str(a).strip()]
        if not proc_list and not appid_list:
            raise ValueError(f"rules[{i}] needs at least one process or steam_appid match")

        rules.append({
            "name": name,
            "profile": profile,
            "match": {
                "process": proc_list,
                "steam_appid": appid_list,
            },
        })

    out["rules"] = rules
    return out


def scan_processes(proc_root: str = "/proc") -> list[str]:
    """Return lowercase strings of process comm + cmdline for matching."""
    texts: list[str] = []
    for entry in _iter_proc_entries(proc_root):
        parts = []
        if entry.get("comm"):
            parts.append(entry["comm"])
        if entry.get("cmdline"):
            parts.append(entry["cmdline"])
        if parts:
            texts.append(" ".join(parts).lower())
    return texts


_NOISE_COMM = frozenset({
    "bash", "zsh", "fish", "sh", "dash", "sudo", "login", "systemd",
    "systemd-journal", "systemd-logind", "systemd-udevd", "dbus-daemon",
    "pipewire", "wireplumber", "pulseaudio", "Xorg", "Xwayland",
    "gnome-shell", "kwin_wayland", "kwin_x11", "Hyprland", "sway",
    "cursor", "node", "npm", "python", "python3", "chrome", "firefox",
    "code", "electron", "gamegent",
})


def _iter_proc_entries(proc_root: str = "/proc") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        entries = os.listdir(proc_root)
    except OSError:
        return out

    for entry in entries:
        if not entry.isdigit():
            continue
        base = os.path.join(proc_root, entry)
        comm = ""
        cmdline = ""
        try:
            with open(os.path.join(base, "comm"), "r", encoding="utf-8", errors="ignore") as f:
                comm = f.read().strip()
        except OSError:
            continue
        try:
            with open(os.path.join(base, "cmdline"), "rb") as f:
                cmdline = f.read().replace(b"\x00", b" ").decode("utf-8", errors="ignore").strip()
        except OSError:
            pass
        out.append({
            "pid": int(entry),
            "comm": comm,
            "cmdline": cmdline,
        })
    return out


_NOISE_EXE = frozenset({
    "steam.exe",
    "steamwebhelper.exe",
    "gameoverlayui.exe",
    "start_protected_game.exe",
    "unitycrashhandler64.exe",
    "unitycrashhandler32.exe",
    "explorer.exe",
    "cmd.exe",
    "conhost.exe",
})


def _basename_token(path: str) -> str:
    path = path.strip().strip('"').strip("'")
    if not path:
        return ""
    # Wine/Proton often: .../drive_c/foo/Control_DX12.exe
    name = os.path.basename(path.replace("\\", "/"))
    return name


def suggest_process_match(comm: str, cmdline: str) -> str:
    """Pick a stable matcher string for binding a profile to this process."""
    tokens = cmdline.split() if cmdline else []
    # Prefer Windows/Proton .exe names that look like the game itself
    for tok in tokens:
        base = _basename_token(tok)
        low = base.lower()
        if low.endswith(".exe") and len(base) > 4 and low not in _NOISE_EXE:
            return base
    # Fall back to any .exe (including launchers) if that's all we have
    for tok in tokens:
        base = _basename_token(tok)
        if base.lower().endswith(".exe") and len(base) > 4:
            return base
    # Prefer steamapps/common game binary path
    for tok in tokens:
        norm = tok.replace("\\", "/")
        if "/steamapps/common/" in norm.lower():
            base = _basename_token(tok)
            if base:
                return base
    # argv0 basename
    if tokens:
        base = _basename_token(tokens[0])
        if base and base not in (".", ".."):
            return base
    return comm or ""


def _steam_roots() -> list[str]:
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, ".steam", "steam"),
        os.path.join(home, ".local", "share", "Steam"),
        os.path.join(home, ".var", "app", "com.valvesoftware.Steam", ".local", "share", "Steam"),
    ]
    roots: list[str] = []
    for root in candidates:
        if os.path.isdir(os.path.join(root, "steamapps")):
            roots.append(root)

    # Extra libraries from libraryfolders.vdf
    for root in list(roots):
        vdf = os.path.join(root, "steamapps", "libraryfolders.vdf")
        if not os.path.isfile(vdf):
            continue
        try:
            with open(vdf, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError:
            continue
        for m in re.finditer(r'"path"\s+"([^"]+)"', text):
            path = m.group(1).replace("\\\\", "/")
            if os.path.isdir(os.path.join(path, "steamapps")) and path not in roots:
                roots.append(path)
    return roots


def _load_steam_install_map() -> dict[str, dict[str, str]]:
    """Map installdir (lower) and appid -> {appid, name, installdir}."""
    by_install: dict[str, dict[str, str]] = {}
    for root in _steam_roots():
        apps = os.path.join(root, "steamapps")
        try:
            names = os.listdir(apps)
        except OSError:
            continue
        for name in names:
            if not (name.startswith("appmanifest_") and name.endswith(".acf")):
                continue
            path = os.path.join(apps, name)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            appid_m = re.search(r'"appid"\s+"(\d+)"', text)
            dir_m = re.search(r'"installdir"\s+"([^"]+)"', text)
            name_m = re.search(r'"name"\s+"([^"]+)"', text)
            if not appid_m or not dir_m:
                continue
            appid = appid_m.group(1)
            installdir = dir_m.group(1)
            game_name = name_m.group(1) if name_m else installdir
            meta = {"appid": appid, "name": game_name, "installdir": installdir}
            by_install[installdir.lower()] = meta
            by_install[f"appid:{appid}"] = meta
    return by_install


def _common_installdir(cmdline: str) -> str | None:
    text = cmdline.replace("\\", "/")
    m = re.search(r"/steamapps/common/([^/]+)/", text, re.IGNORECASE)
    if not m:
        return None
    return m.group(1)


def _extract_steam_appid(cmdline: str, install_map: dict[str, dict[str, str]] | None = None) -> str | None:
    text = cmdline.replace("\\", "/")
    low = text.lower()
    for pat in (
        r"compatdata/(\d+)",
        r"(?:steam[_-]?appid|appid)\s*[=:]\s*(\d+)",
        r"-gameid\s+(\d+)",
        r"gameid[=:](\d+)",
    ):
        m = re.search(pat, low, re.IGNORECASE)
        if m:
            return m.group(1)
    install = _common_installdir(text)
    if install and install_map:
        meta = install_map.get(install.lower())
        if meta:
            return meta["appid"]
    return None


def list_pickable_processes(proc_root: str = "/proc") -> list[dict[str, Any]]:
    """Running Steam games + processes for the portal-style picker.

    Steam titles are returned first as ``kind=steam`` rows keyed by appid
    (best signal for EAC/Proton titles like Elden Ring). Plain processes follow.
    """
    install_map = _load_steam_install_map()
    by_match: dict[str, dict[str, Any]] = {}
    steam_games: dict[str, dict[str, Any]] = {}

    def _is_tool_steam_title(name: str) -> bool:
        low = name.lower()
        return (
            low.startswith("proton")
            or "steam linux runtime" in low
            or "steamworks" in low
            or low.startswith("steamworks")
        )

    for entry in _iter_proc_entries(proc_root):
        cmdline = entry.get("cmdline") or ""
        if not cmdline and entry.get("comm", "").startswith(("kworker", "ksoftirq", "migration", "rcu_")):
            continue
        match = suggest_process_match(entry.get("comm") or "", cmdline)
        if not match:
            continue

        appid = _extract_steam_appid(cmdline, install_map)
        install = _common_installdir(cmdline)
        if install and not appid and install.lower() in install_map:
            appid = install_map[install.lower()]["appid"]

        if appid:
            meta = install_map.get(f"appid:{appid}") or (
                install_map.get(install.lower()) if install else None
            )
            game_name = (meta or {}).get("name") or (install.replace("_", " ") if install else f"Steam {appid}")
            if not _is_tool_steam_title(game_name):
                prev = steam_games.get(appid)
                score = 10
                if match.lower().endswith(".exe") and match.lower() not in _NOISE_EXE:
                    score += 50
                if "/steamapps/common/" in cmdline.lower().replace("\\", "/"):
                    score += 20
                candidate = {
                    "pid": entry["pid"],
                    "match": "",  # bind by appid, not flaky exe
                    "comm": entry.get("comm") or "",
                    "label": game_name,
                    "cmdline": f"Steam AppId {appid}",
                    "steam_appid": appid,
                    "kind": "steam",
                    "score": score,
                }
                if prev is None or candidate["score"] > prev["score"]:
                    steam_games[appid] = candidate

        key = match.lower()
        score = 0
        if match.lower().endswith(".exe") and match.lower() not in _NOISE_EXE:
            score += 100
        elif match.lower().endswith(".exe"):
            score += 20
        if appid:
            score += 50
        if "/steamapps/" in cmdline.lower().replace("\\", "/"):
            score += 40
        if entry.get("comm") in _NOISE_COMM and score < 40:
            score -= 20
        if match.lower() in _NOISE_EXE:
            score -= 60

        preview = cmdline[:120] if cmdline else (entry.get("comm") or "")
        candidate = {
            "pid": entry["pid"],
            "match": match,
            "comm": entry.get("comm") or "",
            "label": match,
            "cmdline": preview,
            "steam_appid": appid,
            "kind": "process",
            "score": score,
        }
        prev = by_match.get(key)
        if prev is None or candidate["score"] > prev["score"]:
            by_match[key] = candidate

    steam_rows = sorted(steam_games.values(), key=lambda r: (-r["score"], r["label"].lower()))
    proc_rows = sorted(by_match.values(), key=lambda r: (-r["score"], r["match"].lower()))
    rows = steam_rows + proc_rows
    for row in rows:
        row.pop("score", None)
    return rows


def _cmdline_has_appid(text: str, appid: str) -> bool:
    appid = appid.strip()
    if not appid:
        return False
    low = text.lower().replace("\\", "/")
    patterns = (
        rf"(?:steam[_-]?appid|appid)\s*[=:]\s*{re.escape(appid)}\b",
        rf"compatdata/{re.escape(appid)}(?:/|\b)",
        rf"-gameid\s+{re.escape(appid)}\b",
        rf"gameid[=:]{re.escape(appid)}\b",
    )
    return any(re.search(pat, low) for pat in patterns)


def match_rule(
    rules: list[dict[str, Any]],
    process_texts: list[str],
) -> dict[str, Any] | None:
    """Return the first matching rule, or None.

    Steam appids are checked before process substrings — more reliable for
    Proton/EAC titles with many helper processes.
    """
    if not rules or not process_texts:
        return None

    blob = "\n".join(process_texts).lower()
    for rule in rules:
        match = rule.get("match") or {}
        processes = match.get("process") or []
        appids = match.get("steam_appid") or []

        for appid in appids:
            if any(_cmdline_has_appid(t, str(appid)) for t in process_texts):
                return rule

        for needle in processes:
            n = str(needle).lower().strip()
            if n and n in blob:
                return rule

    return None


def get_watcher_status() -> dict[str, Any]:
    with _STATUS_LOCK:
        status = dict(_STATUS)
    status["active_profile"] = get_active_profile()
    rules = load_game_rules()
    status["enabled"] = bool(rules.get("enabled"))
    status["poll_seconds"] = rules.get("poll_seconds", 2)
    status["default_profile"] = rules.get("default_profile")
    return status


def _set_status(**kwargs: Any) -> None:
    with _STATUS_LOCK:
        _STATUS.update(kwargs)


def tick(
    rules_data: dict[str, Any] | None = None,
    *,
    process_texts: list[str] | None = None,
    apply: bool = True,
) -> dict[str, Any]:
    """One watcher iteration. Returns status snapshot after the tick."""
    rules_data = rules_data if rules_data is not None else load_game_rules()
    enabled = bool(rules_data.get("enabled"))
    _set_status(enabled=enabled)

    if not enabled:
        _set_status(active_game=None, last_match=None)
        return get_watcher_status()

    texts = process_texts if process_texts is not None else scan_processes()
    matched = match_rule(rules_data.get("rules") or [], texts)

    target_profile: str | None = None
    active_game: str | None = None

    if matched:
        target_profile = str(matched.get("profile") or "").strip() or None
        active_game = str(matched.get("name") or target_profile or "").strip() or None
        _set_status(
            active_game=active_game,
            last_match={
                "name": active_game,
                "profile": target_profile,
                "at": time.time(),
            },
        )
    else:
        default = rules_data.get("default_profile")
        if default:
            target_profile = str(default).strip() or None
            active_game = None
            _set_status(active_game=None, last_match=None)
        else:
            # Leave current profile alone (no thrash on desktop focus).
            _set_status(active_game=None, last_match=None)
            return get_watcher_status()

    if not target_profile:
        return get_watcher_status()

    with _STATUS_LOCK:
        last_applied = _STATUS.get("last_applied_profile")

    if target_profile == last_applied:
        return get_watcher_status()

    if not profile_exists(target_profile):
        _set_status(last_error=f"Profile not found: {target_profile}")
        return get_watcher_status()

    if apply and not find_dongle_path():
        _set_status(last_error="Dongle not connected; will retry")
        return get_watcher_status()

    try:
        activate_profile(target_profile, apply=apply)
        _set_status(
            last_applied_profile=target_profile,
            last_error=None,
            active_game=active_game,
        )
    except Exception as e:
        _set_status(last_error=str(e))

    return get_watcher_status()


def _watcher_loop(*, log: bool = False) -> None:
    _set_status(running=True)
    last_applied = None
    last_error = None
    try:
        while not _WATCHER_STOP.is_set():
            rules = load_game_rules()
            poll = int(rules.get("poll_seconds") or 2)
            try:
                status = tick(rules)
            except Exception as e:
                _set_status(last_error=str(e))
                status = get_watcher_status()

            if log:
                applied = status.get("last_applied_profile")
                err = status.get("last_error")
                game = status.get("active_game")
                if applied != last_applied:
                    if applied:
                        print(
                            f"[gamegent-daemon] activated profile “{applied}”"
                            + (f" (game: {game})" if game else ""),
                            flush=True,
                        )
                    last_applied = applied
                if err and err != last_error:
                    print(f"[gamegent-daemon] {err}", flush=True)
                    last_error = err
                elif not err:
                    last_error = None

            _WATCHER_STOP.wait(timeout=max(1, poll))
    finally:
        _set_status(running=False)


def try_acquire_watcher_lock() -> bool:
    """Exclusive lock so only one watcher (daemon or Flask) runs."""
    global _WATCHER_LOCK_FD
    if _WATCHER_LOCK_FD is not None:
        return True
    os.makedirs(CONFIG_DIR, exist_ok=True)
    fd = os.open(WATCHER_LOCK_FILE, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return False
    os.ftruncate(fd, 0)
    os.write(fd, f"{os.getpid()}\n".encode())
    _WATCHER_LOCK_FD = fd
    return True


def watcher_lock_holder() -> int | None:
    """PID of the process holding the watcher lock (any process), else None."""
    import fcntl
    try:
        fd = os.open(WATCHER_LOCK_FILE, os.O_RDONLY)
    except OSError:
        return None
    try:
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
        return None
    except OSError:
        pid = os.read(fd, 32).strip()
        return int(pid) if pid.isdigit() else -1
    finally:
        os.close(fd)


def release_watcher_lock() -> None:
    global _WATCHER_LOCK_FD
    fd = _WATCHER_LOCK_FD
    _WATCHER_LOCK_FD = None
    if fd is None:
        return
    try:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass
    try:
        os.close(fd)
    except OSError:
        pass


def start_game_watcher() -> bool:
    """Start background watcher thread (idempotent). Returns False if another watcher holds the lock."""
    global _WATCHER_THREAD
    if _WATCHER_THREAD and _WATCHER_THREAD.is_alive():
        return True
    if not try_acquire_watcher_lock():
        return False
    _WATCHER_STOP.clear()
    _WATCHER_THREAD = threading.Thread(
        target=_watcher_loop,
        name="gamegent-game-watcher",
        daemon=True,
    )
    _WATCHER_THREAD.start()
    return True


def stop_game_watcher(timeout: float = 2.0) -> None:
    """Stop background watcher (for tests / shutdown)."""
    global _WATCHER_THREAD
    _WATCHER_STOP.set()
    thread = _WATCHER_THREAD
    if thread and thread.is_alive():
        thread.join(timeout=timeout)
    _WATCHER_THREAD = None
    _set_status(running=False)
    release_watcher_lock()


def run_watcher_forever(*, foreground: bool = True) -> None:
    """Block forever running only the game→profile watcher (no Flask/UI)."""
    import signal

    if not try_acquire_watcher_lock():
        raise SystemExit(
            "Another GameGent watcher is already running "
            "(gamegent daemon, app, or serve). Stop it first."
        )

    def _stop(_signum=None, _frame=None):
        print("[gamegent-daemon] stopping…", flush=True)
        _WATCHER_STOP.set()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    rules = load_game_rules()
    print(
        "[gamegent-daemon] watching for game→profile switches "
        f"(enabled={bool(rules.get('enabled'))}, poll={rules.get('poll_seconds', 2)}s)",
        flush=True,
    )
    if not rules.get("enabled"):
        print(
            "[gamegent-daemon] auto-switch is disabled in game_rules.json — "
            "enable it in the Profiles UI or set \"enabled\": true",
            flush=True,
        )

    _WATCHER_STOP.clear()
    try:
        _watcher_loop(log=foreground)
    finally:
        release_watcher_lock()
        print("[gamegent-daemon] stopped", flush=True)


def reset_watcher_state() -> None:
    """Clear debounce state (tests)."""
    with _STATUS_LOCK:
        _STATUS.update({
            "active_game": None,
            "last_match": None,
            "last_applied_profile": None,
            "last_error": None,
        })
