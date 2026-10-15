## Dev

```bash
# Terminal 1: Flask API
./venv/bin/python web/app.py

# Terminal 2: React dev server (hot reload, proxies /api to Flask)
cd web/react-app && npm run dev

# Production build
cd web/react-app && npm run build
# Flask auto-serves dist/ when it exists
# gamegent app rebuilds dist automatically when src is newer

# Desktop app (pywebview + local Flask on 127.0.0.1:5000)
./venv/bin/pip install -r requirements.txt
# Arch: sudo pacman -S python-gobject webkit2gtk-4.1
# venv/pyvenv.cfg: include-system-site-packages = true
gamegent app
```

## Stack

- **Backend**: Flask (port 5000), REST API at `/api/*`
- **Frontend**: React + TypeScript + Vite
- **Desktop**: pywebview wrapping Flask + `dist/`
- **State**: Zustand (`configStore.ts`)
- **API**: TanStack Query (`hooks/useApi.ts`)

## Notable APIs

- `GET /api/status` — dongle connected? (`find_dongle_path`)
- `GET /api/gamepad` — live Linux joystick state for the in-app tester (`core/gamepad_read.py`)
- `POST /api/mappings/read` — onboard remaps (`read_button_mappings`); 503 if disconnected
- `GET/POST /api/profiles`, `POST /api/profiles/activate`, `DELETE /api/profiles/<name>` — software profiles (`core/profiles.py`)
- `GET/POST /api/game-rules`, `GET /api/game-rules/status`, `GET /api/game-rules/processes` — game→profile auto-switch + process picker (`core/game_watcher.py`)
- `POST /api/config/apply` — push working config to hardware (`core/apply_config.py`)
- `GET /api/gamepad/stream` — same data as server-sent events, pushed on change (the UI uses it, falls back to polling `/api/gamepad`)
- `GET /api/gamepad` — live tester: vendor state report when the dongle is present (`source: vendor`, all physical buttons incl. L4/R4/T1–T3/C1–C4, `core/raw_state.py`), else `/dev/input/js*` (`source: js`)
- `GET /api/device` — battery, firmware, MAC (`core/device_info.py`); `POST /api/reset` — factory-reset config sections (`core/defaults.py`)
- `POST /api/config/autosave` — UI edits: save working config **and active profile**, push only changed sections (`core/profiles.py:autosave_config`); 409 if the active profile changed since the client loaded it. `POST /api/config` also mirrors into the active profile.
- UI polls status (~2s) and mappings (~4s) while connected; skips overwrite if config is dirty
- Game watcher runs in Flask (serve/app) **or** standalone `gamegent daemon` (lock-shared; only one at a time)
- User systemd unit: `gamegent-daemon.service` (installed by `./install.sh`)

## Live tester note

WebKitGTK’s browser Gamepad API is unreliable here: it may pick GameSir mouse passthrough (`js0`) first, and it collapses trigger/hat axes into the 4 stick axes. The tester therefore polls `GET /api/gamepad`: the dongle's vendor state report first (it also shows L4/R4/T1–T3/C1–C4, which XInput never sees), falling back to `/dev/input/js*` (xpad layout, skipping mouse/keyboard nodes).

## Remap read protocol (short)

```
OUT 07 05 05 02 00 [button]   # leading 00 required
IN  06 13 05 02 …
```

Details: `doc/remapping.md`, `doc/hex_protocol.md`, `core/read_remap.py`.

## Lint/Check

```bash
cd web/react-app && npm run typecheck && npx eslint .
```
