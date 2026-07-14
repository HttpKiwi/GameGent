# GameGent — GameSir Tarantula Pro CLI

Native Linux tool to configure GameSir Tarantula Pro controllers via USB HID.
No Windows VM, no proprietary DLLs.

Core HID I/O uses Python 3. The web UI / desktop app additionally need Flask,
React (Node), and optionally pywebview (see Desktop App below).

## Quick Start

```bash
./install.sh                              # ~/.local/bin/gamegent + .desktop entry
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
gamegent status                           # Read current controller state
gamegent read-mappings                    # Read onboard button remaps
gamegent rumble --fire 100 --duration 500
```

### Udev Rule (avoid sudo)

`/etc/udev/rules.d/99-gamesir.rules`:
```
KERNEL=="hidraw*", ATTRS{idVendor}=="3537", ATTRS{idProduct}=="103e", MODE="0666"
```
Then: `sudo udevadm control --reload-rules && sudo udevadm trigger`

## Commands

### Status

```bash
python3 main.py status           # Human-readable state
python3 main.py status --json    # JSON export
python3 main.py status --raw     # Include raw register dumps
```

### Rumble

```bash
python3 main.py rumble --set 80 --right 60    # Set grip rumble level
python3 main.py rumble --fire 100             # Burst both motors
python3 main.py rumble --fire 100 --fire-right 50 --duration 1000
```

### Lighting

```bash
# Mode
python3 main.py light off|static|breathing|colorful|rainbow|radar \
    --brightness 80 --speed 50

# Panel LED
python3 main.py color 0          # Red (hue 0-360°)
python3 main.py led panel 240    # Blue panel
python3 main.py led home 120     # Green home button

# ABXY layout
python3 main.py layout xbox
python3 main.py layout switch
```

### Face Button LEDs

```bash
# All 4 at once
python3 main.py face all --a-hue 0 --b-hue 120 --x-hue 240 --y-hue 60

# Single button (persists others via config cache)
python3 main.py face a 0
python3 main.py face b 120
python3 main.py face x 240
python3 main.py face y 60

# Home button LED
python3 main.py face home 200
python3 main.py led home 200     # same thing
```

### Sticks

```bash
# Modes
python3 main.py stick left native --circle --deadzone-min 5 --curve linear
python3 main.py stick right mouse --x-sens 60 --mouse-dpi 75

# Keyboard mode with WASD
python3 main.py stick left keyboard --overlap 65 \
    --kbd-up 26 --kbd-down 22 --kbd-left 4 --kbd-right 7

# Clone mode
python3 main.py stick left clone

# Curves
python3 main.py stick left native --curve expo --curve-intensity 60
python3 main.py stick left native --curve s-curve --deadzone-min 10 --deadzone-max 80
```

Modes: `native | mouse | keyboard | clone`
Curves: `linear | expo | s-curve`

### Gyro / Motion Aim

```bash
# Mouse aim, hold to activate
python3 main.py gyro mouse --motion aim --method hold --button c1 --axis yaw

# Tilt wheel, always on
python3 main.py gyro mouse --motion tilt --method always --button rb

# Keyboard output with custom directional keys
python3 main.py gyro keyboard --motion aim --method hold --button lt \
    --overlap 70 --kb-up key:w --kb-down key:s \
    --kb-left key:a --kb-right key:d

# Sensitivity, deadzones, curves, invert
python3 main.py gyro mouse --x-sens 75 --y-sens 60 \
    --deadzone-min 10 --deadzone-max 80 \
    --antideadzone-min 5 --antideadzone-max 90 \
    --curve expo --curve-intensity 60 \
    --invert-x --invert-y
```

Output modes: `mouse | left_stick | right_stick | keyboard`
Motion modes: `aim | tilt`
Methods: `off | hold | press | always`
Axis: `yaw | roll | global`
Activate button: `c1 c2 c3 c4 t1 t2 t3 l4 r4 a b x y lb lt l3 rb rt r3 back start`

Keyboard direction targets: `key:X` (scancode), `mouse:scroll_up`, `controller:lt`, `unbind`

### Button Remapping

```bash
gamegent map c1 key:enter          # C1 → Enter key
gamegent map l4 controller:a       # L4 → A button
gamegent map r4 mouse:left_click   # R4 → left click
gamegent map t1 unbind             # T1 → disabled

# Read remaps currently stored on the controller
gamegent read-mappings             # Human-readable
gamegent read-mappings --json      # JSON {source: target}
gamegent read-mappings --raw       # Include raw HID response packets
```

