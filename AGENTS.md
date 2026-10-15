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
- `POST /api/config/autosave` — UI edits: save working config **and active profile**, push only changed sections (`core/profiles.py:autosave_config`); 409 if the active profile changed since the client loaded it. `POST /api/config` also mirrors into the active profile.
- UI polls status (~2s) and mappings (~4s) while connected; skips overwrite if config is dirty
- Game watcher runs in Flask (serve/app) **or** standalone `gamegent daemon` (lock-shared; only one at a time)
- User systemd unit: `gamegent-daemon.service` (installed by `./install.sh`)

## Live tester note

WebKitGTK’s browser Gamepad API is unreliable here: it may pick GameSir mouse passthrough (`js0`) first, and it collapses trigger/hat axes into the 4 stick axes. The tester therefore polls `GET /api/gamepad`, which reads `/dev/input/js*` (xpad layout) and skips mouse/keyboard nodes.

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

## Goal — Razer Viper Mini software

GameGent is the reference for a **similar standalone Linux app for the user's Razer Viper Mini** (`1532:008A`), which the user intends to build. Full background: `doc/handoff-razer-viper-mini.md`.

**User need:** Synapse Hypershift: side button + scroll → spam `E` (Apex loot), without Synapse on Linux.

**Known state:**
- DPI / poll rate / logo RGB: already in OpenRazer (since ~2.9.0), so reuse its protocol rather than re-deriving it.
- Onboard / Hypershift remaps: not supported in OpenRazer for the Viper Mini. This is the part to reverse-engineer (compare to the Basilisk Ultimate remap, class `0x02` / cmd `0x0c`, [openrazer#2845](https://github.com/openrazer/openrazer/issues/2845); [RE wiki](https://github.com/openrazer/openrazer/wiki/Reverse-Engineering-USB-Protocol)).
- Stopgap if needed: host-side [input-remapper](https://github.com/sezanzeb/input-remapper) Hypershift.

GameGent remap docs remain the local RE pattern reference: `doc/remapping.md`, `doc/hex_protocol.md`, `core/read_remap.py`.
