"""
main.py — VMS 3000 Rack Configuration Software v0.5   (PyQt6)
"""

import datetime
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from theme import T
from qt_common import ask_yes_no, hline, make_fonts, show_info, vline
from menubar import build_menubar
from toolbar import build_toolbar
from rack_area import RackArea
from tooltip import ToolTip
from src.sidebar.sidebar import build_sidebar
from src.sidebar.rack_setup import open_rack_setup
from src.sidebar.open_config_load import LoadConfigDialog
from src.sidebar.open_config_save import SaveConfigDialog
from src.sidebar.connection import (
    DirectConnectDialog,
    NetworkConnectDialog,
    disconnect_device,
)
from src.sidebar.rack_setup import cfg_to_rack_type, rack_type_to_cfg
from qt_common import show_error, show_warning
from core import tasks
from core.app_state import AppState
from core.rcs_file import RcsError
from core.model import MT_NONE, MT_VMM_12M, SLOT_NUMBERS
from ui_bridge import model_from_ui, ui_from_model
from workers import run_task
import ops_dialogs as ops


class VMS3000(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            "VMS 3000  —  Rack Configuration Software  v0.5"
        )

        self.state = AppState()
        self.state.listeners.append(self._on_state_event)

        # Window size is controlled in main() using showMaximized()
        self.setStyleSheet(
            f"QMainWindow {{ background:{T['win_bg']}; }}"
        )

        # ── Fonts ────────────────────────────────────────────────────
        self.F = make_fonts()

        # ── Central widget + vertical stack ──────────────────────────
        central = QWidget()
        central.setStyleSheet(
            f"background:{T['win_bg']};"
        )

        self.setCentralWidget(central)

        self._main_layout = QVBoxLayout(central)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # ── Build UI ─────────────────────────────────────────────────
        self._build_menu()

        # ── Toolbar command callbacks ────────────────────────────────
        toolbar_callbacks = {
            "new": self._cmd_new,
            "open": self._cmd_open,
            "save": self._cmd_save,
            "print": self._cmd_print,
            "settings": self._cmd_comm,
            "cut": self._cmd_cut,
            "copy": self._cmd_copy,
            "paste": self._cmd_paste,
            "upload": self._cmd_upload,
            "download": self._cmd_download,
            "refresh": self._cmd_refresh,
            "help": self._cmd_about,
            "direct_connect": self._cmd_direct_connect,
            "network_connect": self._cmd_network_connect,
            "disconnect": self._cmd_disconnect,
        }

        self._icons = build_toolbar(
            central,
            self.F,
            "1",
            toolbar_callbacks,
        )

        # ── Border after toolbar ─────────────────────────────────────
        self._main_layout.addWidget(
            hline(T["toolbar_border"], 2)
        )

        # ── Main body ────────────────────────────────────────────────
        body = QWidget()

        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)

        self._main_layout.addWidget(body, 1)

        # ── Sidebar ──────────────────────────────────────────────────
        build_sidebar(
            body,
            self.F,
            {
                "rack_setup": self._cmd_rack_setup,
                "load": self._cmd_open,
                "save": self._cmd_save,
            },
        )

        # ── Separator between sidebar and rack area ─────────────────
        body_lay.addWidget(
            vline(T["toolbar_border"], 1)
        )

        # ── Rack area ────────────────────────────────────────────────
        self._rack = RackArea(
            body,
            self.F,
        )
        self._rack.app_state = self.state
        self._rack.on_change = self.state.mark_dirty

        body_lay.addWidget(
            self._rack,
            1,
        )

        # ── Status bar ───────────────────────────────────────────────
        self._build_status_bar()

        # ── Clock / date timer ───────────────────────────────────────
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30_000)

        self._tick()

    # ── Menu ─────────────────────────────────────────────────────────

    def _build_menu(self):
        build_menubar(
            self,
            self.F,
            {
                "new": self._cmd_new,
                "open": self._cmd_open,
                "save": self._cmd_save,
                "save_as": self._cmd_save_as,
                "direct_connect": self._cmd_direct_connect,
                "network_connect": self._cmd_network_connect,
                "disconnect": self._cmd_disconnect,
                    "calibrate": self._cmd_calibrate,
                "diag": self._cmd_diag,
                "comm": self._cmd_comm,
                "about": self._cmd_about,
                "cut": self._cmd_cut,
                "copy": self._cmd_copy,
                "paste": self._cmd_paste,
                "select_all": self._cmd_select_all,
                "upload": self._cmd_upload,
                "download": self._cmd_download,
                "events": self._cmd_events,
                "rtc": self._cmd_rtc,
                "alarm_inhibit": self._cmd_alarm_inhibit,
                "trip_multiply": self._cmd_trip_multiply,
                "traffic": self._cmd_traffic,
                "rack_address": self._cmd_rack_address,
            },
        )

    # ── Status bar ───────────────────────────────────────────────────

    def _build_status_bar(self):
        bar = QFrame()
        bar.setObjectName("statusBar")

        bar.setStyleSheet(
            f"QFrame#statusBar {{ "
            f"background:{T['status_bg']}; "
            f"border:1px solid {T['status_border']}; "
            f"}}"
        )

        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        def label(text, font, color):
            l = QLabel(text)
            l.setFont(font)
            l.setStyleSheet(
                f"color:{color}; "
                f"background:transparent;"
            )
            return l

        def sep():
            s = vline(
                T["status_border"],
                1,
            )
            s.setFixedHeight(22)
            return s

        # ── Left section ─────────────────────────────────────────────

        bl.addSpacing(12)

        bl.addWidget(
            label(
                "Sarayu Infotech Solutions Pvt Ltd",
                self.F["ui"],
                T["text_dim"],
            )
        )

        bl.addSpacing(12)

        bl.addWidget(sep())

        bl.addSpacing(10)

        bl.addWidget(
            label(
                "VMS 3000  v0.5",
                self.F["ui_b"],
                T["text_dim"],
            )
        )

        bl.addStretch(1)

        # ── Right section ────────────────────────────────────────────
        # sep → date → time → sep → status → dot

        bl.addWidget(sep())

        bl.addSpacing(6)

        self._date_lbl = label(
            datetime.datetime.now().strftime("%d-%m-%Y"),
            self.F["ui"],
            T["text_dim"],
        )

        bl.addWidget(self._date_lbl)

        bl.addSpacing(8)

        self._time_lbl = label(
            "",
            self.F["ui"],
            T["text_dim"],
        )

        bl.addWidget(self._time_lbl)

        bl.addSpacing(8)

        bl.addWidget(sep())

        bl.addSpacing(8)

        self._conn_lbl = label(
            "Not Connected",
            self.F["ui_b"],
            T["led_red"],
        )

        bl.addWidget(self._conn_lbl)

        bl.addSpacing(6)

        self._conn_dot = label(
            "●",
            self.F["ui"],
            T["led_red"],
        )

        bl.addWidget(self._conn_dot)

        bl.addSpacing(12)

        self._main_layout.addWidget(bar)

    # ── Connection status ────────────────────────────────────────────

    def _set_connection_label(self, connected: bool):
        color = (
            T["led_green"]
            if connected
            else T["led_red"]
        )

        self._conn_lbl.setText(
            "Connected"
            if connected
            else "Not Connected"
        )

        self._conn_lbl.setStyleSheet(
            f"color:{color}; "
            f"background:transparent;"
        )

        self._conn_dot.setStyleSheet(
            f"color:{color}; "
            f"background:transparent;"
        )

    # ── Tick ─────────────────────────────────────────────────────────

    def _tick(self):
        now = datetime.datetime.now()

        self._time_lbl.setText(
            now.strftime("%H:%M")
        )

        self._date_lbl.setText(
            now.strftime("%d-%m-%Y")
        )

    # ── Commands ─────────────────────────────────────────────────────

    # ── State observers ──────────────────────────────────────────────

    def _on_state_event(self, event: str):
        if event in ("dirty", "model", "connection"):
            name = os.path.basename(self.state.file_path) if self.state.file_path else "Untitled"
            star = " *" if self.state.dirty else ""
            self.setWindowTitle(f"VMS 3000  —  Rack Configuration Software  v0.5   [{name}{star}]")
        if event == "connection":
            self._set_connection(self.state.connected)
        if event == "settings":
            self._icons.set_rack_address(self.state.settings.get("rack_address", 1))

    def _set_connection(self, connected: bool):
        super_set = VMS3000._set_connection_label
        super_set(self, connected)
        if connected:
            self._conn_lbl.setText({"serial": "Connected (COM)", "network": "Connected (TCP)",
                                    }.get(self.state.mode, "Connected"))

    def _sync_to_model(self):
        model_from_ui(self.state, self._rack)

    def _sync_from_model(self):
        ui_from_model(self.state, self._rack)

    def _need_connection(self) -> bool:
        if not self.state.connected:
            show_warning(self, "Not connected", "Connect to a rack first (Connection menu or toolbar).")
            return False
        return True

    def _error(self, title, exc):
        show_error(self, title, str(exc) or exc.__class__.__name__)

    def _confirm_discard(self) -> bool:
        if not self.state.dirty:
            return True
        return ask_yes_no(self, "Unsaved changes", "The configuration has unsaved changes.\nContinue and lose them?")

    # ── File commands ────────────────────────────────────────────────

    def _cmd_new(self):
        if self._confirm_discard():
            self.state.new()
            self._rack.clear()

    def _cmd_open(self):
        if not self._confirm_discard():
            return
        path = LoadConfigDialog(self, self.F).show()
        if not path:
            return
        try:
            self.state.open_file(path)
        except (RcsError, OSError, ValueError) as e:
            self._error("Open configuration", e)
            return
        self._sync_from_model()

    def _cmd_save(self):
        if not self.state.file_path:
            return self._cmd_save_as()
        self._do_save(self.state.file_path)

    def _cmd_save_as(self):
        default = os.path.splitext(os.path.basename(self.state.file_path))[0] if self.state.file_path else "Configuration"
        path = SaveConfigDialog(self, self.F).show(default)
        if path:
            self._do_save(path)

    def _do_save(self, path):
        self._sync_to_model()
        try:
            self.state.save_file(path)
        except (OSError, ValueError) as e:
            self._error("Save configuration", e)
            return
        show_info(self, "Save Configuration", f"Configuration saved to\n{path}")

    def _cmd_print(self):
        show_info(self, "Print", "Use File > Save to export the configuration; printing is not implemented.")

    def _cmd_rack_setup(self):
        card = self.state.card

        def apply(cfg: dict):
            card.rack_type_size = cfg_to_rack_type(cfg)
            self.state.set_card(card)

        open_rack_setup(self, self.F, on_ok=apply, initial=rack_type_to_cfg(card.rack_type_size))

    # ── Connection commands ──────────────────────────────────────────

    def _connect_with(self, title, fn):
        ok, res = run_task(self, self.F, title, fn, cancellable=False)
        if ok:
            self.state.notify("connection")
        else:
            self._error(title, res)
        return ok

    def _cmd_direct_connect(self):
        s = self.state.settings
        dlg = DirectConnectDialog(self, self.F, {"com_port": s["com_port"], "baud_rate": s["baud_rate"],
                                                 "rack_address": s["rack_address"], "serial_config": "8N1"})
        if not dlg.show():
            return
        v = dlg.values()

        # Parse serial config (e.g., "8N1" -> bytesize=8, parity="N", stopbits=1)
        serial_config = v.get("serial_config", "8N1")
        from src.sidebar.connection import SERIAL_CONFIGS
        config = SERIAL_CONFIGS.get(serial_config, SERIAL_CONFIGS["8N1"])

        self._connect_with("Connecting...", lambda p, c: self.state.connect_serial(
            v["com_port"], int(v["baud_rate"]), int(v["rack_address"]), v["connect_password"],
            config["parity"], config["bytesize"], config["stopbits"], p))

    def _cmd_network_connect(self):
        s = self.state.settings
        dlg = NetworkConnectDialog(self, self.F, {"ip_address": s["host"], "port": s["tcp_port"],
                                                  "timeout": s["timeout"], "rack_address": s["rack_address"]})
        if not dlg.show():
            return
        v = dlg.values()
        self._connect_with("Connecting...", lambda p, c: self.state.connect_network(
            v["ip_address"], int(v["port"]), int(v["rack_address"]), v["connect_password"], float(v["timeout"]), p))

    def _cmd_disconnect(self):
        if self.state.connected and disconnect_device(self):
            self.state.disconnect()

    def _cmd_refresh(self):
        if not self._need_connection():
            return
        ok, res = run_task(self, self.F, "Checking connection", lambda p, c: tasks.check_connection(self.state.link),
                           cancellable=False)
        if not ok or not res:
            self.state.disconnect()
            show_warning(self, "Connection", "The rack is no longer responding; disconnected.")

    # ── Edit commands (module clipboard) ─────────────────────────────

    def _selected_slot(self):
        sel = self._rack._selected
        if not sel:
            show_info(self, "Select a slot", "Click a slot first.")
            return None
        vb = int(sel.split("_")[1]) - 1
        if vb not in SLOT_NUMBERS:
            show_info(self, "Select a slot", "The configuration panel cannot be copied or pasted.")
            return None
        return vb

    def _cmd_copy(self):
        vb = self._selected_slot()
        if vb:
            self._sync_to_model()
            if not self.state.copy_slot(vb):
                show_info(self, "Copy", "The selected slot has no module.")

    def _cmd_cut(self):
        vb = self._selected_slot()
        if vb:
            self._sync_to_model()
            if self.state.cut_slot(vb):
                self._sync_from_model()
            else:
                show_info(self, "Cut", "The selected slot has no module.")

    def _cmd_paste(self):
        vb = self._selected_slot()
        if not vb:
            return
        clip = self.state.clipboard
        if clip is None:
            show_info(self, "Paste", "Nothing to paste.")
            return
        self._sync_to_model()
        raw = vb + 1
        data = self._rack._slot_data
        if raw > 1 and data.get(f"0_{raw - 1}") == "3000/12M/DIS":
            show_warning(self, "Paste", "This slot is the second half of a 3000/12M/DIS module.")
            return
        if clip.module == MT_VMM_12M:
            if raw not in self._rack._DIS_ALLOWED_START_SLOTS or data.get(f"0_{raw + 1}"):
                show_warning(self, "Paste", "3000/12M/DIS needs this slot and the next one to be free.")
                return
        if data.get(f"0_{raw}") and not ask_yes_no(self, "Paste", "Replace the module in this slot?"):
            return
        if self.state.paste_slot(vb):
            self._sync_from_model()

    def _cmd_select_all(self):
        show_info(self, "Select All", "Select All applies to the setpoint and channel dialogs.")

    # ── Rack operations ──────────────────────────────────────────────

    def _cmd_upload(self):
        if not self._need_connection():
            return
        if not ask_yes_no(self, "Upload from rack", "Read the configuration from the rack?\n"
                                                     "The current screen will be replaced."):
            return
        ok, res = run_task(self, self.F, "Uploading configuration", lambda p, c: self.state.upload(p, c))
        if not ok:
            self._error("Upload", res)
            return
        self._sync_from_model()
        if getattr(res, "warnings", None):
            show_warning(self, "Upload", "\n".join(res.warnings))

    def _cmd_download(self):
        if not self._need_connection():
            return
        self._sync_to_model()
        slots = [n for n in SLOT_NUMBERS if self.state.rack.slots[n].module != MT_NONE]
        chosen = ops.pick_slots(self, self.F, "Download — select slots", slots) if slots else []
        if chosen is None:
            return
        pw = ops.ask_password(self, self.F, "Download to rack", "Configuration password:")
        if pw is None:
            return
        ok, res = run_task(self, self.F, "Downloading configuration",
                           lambda p, c: self.state.download(pw, chosen, p, c))
        if ok:
            show_info(self, "Download", "Configuration downloaded to the rack.")
        else:
            self._error("Download", res)

    def _monitored_slots(self):
        return [n for n in SLOT_NUMBERS if self.state.rack.slots[n].module != MT_NONE]

    def _cmd_events(self):
        if self._need_connection():
            self._sync_to_model()
            ops.EventLogDialog(self, self.F, self.state, self._monitored_slots()).show()

    def _cmd_rtc(self):
        if self._need_connection():
            ops.rtc_dialog(self, self.F, self.state)

    def _cmd_calibrate(self):
        if self._need_connection():
            ops.calibration_dialog(self, self.F, self.state)

    def _flag_command(self, title, attr, setter):
        card = self.state.card
        new = ask_yes_no(self, title, f"{title}: enable?\n(currently {'ON' if getattr(card, attr) else 'OFF'})")
        setter(new)
        if self.state.connected:
            try:
                self.state.link.write_multi(59, [self.state.card.rack_status])
            except Exception as e:                       # noqa: BLE001
                self._error(title, e)

    def _cmd_alarm_inhibit(self):
        self._flag_command("Alarm inhibit", "alarm_inhibit", self.state.set_alarm_inhibit)

    def _cmd_trip_multiply(self):
        self._flag_command("Trip multiply", "trip_multiply", self.state.set_trip_multiply)

    def _cmd_traffic(self):
        ops.traffic_dialog(self, self.F, self.state)

    def _cmd_diag(self):
        if self._need_connection():
            ops.diagnostics_dialog(self, self.F, self.state)

    def _cmd_comm(self):
        ops.comm_settings_dialog(self, self.F, self.state)

    def _cmd_rack_address(self):
        ops.rack_address_dialog(self, self.F, self.state)

    def closeEvent(self, e):
        if self._confirm_discard():
            self.state.disconnect(quiet=True)
            e.accept()
        else:
            e.ignore()

    def _cmd_about(self):
        show_info(
            self,
            "About VMS 3000",
            "VMS 3000  Rack Configuration Software\n"
            "Version 0.5\n\n"
            "© Sarayu Infotech Solutions Pvt Ltd",
        )


# ══════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════

def main():
    app = QApplication(sys.argv)

    app.setStyle("Fusion")

    # Keep the light SCADA look regardless
    # of the OS dark-mode setting
    hints = app.styleHints()

    if hasattr(hints, "setColorScheme"):
        hints.setColorScheme(
            Qt.ColorScheme.Light
        )

    # Create the main window
    window = VMS3000()

    # Open maximized
    window.showMaximized()

    # Start application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
