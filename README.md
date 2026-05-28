# GameGent Controller Tool

Native Python CLI to control GameSir controller hardware via Linux. No VMs, no proprietary wrappers.

## Features
- Control lighting mode, brightness, and animation speed
- Remap controller buttons to keyboard keys or mouse actions
- Persistent local profile caching
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

Examples:

```bash
sudo ./main.py remap t1 a          # t1 types 'a'
sudo ./main.py remap c1 space      # c1 presses space
sudo ./main.py remap t2 left_click # t2 left-clicks
sudo ./main.py remap c3 scroll_up  # c3 scrolls up
```
