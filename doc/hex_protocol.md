# GameGent Hex Protocol Documentation

## General Function

GameGent is a native Linux tool for configuring the GameSir Tarantula Pro controller via USB HID. It communicates directly with the controller's USB HID interface using 32-byte packets to configure:

- Lighting modes and colors
- Stick behavior (native, mouse, keyboard, clone modes)
- Gyro/motion aim
- Button remapping (write + read), combos, and macros
- Trigger deadzones and hair trigger
- Rumble motors

The tool uses a vendor/product ID pair (3537:103e) to locate the hidraw device and sends configuration packets without requiring Windows or proprietary DLLs.

Config / remap traffic is on a **HID config interface** (EP 0x01 OUT, 0x82 IN). Gamepad input lives on EP 0x81 and is unrelated to remap read/write.
---

## Packet Structure Overview

All packets are 32 bytes. The first 4 bytes typically form a command header:
- **Byte 0**: Always `0x07` (command marker)
- **Byte 1**: Class/function identifier
- **Byte 2**: Subtype/parameter
- **Byte 3**: Operation (0x01=write, 0x02=read, 0x03=commit, 0x04=read response)

A commit packet `07 03 08 03` is typically sent after configuration changes to persist them.

---

## File-by-File Hex Structure Documentation

### core/transport.py

**Purpose**: Low-level HID I/O, device discovery, and packet transmission.

**Device Identification**:
- Vendor ID: `0x3537`
- Product ID: `0x103e`

**Key Functions**:

**Session Initialization** (`init_session`):
```
Packet 1: 01 00 [padding]
Packet 2: 07 03 0a 01 [padding]
Packet 3: 07 03 0a 01 [padding]
```
Switches device to configuration mode.

**Page Register Read** (`read_page_register`):
```
Header: 07 [class] [subtype] 02 [reg_lo] [reg_hi]
```
Reads a specific register from a configuration page (little-endian register word).

**Button Remap Register Read** (`read_button_remap_register`):
```
Header: 07 05 05 02 00 [button_index]
```
GameSir remap reads use a **leading zero** before the button index (not LE `[btn] 00`).
Responses must be matched with header `06 13 05 02` (see `core/read_remap.py`).

**Typed Register Read** (`read_typed_register`):
```
Header: 07 [class] [subtype] [param]
```
Reads using feature-specific header.

---

### core/lighting.py

**Purpose**: Lighting modes, colors, ABXY layout, per-LED colors, face button LEDs.

**Lighting Modes**:
```
off:       0x00
static:    0x01
breathing: 0x02
colorful:  0x03
rainbow:   0x04
radar:     0x05
```

**Set Hardware State** (`set_hardware_state`):
```
Header: 07 06 07 01
Byte 4:  brightness (0-100)
Byte 5:  speed (0-100)
Byte 6:  mode byte
Bytes 7-8: 0x00
```

**Set Color** (`generate_color_packet`):
```
Header: 07 10 07 03
Byte 4:  0x04 (zone selector)
Byte 5:  compressed hue (0-255, from 0-360°)
Byte 6:  0x64 (saturation, fixed at 100)
Byte 7:  0x32 (lightness, fixed at 50)
```

**ABXY Layout** (`set_abxy_layout`):
```
Header: 07 09 09 01
Byte 6:  0x01 = xbox, 0x02 = switch
```

**Per-LED Color** (`set_led_color`):
```
Header: 07 10 07 03
Byte 4:  0x00 = home, 0x04 = panel
Byte 5:  compressed hue (0-255)
Byte 6:  saturation (0-100)
Byte 7:  lightness (0-100)
```

**Face Button Colors** (`_send_face_packet_from`):
```
Header: 07 10 07 03
Byte 4:  0x05 (face button zone)
Bytes 5-6:   A button (hue, saturation, lightness)
Bytes 8-10:  B button (hue, saturation, lightness)
Bytes 11-13: X button (hue, saturation, lightness)
Bytes 14-16: Y button (hue, saturation, lightness)
```

