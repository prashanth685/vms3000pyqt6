# VMS 3000 Rack Configuration Software — How the original VB6 application works

Source: `GUI-RCS-V.0.5 [22-07-2022] TEXRON_6M_MB_TimeDelay_Completed` (VB6). This document describes behaviour, the
wire protocol and file formats, and how each part is implemented in the Python/PyQt6 port.

## 1. Purpose
Offline/online configuration tool for a modular vibration-monitoring rack (VMS 3000). The operator lays out modules in
a rack, sets channel parameters, setpoints and relay logic, saves the result to an `.rcs` file, and uploads/downloads
it to the rack over RS-232/485 (Modbus RTU) or TCP. It also reads the event log, sets the rack clock and calibrates gains.

## 2. Rack model
* Slot 0 = **configuration card**; slots 1–11 = modules (VB slot numbers). The PyQt6 UI uses raw slot = VB slot + 1
  (raw 1 is the fixed configuration panel; the displayed number is raw − 1).
* Module types: 0 none, 1 VMM_12M (UI "3000/12M/DIS", occupies two physical slots), 2 RLY_4C (UI "3000/RLY"),
  3 VMM_6M (UI "3000/6M").
* Each monitor module has 4 channels in two pairs (1-2, 3-4). A pair is **Radial** (vibration) or **Thrust** (position).
* Register address of a slot = slot × 1024. The holding-register image is 13001 words.
  VMM slot = 78 words (156 bytes); relay slot = 214 words; config card = 61 words.

## 3. Screens and what they do
| VB form | Port | Behaviour |
|---|---|---|
| MDI / Menu | `main.py`, `menubar.py`, `toolbar.py` | File, Edit, Utilities, Options, Help; toolbar with connection drop-down and rack address |
| Rack view | `rack_area.py` | click slot → module menu; DIS needs slot+next free; last slot (raw 12) 6M/relay only; right-click → options/setpoints/point names |
| Rack Setup | `sidebar/rack_setup.py` | system type (standard / with display / 20-channel), rack size (full 12 / mini 6), interface → `rack_type_size` |
| Configuration | `popups/configuration_settings.py` | connect & config passwords (≤8 chars), device name, IP/subnet/gateway, service port |
| Security options | `popups/securityOption.py` | six check-boxes → bits 0-5 of the security word |
| Measurement config | `points/channel_configuration.py`, `proximiter12m_ridial.py` | per channel: transducer, direction, direct/gap range and clamp, zero position, latching, delays, trip multiply, recorder output; pair type; active flag |
| Setpoints | `points/setpoins.py`, `setpoins_6m.py` | alert / danger / gap upper-lower with enable flags |
| Relay config | `points/relay_config.py` | 4 relay channels, each an AND/OR expression of module alert/danger states, active and latching |
| Direct / Network connect | `sidebar/connection.py` | password, rack address, COM+baud or IP+port+timeout |
| Download password | `ops_dialogs.ask_password` | password verified against the card before writing |
| Read/Write progress | `workers.run_task` | threaded progress dialog with Cancel (replaces VB timer state machines) |
| Event log | `ops_dialogs.EventLogDialog` | read, clear, export CSV |
| RTC | `ops_dialogs.rtc_dialog` | read / set rack clock |
| Calibration | `ops_dialogs.calibration_dialog` | read gains and live values, calculate, write |
| Com-port settings | `ops_dialogs.comm_settings_dialog` | port, baud, parity, bits, timeout (persisted JSON) |

## 4. Communication protocol (Modbus RTU)
Frame: `addr, function, data…, CRC16` — CRC poly 0xA001, init 0xFFFF, appended **low byte first**
(check: `01 03 00 00 00 0A` → `C5 CD`). Up to 3 retries; slave address and CRC are verified on every reply.

Functions: FC03/04 read holding/input, FC16 write multiple, FC08 diagnostics, and custom FC67/68/69/70/71/72/73/80/81.

* **FC08 handshakes**: sub 0, 5, 7, 10 are echo-verified. Sub 2/6/8 return an info word:
  sub 2 – bit0 wait, bit1 complete, bit2 fail, bit3 slot conflict (used after each slot write);
  sub 6 – 1 wait, 2 complete, 4 fail; sub 8 – bit12 wait, bit13 complete.
* **FC67** event-log read, **FC69** event-log length/status, **FC70** clear log, **FC71** read/set RTC,
  **FC80** read calibration (20 little-endian float32), **FC81** write calibration (12 floats; slave = calibration id).
