```markdown
# GameGent Controller Tool

A lightweight, native Python CLI utility to control the hardware lighting states of GameSir controllers directly from Linux via `/dev/hidraw`. No heavy Windows virtual machines, proprietary wrappers, or bloat required.

## Features
* **Zero Dependencies:** Relies entirely on native Python 3 standard libraries and direct kernel interfaces.
* **Granular Control:** Fully reverse-engineered linear scaling for both illumination brightness and animation speed.
* **Persistent Profiling:** Automatically caches your preferred states locally and syncs them instantly on demand.

---

## Protocol Architecture

Through hardware telemetry and USB packet analysis, the configuration payload structure was isolated to a precise 32-byte interrupt packet structure running down the endpoint wire:

```text
[07 06 07 01]  [BRIGHTNESS]  [SPEED]  [MODE_ID]  [00]  [00] ... [PADDING]
     │              │           │        │        │     │          │
     │              │           │        │        └─────┴─ Future Zone Expansion
     │              │           │        └─ Lighting Mode Selector (0x00 - 0x05)
     │              │           └─ Animation Speed Hex Slider Value (0x00 - 0x64)
     │              └─ Illumination Power Hex Slider Value (0x00 - 0x64)
     └─ Global Configuration Header Block

```

### Hardware Mode Mappings

| Mode Name | Byte Code (Hex) | Description |
| --- | --- | --- |
| `off` | `0x00` | Disables the primary global ambient lighting zone. |
| `static` | `0x01` | Solid color state (Speed slider is physically inert). |
| `breathing` | `0x02` | Smooth pulse cycle scaling against the speed clock. |
| `colorful` | `0x03` | Fixed cycle stepping through factory color arrays. |
| `rainbow` | `0x04` | Fluid horizontal fluid spectrum animation sweep. |
| `radar` | `0x05` | Sequential outward flashing pulse pattern. |

---

## Installation & Setup

1. **Clone the repository** into your local environment:
```bash
git clone <repository-url>
cd gamegent-controller

```


2. **Ensure Executive Permissions:** Make sure the driver entry point is flagged as executable:
```bash
chmod +x main.py

```


3. **Udev Rule Configuration (Optional):** To interact with raw HID devices without constantly invoking `sudo`, drop a custom rule into `/etc/udev/rules.d/99-gamesir.rules`:
```udev
KERNEL=="hidraw*", ATTRS{idVendor}=="04d8", MODE="0666"

```


*(Replace `04d8` with your hardware's exact USB Vendor ID verified via `lsusb`).* Then reload with `sudo udevadm control --reload-rules && sudo udevadm trigger`.

---

## Usage Guide

### 1. Inspect Local Profile State

Running the script with no arguments prints the current configuration saved in your local state file:

```bash
./main.py

```

### 2. Update Lighting Mode

Modify the current animation behavior. Available modes include `static`, `breathing`, `colorful`, `rainbow`, and `radar`:

```bash
sudo ./main.py mode rainbow

```

### 3. Modulate Brightness (Linear 0-100%)

Instantly dim or brighten the active illumination targets down the wire:

```bash
sudo ./main.py brightness 35

```

### 4. Adjust Animation Velocity (Linear 0-100%)

Control the dynamic step multiplier interval for moving patterns:

```bash
sudo ./main.py speed 72

```

### 5. Force Hardware Synchronization

Re-assert and push all locally saved configurations down to the physical controller MCU processing queue:

```bash
sudo ./main.py sync

```

---

## Technical Project Structure

* `main.py` - The user-facing command line interface runner and state-routing engine.
* `core/protocol.py` - Protocol packet fabrication logic, byte matrix generation, and input translation layers.
* `core/transport.py` - Low-level operational context managers reading and writing raw byte structures directly to the `/dev/hidraw` device interface blocks.

```

```