---

### core/stick.py

**Purpose**: Stick configuration (modes, curves, keyboard mapping, mouse DPI).

**Stick Modes**:
```
native:    0x00
mouse:     0x01
keyboard:  0x02
clone:     0x03
```

**Curve Presets** (coords are 6 bytes, curve_type is 1 byte):
```
linear:    coords=[0x14,0x10,0x35,0x32,0x55,0x54], curve_type=0x00
expo:      coords=[0x1b,0x17,0x35,0x32,0x4e,0x4d], curve_type=0x01
s-curve:   coords=[0x0e,0x1e,0x2c,0x32,0x4a,0x46], curve_type=0x02
```

**Targeting Packet** (`build_targeting_packet`):
```
Header: 07 0f 02 03
Byte 4:  stick_id (0=left, 1=right)
Byte 5:  overlap_percent (keyboard mode) or x_sensitivity
Byte 6:  y_sensitivity
Byte 7:  0x50 (fixed)
Bytes 8-9: 0x00 (padding)
Byte 10: mode byte
Byte 11: 0x01 (fixed)
Byte 12: mouse_x_dpi (mouse mode only)
Byte 13: mouse_y_dpi (mouse mode only)
```

**Geometry Packet** (`build_geometry_packet`):
```
Header: 07 18 02 01
Bytes 4-10: stick_id flags (0x01 at byte 4 for right stick)
Byte 11: 0x01=circle, 0x00=square
Byte 12: 0x32 (fixed)
Byte 13: deadzone_min (0-100)
Byte 14: antideadzone_min (0-100)
Bytes 15-20: curve coords (6 bytes)
Byte 21: deadzone_max (0-100)
Byte 22: antideadzone_max (0-100)
Byte 23: curve_type (0x00=linear, 0x01=expo, 0x02=s-curve)
Byte 24: curve_intensity (0-100)
```

**Keyboard Mapping Packet** (`build_keyboard_packet`):
```
Header: 07 13 05 01
Bytes 4-9: 0x00 (padding)
Byte 10: zone_index
  0x10=left, 0x11=right, 0x12=up, 0x13=down
  0x18=overlap_left, 0x19=overlap_right
  0x1a=overlap_up, 0x1b=overlap_down
Bytes 11-16: struct (KEYBOARD_ZONE_STRUCT or KEYBOARD_OVERLAP_STRUCT)
Byte 17: scancode (HID usage ID)
```

**Keyboard Zone Structs**:
```
KEYBOARD_ZONE_STRUCT:     [0x00, 0x00, 0x01, 0x02, 0x02, 0x00]
KEYBOARD_OVERLAP_STRUCT:   [0x00, 0x00, 0x01, 0x02, 0x01, 0x02]
```

**Commit Packet**:
```
07 03 08 03 [28 bytes of 0x00]
```

---

### core/gyro.py

**Purpose**: Gyro/motion aim configuration (output modes, motion modes, activation methods).

**Gyro Output Modes**:
```
left_stick:  0x01
right_stick: 0x02
keyboard:    0x03
mouse:       0x04
```

**Motion Modes**:
```
aim:  0x00
tilt: 0x01
```

**Activation Methods**:
```
off:     0x00
press:   0x01
hold:    0x02
always:  0x03
```

**Axis Modes**:
```
global: 0x00
yaw:    0x01
roll:   0x02
```

**Gyro Geometry Packet** (`build_gyro_geometry`):
```
Header: 07 16 04 01
Bytes 4-9: 0x00 (padding)
Byte 10: x_sensitivity (0-100)
Byte 11: deadzone_min (0-100)
Byte 12: antideadzone_min (0-100)
Bytes 13-18: curve coords (6 bytes)
Byte 19: deadzone_max (0-100)
Byte 20: antideadzone_max (0-100)
Byte 21: curve_type (0x00=linear, 0x01=expo, 0x02=s-curve)
Byte 22: curve_intensity (0-100)
```