* **Connect**: check connect password against the card read via FC03, then read slot table.
* **Upload**: read card (61 words) → slot info → each slot image (VMM 78 words; relay 2×107 words).
* **Download**: verify config password (read from card) → write card (60 words) → per slot write + FC08 wait
  (complete / fail / slot-conflict) → relay writes 114 words then 100 words at +114.

## 5. Data encoding (engineering units ↔ counts)
Model stores engineering units; codecs convert at the wire/file boundary.

* mil: 40/32767 per count; volts: 24/32767 per count; delay: 60/255 s per count; trip multiply: 10/65535 per count.
* µm = mil × 25.4; rounding is half-to-even; values masked to 16-bit two's complement.

### Slot frame (156 bytes)
| Bytes | Meaning |
|---|---|
| 0–5 | slot id, module type, input words (14), holding words (78), 0, 0 |
| 6–7 | rack status |
| 10 / 11 | pair 3-4 / pair 1-2 type (1 radial, 2 thrust) |
| 12–13 | channel word: bits0-3 active, 4-7 thrust direction, 8-11 alert latch, 12-15 danger latch |
| 14–15 | alarm-enable word: direct, gap, direct-danger, gap-danger (4 bits each) |
| 16–19 | recorder bytes (swapped per pair) |
| 20 + 8·row + 2·ch | 15 rows × 4 channels |
| 140+ / 144+ | delay alert / danger bytes (index swap 1,0,3,2) |
| 148 + 2·ch | units byte, parameter byte |

Rows: sensitivity 7874; direct range; gap range; direct alert (radial) / upper (thrust); direct lower; gap alert
upper/lower; direct danger or danger upper; danger lower; gap danger upper/lower; direct clamp; gap clamp;
zero position (thrust); trip multiply (radial).

### Configuration card (61 words)
word 0 slot-available mask; 1–33 slot table (6 bytes per slot); 34–37 config password; 38–41 connect password;
42–45 config id; 46–49 device name; 50–51 IP; 52–53 subnet; 54–55 gateway; 57 service port; 58 rack_type_size
(785 = 20-ch + full + standard; system 256/512/768, size 16/32, interface 1/2); 59 rack status
(bit3 alarm inhibit, bit4 trip multiply); 60 security options (bits 0-5).

### Relay block
50 words per relay channel (sequence area starts at word 14): word0 = n_params·256 + n_steps; parameter words
`relay_ch<<12 | slot<<8 | channel<<4 | alert`; step words `op1<<9 | op2<<2 | op` (1 = `*`, 2 = `+`); then token nibbles
( `(`=1 `+`=2 `*`=3 param=4 `)`=5, four per word). Expression syntax `S<slot>C<ch>A<alert>`, `*` = AND (binds tighter),
`+` = OR, innermost brackets reduced first.

### `.rcs` file
13001 decimal values, one per line, each byte XOR 128, CRLF, **written twice**; the reader checks both copies match.
The port also reads/writes JSON for debugging (`read_any`).

### Event record (10 bytes)
`Y M D h m s x x ev_lo ev_hi`; event word = slot[0:4] channel[4:8] alarm type[8:12] direction[12:14] mode[14:16].

## 6. Port architecture
```
core/   modbus_rtu, scaling, model, vmm_codec, config_card, relay_logic, image, rcs_file, events, calibration,
        simulator, transport, link, tasks, settings, app_state      (no Qt – unit-tested)
src/    ui_bridge (screens <-> model), workers (QThread progress), ops_dialogs, points/*_store (dialog state)
main.py PyQt6 window; every command goes through AppState
```
`SimulatedRack` + `SimTransport` is used by the tests only (no demo mode in the UI).

## 7. Known VB defects and how the port treats them
* password compare used `<> Null` (always true) → proper string comparison;
* security word was never sent → now written;
* relay parameter slot was one digit → port allows slots 1-11;
* gap decode off by one (65535 − x) → decoded exactly;
* default subnet 255.255.255.1 → 255.255.255.0;
* relay upload loop overran by one word → bounded.

## 8. Limits of the port
Network connect is RTU-over-TCP and untested on hardware; system-event log reading follows the VB behaviour only
partially; Axial-vibration pair type is stored as thrust; mini-rack (6 slot) layout is saved but the rack view still draws
12 slots; Undo/Redo, firmware update and printing are not implemented.
