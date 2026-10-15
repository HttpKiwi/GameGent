# GameSir Tarantula Pro: configuration protocol (reverse engineered)

**Source:** GameSir Connect **1.16.5** for Windows (Electron). Two layers were analysed:
- the JS layer, `resources/app.asar` → `dist/electron/main.js`, which holds the data model, enums and defaults;
- the native layer, `resources/dfu/sapjoyuniapis_x86_v1.0.16.dll` ("SAPJoyUni", C++ namespace `Sapientia::Joystick`, sha256 `4d24f4cb…4005`), decompiled with Ghidra 12.1.4 to get the byte encoding.

**Confidence:** **[DLL]** = read directly from the decompiled packet builders, serialisers and framer. **[JS]** = read from the app's JavaScript model. **[inferred]** = not directly observed.

In the app the Tarantula Pro is model **`T3Pro`**. The wireless dongle is model `T3Pro_Dongle` / `G760402`.

## Hardware verification (2026-10-13, dongle `3537:103e`, dongle fw `V0241221A`, controller fw 2.0.6)

- Read back on hardware: GET replies for `GetDeviceInfo`, `GetVersion(dongle)`, `GetStickMapping`, `GetStickCurve`, `GetMotionSenseMapping`, `GetMotionSenseCurve`, `GetDPadParam`, `GetTriggerParam`, `GetVibrateParam` and `GetLightParam` all match the §5 layouts.
- SET replies: every SET tried (`SetStickMapping`, `SetStickCurve`, `SetDPadParam`, `SaveConfigPage`, `SetVibrateParam`, `SetLightParam`, `SetVibrateTest`, `SetMacroStep` clear) replies `06 04 [obj] [op] [status]` within 20–60 ms, status `0` = OK. The device didn't reject a wrong `len` byte. GameGent's `send_raw_bytes` waits for this reply (500 ms) and raises `DeviceError` on a timeout or a non-zero status.
- On this machine the dongle exposes **one** hidraw node (interface 1). It carries report IDs `01 02 03 06 07`, and both config replies and `06 1a 0a 03` state reports arrive on it. Interface 0 (vendor class `ff/5d/01`) is bound by `xpad` and has no hidraw node, so §1's usage-page split is not needed here.
- `GetDeviceInfo` reply: `06 0e 0a 01 | 00 | 02 06 | 12 94 90 5e 5a a0 | 64 | 00`, i.e. fw 2.06 and battery 100.
- `GetVersion(dongle)` reply bytes 11–14: `02 41 22 1a` = `V0241221A`.

---

## 1. Device and HID interfaces [JS]

| Mode | VID:PID | Config interface (SAPJoyUni DLL) | Notes |
|---|---|---|---|
| Wireless (2.4 GHz dongle) | `3537:103E` | Usage page `0xFFF0` | Supported by GameGent |
| Wired (USB-C) | `3537:1050` | Usage page `0xFFFF` | Not handled by GameGent |
| (third PID the DLL opens) | `3537:100E` | ? | Listed in `pid:[4176,4158,4110]` |

There is a separate state/notification interface (usage page `0xFFA0`, usage 1, interface 1), opened with node-hid:
- `06 1a 0a 03 …`: live gamepad state plus the RGB colour of 5 LEDs (§6).
- `06 05 0a 0d [mask]`: profile-changed push notification (§6).
- The app writes rumble bursts there: `07 07 0a 04 L R 00 00`.

## 2. Framing [DLL]

```
OUT:  [rid] [len] [obj] [op] [payload…]  zero-padded to the output-report size
        rid = 0x07   (0x05 only for firmware-update packets, obj 0x53 'S')
        len = payload_len + 3        (older GameGent docs call this the "class byte")
IN :  06 [len] [obj] [op] [data…]
        GET reply : data starts at byte 4 (same layout as the SET payload)
        SET reply : byte 4 = status, 0 = OK, non-zero = device error code
```

- The DLL waits for the reply to every command (500 ms timeout) and reads the SET status byte.
- The app sends `SaveConfigPage` 500 ms after the last SET (debounced), not once per packet.
- GameGent's `init_session` (`01 00`, then `07 03 0a 01` ×2) is an unknown report-1 write followed by two `GetDeviceInfo` requests. It isn't a mode switch.

## 3. Command table [DLL]

`obj`/`op` come from the 16-bit word each command constructor stores (low byte = obj, high byte = op).