**Gyro Targeting Packet** (`build_gyro_targeting`):
```
Header: 07 0e 04 03
Byte 4:  x_sensitivity (0-100)
Byte 5:  y_sensitivity (0-100)
Byte 6:  output_mode byte
Byte 7:  motion_mode byte
Byte 8:  axis_mode byte
Byte 9:  activate_button (button index)
Byte 10: activate_method byte
Bytes 11-12: 0x32 (fixed)
Byte 13: 0x01=invert_x, 0x00=normal
Byte 14: 0x01=invert_y, 0x00=normal
```

**Gyro Keyboard Direction Zones**:
```
up:    0x20
down:  0x21
left:  0x22
right: 0x23
```

**Gyro Keyboard Packet** (via `resolve_gyro_direction_packet`):
```
Header: 07 13 05 01
Bytes 4-9: 0x00 (padding)
Byte 10: zone_index (0x20-0x23)
Bytes 11-16: struct (depends on target type)
Bytes 17-31: payload (16 bytes, varies by target)
```

**Commit Packet**:
```
07 03 08 03 [28 bytes of 0x00]
```

---

### core/remap.py

**Purpose**: Button remapping, combos, macros.

**Remap Packet Structure** (`build_remap_packet`):
```
Header: 07 13 05 01
Bytes 4-7: 0x00 (padding)
Bytes 8-9: 0x00 (padding)
Byte 10: button_index (physical button to remap)
Bytes 11-12: 0x00 (padding)
Byte 13: 0x01 (flag)
Bytes 14-15: report_type
Bytes 16-31: payload (16 bytes)
```

**Report Types**:
```
REPORT_KEYBOARD:   0x02 0x02
REPORT_MOUSE:      0x03 0x04
REPORT_CONTROLLER: 0x01 0x01
REPORT_UNBIND:     0x00 0x00
REPORT_COMBO_2KEY: 0x01 0x02
REPORT_COMBO_3KEY: 0x01 0x03
REPORT_TURBO:      0x04 0x04
```

**Keyboard Remap Payload**:
```
Byte 0: 0x00
Byte 1: usage_id (HID keyboard usage)
Bytes 2-15: 0x00
```

**Mouse Button Payload**:
```
Bytes 0-2: 0x00
Byte 3: button_bitfield (0x01=left, 0x02=right, 0x04=middle, 0x08=button5, 0x10=button4)
Bytes 4-15: 0x00
```

**Mouse Scroll Payload**:
```
Bytes 0-1: 0x00
Byte 2: scroll_value (0x01=up, 0xff=down)
Byte 3: 0x00
Bytes 4-15: 0x00
```

**Controller Button Payload**:
```
Byte 0: target_button_id
Bytes 1-15: 0x00
```

**Turbo Flags** (injected at bytes 11-13):
```
Byte 11: continuous_toggle (0x00=off, 0x01=on)
Byte 12: turbo_mode (0x02=on, 0x00=off)
Byte 13: rate_hz (1-255, when turbo on)
```

**Combo Packet** (`combo_packet`):
```
Header: 07 13 05 01
Bytes 4-9: 0x00 (padding)
Byte 10: button_index
Bytes 11-12: 0x00 (padding)
Byte 13: 0x01 (flag)
Bytes 14-15: report_type (depends on key types)
Bytes 16-31: payload (2 or 3 key IDs, padded to 16 bytes)
```

**Combo Report Types**:
```
Controller keys: 0x01 0x02 (2 keys) or 0x01 0x03 (3 keys)
Keyboard keys:    0x02 0x03 (2 keys) or 0x02 0x04 (3 keys)
Mouse keys:       0x03 0x04 (always 4-byte bitfield)
```

**Macro Init Packet** (`build_macro_init_packet`):
```
Header: 07 13 05 01
Bytes 4-9: 0x00 (padding)
Byte 10: button_index
Bytes 11-12: 0x00 (padding)
Byte 13: 0x01 (flag)
Bytes 14-15: 0x00 0x00 (report type for macro init)
Bytes 16-31: 0x00 (padding)
```

