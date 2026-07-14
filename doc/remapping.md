# GameGent — GameSir Tarantula Pro CLI

Configure GameSir Tarantula Pro controller via USB HID. No Windows DLL needed.

## Quick Start

```bash
python3 main.py status          # Read current controller state
python3 main.py rumble --fire 100 --duration 500   # Test vibration
python3 main.py light static --brightness 80 --speed 50
python3 main.py color 240       # Set hue to 240°
```

## Features

### Rumble

```bash
python3 main.py rumble --set 80 --right 60   # Set grip rumble level
python3 main.py rumble --fire 100            # Burst both motors
python3 main.py rumble --fire 100 --fire-right 50 --duration 1000
```

### Lighting

```bash
python3 main.py light off|static|breathing|colorful|rainbow|radar \
    --brightness 80 --speed 50
python3 main.py color 0          # Red (hue 0-360°)
```

### Stick Config

```bash
# Standard modes
python3 main.py stick left native --circle --deadzone-min 5 --curve linear
python3 main.py stick right mouse --x-sens 60 --mouse-dpi 75

# Keyboard mode with WASD
python3 main.py stick left keyboard --overlap 65 \
    --kbd-up 26 --kbd-down 22 --kbd-left 4 --kbd-right 7

# Clone mode
python3 main.py stick left clone
```

Modes: `native | mouse | keyboard | clone`
Curves: `linear | expo | s-curve` with `--curve-intensity`

### Gyro / Motion Aim

```bash
# Mouse aim with hold activation
python3 main.py gyro mouse --motion aim --method hold --button c1 --axis yaw

# Tilt wheel, always on
python3 main.py gyro mouse --motion tilt --method always --button rb

# Keyboard output with custom keys
python3 main.py gyro keyboard --motion aim --method hold --button lt \
    --overlap 70 --kb-up key:w --kb-down key:s \
    --kb-left key:a --kb-right key:d

# Sensitivity, deadzones, curves
python3 main.py gyro mouse --x-sens 75 --y-sens 60 \
    --deadzone-min 10 --deadzone-max 80 \
    --antideadzone-min 5 --antideadzone-max 90 \
    --curve expo --curve-intensity 60 --invert-x
```

Output modes: `mouse | left_stick | right_stick | keyboard`
Motion: `aim | tilt`
Methods: `off | hold | press | always`
Axis: `yaw | roll | global`
Activate button: `c1 c2 c3 c4 t1 t2 t3 l4 r4 a b x y lb lt l3 rb rt r3 back start`

Keyboard targets: `key:X` (scancode), `mouse:scroll_up`, `controller:lt`, `unbind`

### Button Remapping

```bash
python3 main.py map c1 key:enter          # C1 → Enter key
python3 main.py map l4 controller:a       # L4 → A button
python3 main.py map r4 mouse:left_click   # R4 → left click
python3 main.py map t1 unbind             # T1 → disabled

python3 main.py read-mappings             # Read onboard remaps
python3 main.py read-mappings --json
python3 main.py read-mappings --raw
```

Source buttons: `c1 c2 c3 c4 t1 t2 t3 l4 r4`
Targets: `key:X`, `controller:X`, `mouse:X`, `unbind`

### Config

```bash
python3 main.py config --show             # Show full config
python3 main.py config --set stick_left.mode=keyboard
```

### Status

```bash
python3 main.py status                    # Human-readable state
python3 main.py status --json             # JSON export
python3 main.py status --raw              # Include raw register dumps
```

## Project Structure

```
core/
  __init__.py          # Public API re-exports
  transport.py         # HID I/O (device discovery, read/write)
  hid_keycodes.py      # USB HID usage tables + remap packet builders
  config.py            # JSON config persistence
  lighting.py          # Lighting modes + color
  remap.py             # Button remap write logic
  read_remap.py        # Button remap read / decode
  stick.py             # Stick config + curve presets
  rumble.py            # Grip rumble set/fire/read
  gyro.py              # Gyro/motion aim config
  read_state.py        # Full controller state read
desktop/
  app.py               # pywebview desktop launcher
main.py                # CLI entry point (argparse)
pcapng/                # Reference USB captures (GameSir app)
```

## Remapping Packet Reference

### Writes (host → device)

All remap **write** commands are 32-byte HID output reports. Header `07 13 05 01`.

### Keyboard (`02 02`)

```
07 13 05 01 00 00 00 00 00 00 {BTN} 00 00 01 02 02 00 {KEY} [14 zeros]
```
Byte 10: button index. Byte 17: USB HID keyboard usage ID.

### Mouse (`03 04`)

```
07 13 05 01 00 00 00 00 00 00 {BTN} 00 00 01 03 04 00 00 00 {BT} [12 zeros]
```
Byte 19: button bitfield (0x01=left, 0x02=right, 0x04=middle, 0x08=B5, 0x10=B4).

### Mouse Scroll (`03 04`)

```
07 13 05 01 00 00 00 00 00 00 {BTN} 00 00 01 03 04 00 00 {WH} 00 [12 zeros]
```
Byte 18: scroll value (0x01=up, 0xFF=down).

### Controller (`01 01`)

