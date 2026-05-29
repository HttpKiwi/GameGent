# GameGent Controller Tool

Native Python CLI to control GameSir controller hardware via Linux. No VMs, no proprietary wrappers.

## Features
- Control lighting mode, brightness, and animation speed
- Remap controller buttons to keyboard keys, mouse actions, or other controller buttons
- Unbind/disable buttons
- Configure stick modes: native analog, mouse emulation, 4-way keyboard mapper, stick cloning
- Per-stick curve presets (linear, expo, s-curve), dead zones, and sensitivity
- Custom directional scancodes in keyboard mode
- Persistent local profile caching with mapping sync
- Zero dependencies — Python 3 standard library only

## Setup

```bash
chmod +x main.py
```

### Udev rule (avoid sudo)

Drop this in `/etc/udev/rules.d/99-gamesir.rules`:

```udev
KERNEL=="hidraw*", ATTRS{idVendor}=="04d8", MODE="0666"
```

Replace `04d8` with your device vendor ID from `lsusb`. Then:

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

## Usage

### Show current profile

```bash
./main.py
```

### Set lighting mode

```bash
sudo ./main.py mode rainbow
```

Modes: `off`, `static`, `breathing`, `colorful`, `rainbow`, `radar`

### Set brightness (0-100%)

```bash
sudo ./main.py brightness 35
```

### Set animation speed (0-100%)

```bash
sudo ./main.py speed 72
```

### Sync saved profile to device

```bash
sudo ./main.py sync
```

### Remap a button

```bash
sudo ./main.py remap <button> <target>
```

Buttons: `c1`-`c4`, `t1`-`t3`, `l4`, `r4`

Targets:
- **Keys:** `a`-`z`, `0`-`9`, `f1`-`f24`, `enter`, `escape`, `space`, `tab`, `backspace`, arrows (`up`/`down`/`left`/`right`), modifiers (`left_ctrl`, `left_shift`, `left_alt`, `left_gui`, etc.)
- **Mouse clicks:** `left_click`, `right_click`, `middle_click`, `button_4`, `button_5`
- **Scroll:** `scroll_up`, `scroll_down`
- **Controller buttons:** `a`, `b`, `x`, `y`, `lb`, `rb`, `lt`, `rt`, `l3`, `r3`, `back`, `start`, `dpad_up`, `dpad_down`, `dpad_left`, `dpad_right`, `screenshot`
- **Unbind:** `unbind` disables the button entirely

Examples:

```bash
sudo ./main.py remap t1 a          # t1 types 'a'
sudo ./main.py remap c1 space      # c1 presses space
sudo ./main.py remap t2 left_click # t2 left-clicks
sudo ./main.py remap c3 scroll_up  # c3 scrolls up
sudo ./main.py remap l4 b          # l4 acts as B button
sudo ./main.py remap r4 start      # r4 opens start menu
sudo ./main.py remap c1 unbind     # c1 disabled
```

### Clear a mapping (remove from config + unbind hardware)

```bash
sudo ./main.py remap <button> clear
```

### Disambiguation prefixes

When a target name conflicts (e.g. controller `a` vs keyboard `a`), use a prefix:

```bash
sudo ./main.py remap l4 controller:a   # L4 → controller A button
sudo ./main.py remap l4 key:a          # L4 → keyboard 'a' key
sudo ./main.py remap l4 mouse:left_click
```

### Stick Configuration

View stick settings:
```bash
./main.py stick left
./main.py stick right
```

Set stick mode (native/mouse/keyboard/clone):
```bash
sudo ./main.py stick left mode mouse
sudo ./main.py stick right mode keyboard
```

Set curve and zones:
```bash
sudo ./main.py stick left curve expo
sudo ./main.py stick left deadzone-min 10
sudo ./main.py stick left intensity 75
sudo ./main.py stick right circle false
```

Sensitivity (0-100):
```bash
sudo ./main.py stick left x-sens 60
sudo ./main.py stick left y-sens 55
```

Keyboard mode — set directional scancodes:
```bash
sudo ./main.py stick left key-up w         # W key (0x1a)
sudo ./main.py stick left key-up up        # Arrow up (0x52)
sudo ./main.py stick left key-down s
sudo ./main.py stick left key-left a
sudo ./main.py stick left key-right d
sudo ./main.py stick left key-up controller:b  # B button
sudo ./main.py stick left key-up mouse:left_click
```

Mouse mode — set DPI (0-100):
```bash
sudo ./main.py stick left mouse-x-dpi 80
sudo ./main.py stick left mouse-y-dpi 75
```

Overlap threshold (keyboard mode, 0-100):
```bash
sudo ./main.py stick left overlap 60
sudo ./main.py stick left key-up-overlap 30
```

Clone mode — right stick mirrors left:
```bash
sudo ./main.py stick left mode clone
```

Full list of stick attributes:
```
mode, circle, x-sens, y-sens, overlap,
mouse-x-dpi, mouse-y-dpi,
deadzone-min, deadzone-max, antideadzone-min, antideadzone-max,
curve, intensity,
key-up, key-down, key-left, key-right,
key-up-overlap, key-down-overlap, key-left-overlap, key-right-overlap
```
