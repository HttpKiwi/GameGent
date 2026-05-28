# GameSir Controller Remapping Protocol

## Packet Format

All remapping commands are 32-byte (64 hex char) HID packets sent to the dongle
via `/dev/hidraw*`.

```
Offset  Size  Field            Notes
------  ----  ---------------  -----------------------------------------
 0       4    Command header    07 13 05 01 — fixed across all remap pkts
 4       4    Padding           00 00 00 00
 8       2    Padding           00 00
10       1    Button index      XX — physical button on the controller
11       2    Padding           00 00
 13       1    Flag              01 — always 1
 14       2    Report type       02 02 = keyboard | 03 04 = mouse
                                 01 01 = controller | 00 00 = unbind
 16      16    Payload           See below per report type
------  ----  ---------------  -----------------------------------------
Total: 32 bytes
```

---

## Button Index (byte 10)

Identifies which physical controller button is being remapped.
Observed button index codes:

- `c1` = `0x29`
- `c2` = `0x2a`
- `c3` = `0x2b`
- `c4` = `0x2c`
- `t1` = `0x26`
- `t2` = `0x27`
- `t3` = `0x28`
- `l4` = `0x24`
- `r4` = `0x25`

---

## Keyboard Report (`02 02`)

Byte 16 is padding (0x00). Byte 17 holds the USB HID keyboard usage ID (page 0x07).
All mappings use the standard [USB HID Usage Tables](https://www.usb.org/sites/default/files/hut1_5.pdf).

### Structure

```
Byte 16: 00 (padding)
Byte 17: XX (usage ID — the keycode)
Bytes 18–31: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 (padding)
```

### Template

```
07130501 00000000 0000 {BTN} 0000 01 0202 00{KEYCODE} [14 zero bytes]
                                    ^^            ^^
                                    report type   keycode at byte 17
```

{BTN} = physical button index (0x29 for C1)
{KEYCODE} = USB HID keyboard usage ID

---

## Mouse Report (`03 04`)

Bytes 17–31 encode a standard USB HID mouse report, padded with leading zeros.

### Structure

```
Byte 17–18: 00 00    (X movement — always zero for button remaps)
Byte 19:    WH       (wheel: 01 = scroll up, ff = scroll down)
Byte 20:    BT       (button bitfield — see below)
Bytes 21–31: 00...   (padding)
```

### Button Bitfield (byte 19)

| Mask   | Action         |
|--------|----------------|
| 0x01   | Left click     |
| 0x02   | Right click    |
| 0x04   | Middle click   |
| 0x08   | Button 5       |
| 0x10   | Button 4       |

### Template

```
07130501 00000000 0000 {BTN} 0000 01 0304 0000 00 {WH} {BT} [12 zero bytes]
                                      ^^^^            ^^   ^^
                                      report type     whl  btn
```

---

## Controller Report (`01 01`)

Maps a physical button to another controller button. Byte 16 holds the
target button ID directly (no leading pad byte).

### Structure

```
Byte 16: XX (target button ID — see table below)
Bytes 17–31: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 (padding)
```

### Target Button IDs

| ID   | Button       | ID   | Button       |
|------|------------- |------|------------- |
| 0x00 | B            | 0x0a | Back/Select  |
| 0x01 | A            | 0x0b | Start        |
| 0x02 | Y            | 0x0c | D-pad Left   |
| 0x03 | X            | 0x0d | D-pad Right  |
| 0x04 | LB           | 0x0e | D-pad Up     |
| 0x05 | LT           | 0x0f | D-pad Down   |
| 0x06 | L3           | 0x2d | Screenshot   |
| 0x07 | RB           |      |              |
| 0x08 | RT           |      |              |
| 0x09 | R3 (stick)   |      |              |

### Template

```
07130501 00000000 0000 {BTN} 0000 01 0101 {TARGET} [15 zero bytes]
                                    ^^         ^^
                                    type       target btn at byte 16
```

---

## Unbind Report (`00 00`)

Disables a physical button entirely.

### Template

```
07130501 00000000 0000 {BTN} 0000 01 0000 [16 zero bytes]
                                    ^^
                                    type
```

---

## Usage from Python

No need to manually map every key. Lookup tables are in `core/hid_keycodes.py`.

```python
from core import (
    KEYBOARD_USAGE, MOUSE_BUTTON, MOUSE_SCROLL, CONTROLLER_BUTTON,
    keyboard_packet, mouse_button_packet, mouse_scroll_packet,
    controller_packet, unbind_packet,
)

# Keyboard key
pkt = keyboard_packet(0x29, KEYBOARD_USAGE["enter"])

# Mouse
pkt = mouse_button_packet(0x29, MOUSE_BUTTON["left_click"])
pkt = mouse_scroll_packet(0x29, MOUSE_SCROLL["scroll_up"])

# Controller button
pkt = controller_packet(0x24, CONTROLLER_BUTTON["a"])

# Unbind
pkt = unbind_packet(0x24)
```

Or use the high-level `apply_mapping` in `core/protocol.py`:

```python
from core.protocol import apply_mapping

apply_mapping("l4", "a")          # L4 → A button
apply_mapping("c1", "enter")      # C1 → Enter key
apply_mapping("l4", "left_click") # L4 → left mouse click
apply_mapping("l4", "unbind")     # L4 → disabled
```