```
07 13 05 01 00 00 00 00 00 00 {BTN} 00 00 01 01 01 {TGT} [15 zeros]
```
Byte 16: target controller button ID.

### Unbind (`00 00`)

```
07 13 05 01 00 00 00 00 00 00 {BTN} 00 00 01 00 00 [16 zeros]
```

### Reads (onboard remap state)

GameSir app traffic uses a **separate** page-gateway read (not `07 13 05 02`).

Observed on Windows USBPcap (filter `usbhid.data` on EP **0x01 OUT** / **0x82 IN** — not gamepad EP 0x81):

```
OUT: 07 05 05 02 00 {BTN} 00…   (32 bytes, zero-padded)
IN:  06 13 05 02 …               (64-byte report on Linux hidraw; report ID 0x06)
```

Important: the button index is at byte **5** of the OUT command (`00 {BTN}`), **not** little-endian `{BTN} 00`. Sending `{BTN} 00` returns empty/wrong payloads.

Linux hidraw response layout (verified against live device + PCAP):

| Offset | Meaning |
|--------|---------|
| 0 | Report ID `0x06` |
| 1–3 | `13 05 02` (remap response header) |
| 4 or 10 | Button index (layout varies by padding; GameGent matches either) |
| mid-packet | Report type `01 01` / `02 02` / `03 04` / `00 00`, or native `14 01` |
| payload | Same 16-byte payload shape as write packets |

Decode rules used by `core/read_remap.py`:
- `14 01` → native / not remapped → omit from output
- Face-button identity (`a→a`, `y→y`, …) → treat as unmapped
- `01 01` + target id → `controller:…`
- `02 02` / `03 04` → keyboard / mouse targets

CLI: `gamegent read-mappings [--json|--raw]`  
API: `POST /api/mappings/read` `{ "sync": false }` → `{ "key_mappings": {…} }` (503 if dongle missing)

## HID Keycode Reference

Common scancodes (full table in `core/hid_keycodes.py`):

| Key | Usage ID | Key | Usage ID |
|-----|----------|-----|----------|
| a   | 0x04     | n   | 0x11     |
| b   | 0x05     | o   | 0x12     |
| c   | 0x06     | p   | 0x13     |
| d   | 0x07     | q   | 0x14     |
| e   | 0x08     | r   | 0x15     |
| f   | 0x09     | s   | 0x16     |
| g   | 0x0a     | t   | 0x17     |
| h   | 0x0b     | u   | 0x18     |
| i   | 0x0c     | v   | 0x19     |
| j   | 0x0d     | w   | 0x1a     |
| k   | 0x0e     | x   | 0x1b     |
| l   | 0x0f     | y   | 0x1c     |
| m   | 0x10     | z   | 0x1d     |
| 1   | 0x1e     | F1  | 0x3a     |
| F5  | 0x3e     | F7  | 0x40     |
| enter | 0x28  | space | 0x2c   |
| left_ctrl | 0xe0 | left_shift | 0xe1 |

## Gyro Protocol Reference

### Targeting Packet (`07 0e 04 03`)

Layout B (mouse/stick mode):
```
byte 4:  x_sensitivity
byte 5:  y_sensitivity
byte 6:  method (0x04 = enabled, 0x00 = off)
byte 7:  motion (0x00 = aim, 0x01 = tilt)
byte 8:  output (0x00 = mouse, 0x01 = right_stick, 0x02 = left_stick)
byte 9:  activate button
byte 10: axis (0x02 = yaw, 0x01 = roll, 0x00 = global/disable)
byte 11-12: dpi (0x32 0x32)
byte 13: invert X (0x01 = on)
byte 14: invert Y (0x01 = on)
```

Layout A (keyboard mode): byte 6 = 0x03, byte 8 = 0x00, byte 4 = overlap%

### Geometry Packet (`07 16 04 01`)

```
byte 4-9:  reserved
byte 10:   x_sensitivity
byte 11:   deadzone_min
byte 12:   antideadzone_min
byte 13-18: curve coords (6 bytes)
byte 19:   deadzone_max
byte 20:   antideadzone_max
byte 21:   curve_type (0=linear, 1=expo, 2=s-curve)
byte 22:   curve_intensity
```

### Rumble Packets

Set level: `07 09 06 01 [left%] [right%]`, commit: `07 03 08 03`
Fire motor: `07 07 0a 04 [left%] [right%]` (burst-fire, stop with zeros)

### Lighting Packets

Mode: `07 06 07 01 [brightness] [speed] [mode]`
Color: `07 10 07 03 04 [hue_byte] [sat] [light]`

### Stick Packets

Targeting: `07 0f 02 03 [stick_id] [x_sens] [y_sens] [0x50] [00 00] [mode] [0x01] [dpi_x] [dpi_y]`
Geometry: `07 18 02 01 [7b offset] [circle] [0x32] [dz_min] [anti_min] [6b curve] [dz_max] [anti_max] [curve_type] [intensity]`

## Known Limitations

- Onboard remap changes have no USB event; clients must poll reads
- Multi-profile / profile-slot switching not yet implemented
- D-pad/trigger advanced profile tooling may still be incomplete vs GameSir app
