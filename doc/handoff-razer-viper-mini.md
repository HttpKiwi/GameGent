# Handoff — Razer Viper Mini remapping (vs GameGent)

**Date:** 2026-09-28  
**Workspace used for context:** GameGent (GameSir Tarantula Pro HID RE)  
**Goal of inquiry:** Decide whether Viper Mini needs a GameGent-style reverse-engineering project, specifically for **Hypershift remapping**.

---

## User need (concrete)

Synapse Hypershift bind used in Apex Legends:

- Hold side button (Hypershift modifier)
- Scroll wheel → spam `E` (loot pickup)

Want this (or equivalent) on Linux without depending on Synapse.

---

## Verdict

| Layer | Status |
|-------|--------|
| DPI / poll rate / logo RGB | **Done** — OpenRazer since ~2020 (`1532:008A`) |
| Onboard / Hypershift remaps | **Not done** for Viper Mini |
| Full GameGent-from-scratch stack | **Not warranted** — protocol + driver already exist |

**Practical path for Apex:** recreate the bind with **input-remapper** (host-side Hypershift).  
**RE path:** only if the goal is *editing Synapse-class onboard Hypershift from Linux*.

---

## What GameGent is (reference pattern)

GameGent exists because GameSir had almost no open Linux stack. It reverse-engineered USB HID and shipped:

- CLI + Flask API + React UI
- Onboard remap read/write (`doc/remapping.md`, `doc/hex_protocol.md`, `core/read_remap.py`)
- Profiles, lighting, rumble, game→profile watcher

That full-stack pattern only makes sense for Viper Mini if targeting onboard remap/Hypershift as a product. Do **not** reimplement DPI/RGB — OpenRazer already owns that.

---

## What already exists for Razer

### OpenRazer

- Device class: `RazerViperMini` — VID `0x1532`, PID `0x008A`
- Methods: DPI, DPI stages, poll rate, logo brightness/effects, custom frame
- Kernel driver: `razermouse_driver.c`
- Frontends: Polychromatic, RazerGenie, etc.
- Support added in [PR #1163](https://github.com/openrazer/openrazer/pull/1163) (OpenRazer ≥ 2.9.0)

### Protocol (already documented)

- 90-byte Razer HID feature reports
- RE guide: [openrazer/wiki/Reverse-Engineering-USB-Protocol](https://github.com/openrazer/openrazer/wiki/Reverse-Engineering-USB-Protocol)
- Unknown / onboard notes: [openrazer/wiki/Unknown-commands](https://github.com/openrazer/openrazer/wiki/Unknown-commands)
- Partial remap RE on other mice: [Basilisk Ultimate #2845](https://github.com/openrazer/openrazer/issues/2845) — class `0x02` / cmd `0x0c`
- Keyboard remaps (related, not mice): [issue #2031](https://github.com/openrazer/openrazer/issues/2031) — Hypershift flag in payload for keys
- OpenRazer maintainers have steered macros toward input-remapper rather than growing daemon macro support ([PR #2691](https://github.com/openrazer/openrazer/pull/2691) discussion)

### Gaps (the Synapse-shaped hole)

OpenRazer does **not** expose for Viper Mini:

- Button remapping
- Hypershift layer bindings
- Onboard profile memory write/read for those bindings
- Scroll-wheel → key macros stored on device

Viper Mini marketing lists “Onboard Memory Profile” and Synapse Hypershift. Whether a given Hypershift+macro bind persists after quitting Synapse is device/firmware-dependent — if previously saved to onboard on Windows, it may still fire on Linux until overwritten, but **cannot be edited from Linux today**.

---

## Recommended paths

### A. Host-side Hypershift (ship the Apex bind now)

Use [input-remapper](https://github.com/sezanzeb/input-remapper):

- Side button as modifier layer
- Wheel → repeating `key(E)` (watch `WHEEL` vs `WHEEL_HI_RES`; disable the unused one)
- Same idea documented in [input-remapper discussion #688](https://github.com/sezanzeb/input-remapper/discussions/688)

Pros: works without RE; matches gaming need.  
Cons: per-machine; not true onboard Synapse memory.

### B. One-time Synapse onboard write

Configure on Windows, save to onboard profile, use on Linux read-only.

Pros: zero Linux tooling if the bind actually persists.  
Cons: can’t iterate on Linux; may not persist for Hypershift/macros on this SKU.

### C. GameGent-like / OpenRazer extension (only if A/B insufficient)

Scope = **remap + Hypershift protocol for Viper Mini**, not a new RGB/DPI stack.

Suggested approach (mirror GameGent RE workflow, land in OpenRazer):

1. Windows VM + USB passthrough; capture Synapse with Wireshark/usbmon while setting the Apex Hypershift bind
2. Decode against the known 90-byte report format
3. Diff vs Basilisk Ultimate `0x02/0x0c` remap writeup — reuse what matches
4. Confirm read-back of bindings on live Viper Mini firmware
5. Prefer contributing driver/daemon/pylib to OpenRazer over a parallel full app (unless a thin CLI like GameGent is desired for iteration)

---

## Key links

| Resource | URL |
|----------|-----|
| OpenRazer mouse class | https://github.com/openrazer/openrazer/blob/master/daemon/openrazer_daemon/hardware/mouse.py |
| Viper Mini already supported | https://github.com/openrazer/openrazer/issues/2545 |
| Unknown commands / onboard memory | https://github.com/openrazer/openrazer/wiki/Unknown-commands |
| Basilisk Ultimate remap RE | https://github.com/openrazer/openrazer/issues/2845 |
| Keyboard remap + Hypershift flag | https://github.com/openrazer/openrazer/issues/2031 |
| GameGent remap docs (this repo) | `doc/remapping.md`, `doc/hex_protocol.md` |

---

## Next actions (if continuing)

1. [ ] Try input-remapper for side-hold + wheel → spam `E`; validate in Apex on Linux
2. [ ] If onboard edit is still required: capture Synapse Hypershift+scroll macro traffic on Viper Mini
3. [ ] Compare capture to Basilisk Ultimate #2845; note PID `008A`-specific deltas
4. [ ] Decide: OpenRazer PR vs small GameGent-style CLI sidecar that only speaks remap commands

---

## Out of scope for a Viper Mini project

- Reimplementing OpenRazer lighting/DPI
- Full React+Flask UI unless remap tooling proves sticky enough to deserve one (GameGent UI was justified by a greenfield device)
