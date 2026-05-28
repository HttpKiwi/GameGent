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
16       1    Padding           00
17      15    HID payload       See below per report type
------  ----  ---------------  -----------------------------------------
Total: 32 bytes
```

---

## Button Index (bytes 8–9)

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

## Usage from Python

No need to manually map every key. The standard USB HID usage table is
embedded in `core/hid_keycodes.py` — a single lookup dict.

```python
from core.hid_keycodes import (
    KEYBOARD_USAGE, MOUSE_BUTTON, MOUSE_SCROLL,
    keyboard_packet, mouse_button_packet, mouse_scroll_packet,
)

# Build a packet for any key:
pkt = keyboard_packet(button_index=0x29, usage_id=KEYBOARD_USAGE["enter"])
# => bytes ready for os.write(fd, pkt)

# Or mouse button:
pkt = mouse_button_packet(0x29, MOUSE_BUTTON["left_click"])
pkt = mouse_scroll_packet(0x29, MOUSE_SCROLL["scroll_up"])
```

## Verified Captures

Confirmed via USB sniffing for button `0x29` (C1). All match the standard
HID spec. See `key_binds.json` for hex dump.