Source buttons: `c1 c2 c3 c4 t1 t2 t3 l4 r4` (plus face/bumper IDs when reading)
Targets: `key:X`, `controller:X`, `mouse:X`, `unbind`

Onboard remaps are readable via `07 05 05 02 00 [button_index]` (see
[`doc/remapping.md`](doc/remapping.md) and [`doc/hex_protocol.md`](doc/hex_protocol.md)).
Identity mappings on face buttons (`a→a`) and native report `14 01` are treated as unmapped.

### Config

```bash
python3 main.py config --show             # Show full config
python3 main.py config --set stick_left.mode=keyboard
python3 main.py config --get stick_left.deadzone_min
```

## Button Reference

**Remappable source buttons** (extra back buttons):

| Name | Hex  | Name | Hex  |
|------|------|------|------|
| l4   | 0x24 | r4   | 0x25 |
| t1   | 0x26 | t2   | 0x27 |
| t3   | 0x28 | c1   | 0x29 |
| c2   | 0x2a | c3   | 0x2b |
| c4   | 0x2c |      |      |

**Target controller buttons** (face buttons, bumpers, etc.):

| Name   | Hex  | Name     | Hex  |
|--------|------|----------|------|
| a      | 0x01 | b        | 0x00 |
| x      | 0x03 | y        | 0x02 |
| lb     | 0x04 | rb       | 0x07 |
| lt     | 0x05 | rt       | 0x08 |
| l3     | 0x06 | r3       | 0x09 |
| back   | 0x0a | start    | 0x0b |
| dpad_up | 0x0e | dpad_down | 0x0f |
| dpad_left | 0x0c | dpad_right | 0x0d |
| screenshot | 0x2d |

## Known Limitations

- Remap changes onboard are only visible via polling (no USB push notification)
- Profile switching / multi-profile storage is not yet implemented
- Face button LED colors require all 4 sent at once (cached via config for single-button mode)
- Device must be unbound from VM passthrough before use
- `gamegent` must run via the project venv (`./venv/bin/…`); the launcher re-execs into it (do not use system `pip` on Arch)

## Desktop App

```bash
./install.sh                 # Symlink + .desktop launcher
./venv/bin/pip install -r requirements.txt
gamegent app                 # Opens native desktop window
```

What it does:
- Starts Flask on `127.0.0.1:5000` and opens a pywebview window on that URL
- Rebuilds `web/react-app/dist` automatically when React source is newer than the build
- Polls `GET /api/status` (~2s) for a connection indicator
- While connected, polls `POST /api/mappings/read` (~4s) and syncs remaps into the UI when config is not dirty

App menu entry: **GameGent**. Browser UI: `gamegent serve` (add `--prod` to build + serve dist only).

### Arch Linux notes

pywebview needs a system GUI backend, and the venv must see system site packages:

```bash
sudo pacman -S python-gobject webkit2gtk-4.1   # or: python-pyqt6
# venv/pyvenv.cfg must have:
#   include-system-site-packages = true
./venv/bin/pip install -r requirements.txt
gamegent app
```

Do **not** run `pip install pywebview` against system Python (PEP 668 / externally managed).

Config traffic for remaps lives on HID endpoint **0x01 OUT / 0x82 IN** (`usbhid.data` in Wireshark), not the gamepad stream on 0x81.

## Project Structure

```
core/
  __init__.py          # Public API
  transport.py         # HID I/O (device discovery, read/write)
  hid_keycodes.py      # USB HID usage tables + remap packet builders
  config.py            # JSON config persistence (~/.config/gamegent/)
  lighting.py          # Lighting modes, color, layout, LEDs
  remap.py             # Button remap logic
  read_remap.py        # Read onboard remaps from hardware
  stick.py             # Stick config + curve presets
  rumble.py            # Grip rumble
  gyro.py              # Gyro/motion aim
  read_state.py        # Full controller state read
desktop/
  app.py               # pywebview desktop launcher
web/
  app.py               # Flask API + React dist serving
  react-app/           # React + TypeScript UI
main.py                # CLI entry point
install.sh             # PATH symlink + .desktop install
doc/remapping.md       # Packet protocol reference
pcapng/                # Reference USB captures
```