**Macro Step Packet** (`build_macro_step_packet`):
```
Header: 07 13 01 01
Byte 4:  button_index
Byte 5:  step_index (0-based)
Byte 6:  macro_type (0x01=normal, 0x02=hold)
Byte 7:  loop_flag (0x01=loop, 0x00=once)
Bytes 8-9: 0x00 (padding)
Byte 10: 0x01 (controller button type)
Byte 11: 0x01 (action type)
Byte 12: target_button_id
Bytes 13-14: 0x00 (padding)
Byte 15: 0x00
Bytes 16-17: press_ms (big-endian 16-bit)
Bytes 18-19: release_ms (big-endian 16-bit)
Bytes 20-31: 0x00 (padding)
```

**Combo/Macro Enable Packet**:
```
Header: 07 13 01 01
Byte 4: button_index
Byte 5: 0xff
Bytes 6-31: 0x00 (padding)
```

**Commit Packet**:
```
07 03 08 03 [28 bytes of 0x00]
```

---

### core/read_remap.py

**Purpose**: Read onboard button remaps from hardware (discovered via GameSir app PCAP).

**USB context** (Windows USBPcap / Wireshark):
- Config channel: EP **0x01 OUT**, EP **0x82 IN**, field `usbhid.data`
- Gamepad noise: EP **0x81** (ignore when analyzing remaps)

**Read command** (`read_button_remap_register` in `transport.py`):
```
OUT: 07 05 05 02 00 [button_index] [zeros…]
```
Not little-endian: must be `00 [btn]`, **not** `[btn] 00`.

**Response**:
```
IN: 06 13 05 02 …
```
Linux hidraw returns a 64-byte report. Match `d[0]==0x06` and `d[1:4]==13 05 02`.

**Decode**:
- Native / stock face mapping marker: `14 01` → no custom remap
- Report types same as writes: `01 01` controller, `02 02` keyboard, `03 04` mouse, `00 00` unbind
- Payload follows the report type (same layout as write payloads)
- Identity face mappings (`a→a`) are filtered out as “unmapped”

**CLI / API**:
- `gamegent read-mappings [--json|--raw]`
- `POST /api/mappings/read` → `{ key_mappings: {…} }`
- `GET /api/status` → `{ connected: bool, path: string|null }`

---

### core/rumble.py

**Purpose**: Grip rumble motor control.

**Set Rumble Level** (`set_rumble_level`):
```
Header: 07 09 06 01
Byte 4:  left_pct (0-100)
Byte 5:  right_pct (0-100)
Bytes 6-31: 0x00 (padding)
```

**Fire Rumble** (`fire_rumble`):
```
Header: 07 07 0a 04
Byte 4:  left_pct (0-100)
Byte 5:  right_pct (0-100)
Bytes 6-31: 0x00 (padding)
```
This packet is sent repeatedly in a loop for the duration, then sent with 0,0 to stop.

**Read Rumble Level** (`read_rumble_level`):
```
Command: 07 09 06 02
Response: bytes 4-5 contain left/right percentages
```

**Commit Packet**:
```
07 03 08 03 [28 bytes of 0x00]
```

---

### core/trigger.py

**Purpose**: Trigger deadzones, hair trigger, response curves.

**Hair Trigger Modes**:
```
off:       0x00
adaptive:  0x01
fixed:     0x02
```

**Trigger Config Packet** (`build_trigger_packet`):
```
Header: 07 13 03 01
Byte 4:  trigger_id (0=left, 1=right)
Byte 5:  hair_mode byte
Byte 6:  hair_trigger_begin (0-100, default: 10 for left, 20 for right)
Byte 7:  hair_trigger_end (0-100, default: 30 for left, 5 for right)
Byte 8:  deadzone_begin (0-100)
Byte 9:  antideadzone_begin (0-100)
Bytes 10-15: curve coords (6 bytes)
Byte 16: deadzone_end (0-100)
Byte 17: antideadzone_end (0-100)
Byte 18: curve_type (0x00=linear, 0x01=expo, 0x02=s-curve)
Byte 19: curve_intensity (0-100)
Bytes 20-31: 0x00 (padding)
```

