# VMS 3000 — tkinter → PyQt6 migration notes

Run with `pip install -r requirements.txt` then `python main.py`.
Pillow is no longer needed (icons and rack photos are rendered/scaled by Qt).

## What changed
| Area | tkinter | PyQt6 |
|---|---|---|
| Windows / dialogs | `Tk`, `Toplevel` + `grab_set` | `QMainWindow`, modal `QDialog.exec()` |
| Rack view, gauges, relay slot strip, PSM panel | `tk.Canvas` | custom-painted `QWidget` (`QPainter`) + hit-testing |
| Menus / context menus | `tk.Menu` | `QMenuBar` / `QMenu` |
| Images / icons | `PIL.ImageTk` | `QPixmap`, Material Icons font drawn with `QPainter` |
| Message boxes / file dialogs | `messagebox`, `filedialog` | `QMessageBox`, `QFileDialog` |
| Variables | `StringVar` | widget state / signals |

New shared module: **`qt_common.py`** (themed dialog base, buttons, fonts, image cache, message-box helpers).
Public call signatures of the dialogs (`SetpointsDialog(parent, fonts, slot)`, `.show()`, ...) were kept.
`.show()` on dialogs now blocks until closed (modal), as the old `grab_set` dialogs behaved for the user.

## Behaviour fixes made during the port
* **Setpoints › Colors › Apply** used to call `_build_ui()` again and stack a second copy of the UI; it now just recolours the gauges.
* **Relay Config** crashed (`_channel_combo` didn't exist yet) when the initially-selected slot held a channel module; widgets are now built first, then the slot is selected.
* **Direct/Network Connect**: the status bar said "Connected" even if you pressed Cancel. `show()` now returns True only on Connect.
* **Calibration**: Connection/Date-Time frames overlapped the third Gain section, and Calculate/Write indexed `calc_gains[i*3+gain-1]` into a 4-item list (IndexError). Re-laid out; widgets are stored per gain section.
* `RackArea` no longer needs a `StringVar` hint; it owns its hint label (`set_hint()`).

## Left as-is (pre-existing, not tkinter-related)
* In `rack_area._right_click`, 3000/6M opens the *Proximity* options dialog (`model="6M"`); `SixMOptionsDialog` exists but is not wired in (the old `elif` for it was unreachable).
* `ui/*.py` (older PyQt6 scaffold) import `XPButton` from `controls/xp_button.py`, which is an empty file, so those stubs don't import. The app does not use them.
