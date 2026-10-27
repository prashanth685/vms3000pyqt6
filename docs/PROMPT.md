# Prompt: build the VMS 3000 Rack Configuration Software in Python / PyQt6

You are a senior Python engineer. Build (or complete) a desktop application that is a faithful port of the VB6
"VMS 3000 Rack Configuration Software". Use Python 3.11+, **PyQt6**, **pyserial**, **pytest**. Read `docs/DOCUMENTATION.md`
first — it is the specification of the protocol, register images, scaling and file formats.

## Rules
1. Keep a Qt-free `core/` package (model, codecs, protocol, tasks, simulator) and a thin UI layer. All rack work runs in a
   worker thread (`QThread`) with a progress dialog and Cancel; never block the GUI thread.
2. The model stores **engineering units**; convert to counts only in codecs (mil 40/32767, volt 24/32767, delay 60/255 s,
   trip 10/65535, half-to-even rounding, 16-bit two's complement).
3. Implement Modbus RTU yourself (CRC16 0xA001, low byte first) with FC03/04/08/16 and custom FC67–73, 80, 81; 3 retries.
4. Implement `.rcs` exactly (13001 values, XOR 128, CRLF, two copies, verify equality).
5. Provide a `SimulatedRack` so every feature is testable without hardware for tests only; the UI has no demo mode.
6. Fix the known VB defects listed in the documentation rather than copying them.

## Deliverables
* Rack view: assign 3000/12M/DIS (two slots), 3000/6M, 3000/RLY; validate placement; cut/copy/paste modules.
* Dialogs: Rack Setup, Configuration Settings (+ Security Options bitmask), channel configuration, setpoints (12M & 6M),
  relay logic (4 channels, expression validation, active/latching), connect (direct/network), download password and
  slot selection, event log (read/clear/CSV), RTC, calibration, alarm inhibit, trip multiply, communication settings,
  traffic view.
* Commands: New/Open/Save/Save As, Upload, Download, Connect/Disconnect, Diagnostics, Refresh.
* A bridge (`ui_bridge.py`) converting screen state ⇄ `RackModel` so save/upload/download use one source of truth.
* Tests: CRC vector `01 03 00 00 00 0A → C5 CD`, slot codec round trip, config card, relay compile/decompile,
  `.rcs` round trip, simulator upload/download/events/RTC, bridge round trip.

## Acceptance
`pytest` passes; the app starts (`python main.py`); Connect → Upload → Save → Open → Download completes; a saved `.rcs`
reopens to an identical model.