**Commit Packet**:
```
07 03 08 03 [28 bytes of 0x00]
```

---

### core/hid_keycodes.py

**Purpose**: HID keycode mappings and packet builders.

**Keyboard Usage IDs** (USB HID Usage Tables §10, page 0x07):
- Letters: a=0x04, b=0x05, ..., z=0x1d
- Numbers: 1=0x1e, 2=0x1f, ..., 0=0x27
- Modifiers: left_ctrl=0xe0, left_shift=0xe1, left_alt=0xe2, left_gui=0xe3
- Function keys: f1=0x3a, f2=0x3b, ..., f12=0x45
- Navigation: enter=0x28, escape=0x29, backspace=0x2a, tab=0x2b, space=0x2c
- Arrows: up=0x52, down=0x51, left=0x50, right=0x4f

**Mouse Button Bitfield**:
```
left_click:   0x01
right_click:  0x02
middle_click: 0x04
button_5:     0x08
button_4:     0x10
```

**Mouse Scroll**:
```
scroll_up:   0x01
scroll_down: 0xff
```

**Controller Button IDs** (target for remapping):
```
b:          0x00
a:          0x01
y:          0x02
x:          0x03
lb:         0x04
lt:         0x05
l3:         0x06
rb:         0x07
rt:         0x08
r3:         0x09
back:       0x0a
start:      0x0b
dpad_left:  0x0c
dpad_right: 0x0d
dpad_up:    0x0e
dpad_down:  0x0f
screenshot: 0x2d
```

**Controller Source Buttons** (remappable physical buttons):
```
l4: 0x24
r4: 0x25
t1: 0x26
t2: 0x27
t3: 0x28
c1: 0x29
c2: 0x2a
c3: 0x2b
c4: 0x2c
```

---

### core/read_state.py

**Purpose**: Reading current controller state from device.

**Read Lighting**:
```
Command: 07 06 07 02
Response: bytes 4-6 = (brightness, speed, mode)
```

**Read Color**:
```
Command: 07 10 07 04
Response: bytes 5-7 = (hue, saturation, lightness)
```

**Read Stick Targeting**:
```
Command: 07 0f 02 04 [stick_id]
Response: full targeting packet data
```

**Read Stick Geometry**:
```
Command: 07 18 02 02 [optional stick_id flags]
Response: full geometry packet data
```

**Read Trigger**:
```
Command: 07 05 03 02 [trigger_id]
Response: bytes 4-19 contain trigger config
```

**Read Layout**:
```
Command: 07 05 09 02
Response: byte 6 = 0x01 (xbox) or 0x02 (switch)
```

**Page Register Reads** (for full state dump):
```
Command: 07 [class] [subtype] 02 [reg_lo] [reg_hi]
Response: bytes 4+ contain register data
```

---

### core/config.py

**Purpose**: JSON configuration persistence (~/.config/gamegent/config.json).

No hex structures - this file handles JSON serialization/deserialization of configuration state to cache settings like face button LED colors between sessions.

---

## Common Patterns

### Commit Packet
After most configuration changes, a commit packet is sent:
```
07 03 08 03 [28 bytes of 0x00]
```
This persists the changes to the controller's non-volatile memory.

### Session Initialization
Before reading state, a session is initialized:
```
01 00 [padding]
07 03 0a 01 [padding]
07 03 0a 01 [padding]
```

### Response Format
Read responses typically have:
- Byte 0: Report ID (usually 0x06)
- Byte 1: Class byte (echoed from command)
- Byte 2: Subtype (echoed from command)
- Byte 3: Operation (echoed from command)
- Bytes 4+: Data payload

### Padding
All packets are exactly 32 bytes. Unused bytes are padded with 0x00.