| obj | op | Command | Payload (SET) / args (GET) |
|---|---|---|---|
| 01 | 01 | SetMacroStep | 16 B, §5.6 |
| 01 | 02 | GetMacroStep | `[key][index]` |
| 02 | 01 | SetStickCurve | 21 B, §5.2 |
| 02 | 02 | GetStickCurve | `[stick][page]` |
| 02 | 03 | SetStickMapping | 12 B, §5.1 |
| 02 | 04 | GetStickMapping | `[stick]` |
| 03 | 01 | SetTriggerParam | 16 B, §5.3 |
| 03 | 02 | GetTriggerParam | `[trigger]` |
| 04 | 01 | SetMotionSenseCurve | 19 B, §5.4 |
| 04 | 02 | GetMotionSenseCurve | `[page]` |
| 04 | 03 | SetMotionSenseMapping | 11 B, §5.5 |
| 04 | 04 | GetMotionSenseMapping | – |
| 05 | 01 | SetKeyMapping | 16 B, §5.7 |
| 05 | 02 | GetKeyMapping | `[page][key]` (the "leading 00" in GameGent's remap read) |
| 06 | 01 | SetVibrateParam | `[leftGrip][rightGrip][ltMode][rtMode][ltLevel][rtLevel]` |
| 06 | 02 | GetVibrateParam | – |
| 07 | 01 | SetLightParam | `[brightness][speed][mode]` |
| 07 | 02 | GetLightParam | – |
| 07 | 03 | SetLightColor | `[name]` + 4 × `[h8][s][v]`, h8 = h°/360·255 |
| 07 | 04 | GetLightColor | `[name]` |
| 08 | 01 | SetConfigPage | `[page]` |
| 08 | 02 | GetConfigPage | – |
| 08 | 03 | SaveConfigPage (GameGent's "commit") | – |
| 08 | 04 | ResetConfigPage (factory reset of the page) | – |
| 09 | 01 | SetDPadParam | 6 B, §5.8 |
| 09 | 02 | GetDPadParam | – |
| 09 | 03 | SetDeviceType | `[id][type]`: **rewrites device identity, never send** |
| 09 | 04 | GetDeviceType | – |
| 0a | 01 | GetDeviceInfo | → `[id][fw0][fw1][mac×6][battery][type]`; battery 255 = charging |
| 0a | 02 | SetGamepadStateReport | `[0 off / 1 original (raw) / 2 mapped]` |
| 0a | 04 | SetVibrateTest | `[leftGrip][rightGrip][lt][rt]` |
| 0a | 05 | SetStickTriggerCalibration | 1 byte (unknown) |
| 0a | 06 | GetStickTriggerCalibration | – |
| 0a | 07 | SetGyroscopeCalibration | 1 byte (unknown) |
| 0a | 08 | GetGyroscopeCalibration | – |
| 0a | 09 | SetLightColorTest | `[enable][h8][s][v]` |
| 0a | 0a | SetABXYRotationTest | 1 byte |
| 0a | 0b | ExchangeBTAddress | 6 B → 6 B |
| 0a | 0c | ExchangeBTLinkKey | → 16 B |
| 84 | 01 | GetVersion | `[1 = controller, 2 = dongle]` → engineer/protocol/firmware/hardware |
| 84 | 02 | GetMacAddress | `[device]` |
| 84 | 03 | **SetISPMode** (enters bootloader, never send) | `[device]` |
| 84 | 04 | SetPairMode | `[device]` |
| 53 | 11 | Firmware update (rid 0x05) | – |

Calibration and BT/pairing commands exist in the DLL, but the T3Pro code path never calls them. Don't send them blindly.

## 4. Enums [JS, matching the DLL]

- **Key IDs (`SAPJoyUniKey`):** B 0, A 1, Y 2, X 3, LB 4, LT 5, L3 6, RB 7, RT 8, R3 9, View 10, Menu 11; D-pad Left 12, Right 13, Up 14, Down 15; stick wheel zones InnerLStick L/R/U/D 16–19, InnerRStick 20–23, OuterLStick 24–27, OuterRStick 28–31; gyro wheel zones Left/Right/Up/Down 32–35; L4 36, R4 37, T1 38, T2 39, T3 40, C1 41, C2 42, C3 43, C4 44, Capture 45.
- **Mapping type:** Vacant 0, Joystick 1, Keyboard 2, Mouse 3, Media 4.
- **Trigger mode** (key, macro and gyro activation): Off 0, OneShot 1 (press/toggle), Hold 2, AlwaysOn 3.
- **Turbo mode:** Off 0, A 1, B 2, C 3. The app picks it from the rate: ≥ 20 → C, ≥ 12 → B, > 1 → A, otherwise Off with turboTimes = 1.
- **Stick output mode:** Close (native) 0, Mouse 1, Keys (wheel) 2, StickMapping (output as the other stick, GameGent "clone") 3.
- **Stick shape:** Square 0, Circle 1.
- **Hair trigger:** Linear 0, AdaptiveFast 1, FixedFast 2.
- **Gyro output:** Off 0, LeftStick 1, RightStick 2, Keys 3, Mouse 4.
- **Gyro type:** Shooting (aim) 0, Racing (tilt) 1.
- **Gyro axis (`shootingMode`):** YZ 0 (yaw), XY 1 (roll), XYZ 2 (global).
- **Light mode:** Off 0, AlwaysOn 1, Breathing 2, PhantomColor 3, Streamer 4, Radar 5.
- **Light name:** Home 0, Pedestal 1, Left 2, Right 3, Panel 4, ABXY 5, BAYX 6. The T3Pro uses ABXY, BAYX, Home and Panel.
- **D-pad type:** 8-way 0, 4-way 1. **D-pad swap:** Off 0, D-pad→LS 1, D-pad→RS 2, LS↔RS 3.
- **Layout:** ABXY (Xbox) 1, BAYX (Switch) 2.
- **Gamepad report:** Off 0, Original 1, Mapped 2. **Device ID:** controller 1, dongle 2.

## 5. Payload layouts [DLL]. Byte numbers are absolute packet offsets.

### 5.1 SetStickMapping `07 0f 02 03`
| b | field |
|---|---|
| 4 | stick (0 L / 1 R) |
| 5 | angle (cross / diagonal overlap %), app default 40 |
| 6 | innerTriggerRange (app: always 40) |
| 7 | outerTriggerRange (app: always 80) |
| 8 | stickDirectionX (invert X) |
| 9 | stickDirectionY (invert Y) |
| 10 | mode (§4 stick output) |
| 11 | state (app: 1) |
| 12 | miceSensitivityX |
| 13 | miceSensitivityY (app: same as X) |
| 14 | miceDirectionX (= invert X) |
| 15 | miceDirectionY (= invert Y) |

### 5.2 SetStickCurve `07 18 02 01`
`b4` stick · `b5` page · `b6` key (app writes the stick index) · `b7` trigger (0) · `b8–10` h8 s v (0) · `b11` shape (0 square / 1 circle) · `b12` **ratio** (X/Y axis ratio, 50 = equal) · `b13` beginDeadzone · `b14` beginAntiDeadzone · `b15–20` 3 curve points (x,y), app default (30,30)(50,50)(70,70) · `b21` endDeadzone · `b22` endAntiDeadzone · `b23` curveType · `b24` curvature (app default 100).

The stick has no separate X and Y sensitivity. The only per-axis controls are `ratio` here and mouse sensitivity in §5.1.

### 5.3 SetTriggerParam `07 13 03 01`
`b4` trigger · `b5` type (hair trigger) · `b6` triggerValue · `b7` releaseValue · `b8–17` `[beginDZ, beginAntiDZ, p0x, p0y, p1x, p1y, p2x, p2y, endDZ, endAntiDZ]` · `b18` curveType · `b19` curvature. App defaults: deadzone 5/95, anti-deadzone 0/100, hair trigger 10/20.

### 5.4 SetMotionSenseCurve `07 16 04 01`
`b4` page · `b5` key · `b6` trigger · `b7–9` h8 s v · `b10` **ratio** · `b11–20` points (same order as §5.3) · `b21` curveType · `b22` curvature.

### 5.5 SetMotionSenseMapping `07 0e 04 03`
`b4` angle (cross) · `b5` outputTriggerRange (app default 40) · `b6` mode (gyro output) · `b7` type (aim/tilt) · `b8` shootingMode (axis) · `b9` key (activation button) · `b10` trigger (activation method) · `b11` stickSensitivityX · `b12` stickSensitivityY · `b13` stickDirectionX (invert) · `b14` stickDirectionY (invert).

### 5.6 SetMacroStep `07 13 01 01`
`b4` key · `b5` index (0–11; **0xFF = clear all steps**) · `b6` trigger (1 OneShot, 2 Hold, 3 AlwaysOn) · `b7` loop · `b8–9` loopTime (hi, lo) · `b10` mappingType · `b11` keyCount · `b12–15` code (Joystick = 4 key IDs; Keyboard = [modifiers, k1, k2, k3]; Mouse/Media = [0, 0, scroll, bits]) · `b16–17` startTime (hi, lo) · `b18–19` endTime (hi, lo).

Macros only on L4, R4, T1, T2, T3, C1–C4, max 12 steps each [JS]. Time units unconfirmed (fields are named `…In10MS`, but the T3Pro path writes ms unscaled).

### 5.7 SetKeyMapping `07 13 05 01`
| b | field |
|---|---|
| 4 | page (0 = default, 1 = second layer? [inferred]) |
| 5 | key (shift key) |
| 6 | trigger |
| 7–9 | h8 s v (app sends 0) |
| 10 | mappingKey: the physical source button |
| 11 | toggle |
| 12 | turboMode |
| 13 | turboTimes (rate; 1 = no turbo) |
| 14 | mappingType |
| 15 | keyCount |
| 16–19 | code[0..3] |

Code encodings:
- Joystick: `[id1, id2, id3, …]` (combos are 2 or 3 IDs).
- Keyboard: `[modifier bitmask (LCtrl, LShift, LAlt, Win, RCtrl, RShift, RAlt), k1, k2, k3]`, count = 1 + number of keys.
- Mouse: `[0, 0, scroll (1 up / 0xFF down / 0x80 both), buttons]`, button bits L 1, R 2, M 4, B5 8, B4 0x10.
- Media: `[0, 0, 0, bits]`: Mute, Vol−, Vol+, MicMute, Play, Prev, Stop, Next.

GameGent's `REPORT_TURBO = 04 04` is actually Media with 4 code bytes. Unmapped = Joystick type with `code0 == mappingKey`. App defaults: C1, C2 → View; C3, C4 → Menu; T3 → Capture.

### 5.8 SetDPadParam `07 09 09 01`
| b | field | meaning |
|---|---|---|
| 4 | type | 8-way / 4-way |
| 5 | mode | D-pad / stick swap (§4) |
| 6 | layout | 1 ABXY / 2 BAYX |
| 7 | smartStartStop | Auto On/Off; **0 = enabled** |
| 8 | fastTrigger | trigger-travel auto calibration; **0 = enabled** |
| 9 | macroSwitch | key ID used as macro on/off switch; 0 = none |

Write it read-modify-write (GameGent's `set_abxy_layout` does).

## 6. Input reports [JS] (enable with `SetGamepadStateReport`)

**`06 1a 0a 03` gamepad state.** Bytes 4–7 LS X/Y, RS X/Y (128 = centre). Bytes 8–9 LT/RT. Button bits:

| Byte | bit0 | bit1 | bit2 | bit3 | bit4 | bit5 | bit6 | bit7 |
|---|---|---|---|---|---|---|---|---|
| 10 | B | A | Y | X | LB | LT | L3 | RB |
| 11 | RT | R3 | View | Menu | Left | Right | Up | Down |
| 12 | Home | Capture | M | | | | | |
| 13 | L4 | R4 | T1 | T2 | T3 | C1 | C2 | C3 |
| 14 | C4 | | | | | | | |

Bytes 27–41: live RGB of 5 LEDs. "Original" mode reports raw physical buttons (a button tester without xpad).

**`06 05 0a 0d [mask]` profile changed.** Mask bits: 1 sticks, 2 triggers, 4 key mappings, 5 vibration, 6/7 lights.

## 7. Dongle firmware `V0241221A → V0250917A`

- Bundled as `packages/Burn_GDF-G760402_2977_V10_250917a.ufw`; update path is `SetISPMode(dongle)` then a JieLi DFU worker. Images are encrypted, so code changes can't be diffed.
- Controller firmware (2.0.6, `G560159` / `G560163`) is updated separately.

| Release note | Protocol meaning |
|---|---|
| Option to enable/disable automatic trigger travel calibration | `SetDPadParam` b8 (`fastTrigger`) |
| Turbo settings no longer survive power-off | turbo (§5.7 b12/b13) is volatile; re-apply on connect |
| Added Radar lighting effect | `LightMode = 5`; likely no effect before `V0250917A` |
