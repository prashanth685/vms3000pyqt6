"""
main.py — VMS 3000 Rack Configuration Software v0.5   (PyQt6)
"""

import datetime
import sys

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
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


class VMS3000(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            "VMS 3000  —  Rack Configuration Software  v0.5"
        )

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
            "print": lambda: print("Print action"),
            "settings": lambda: print("Settings action"),
            "cut": lambda: print("Cut action"),
            "copy": lambda: print("Copy action"),
            "paste": lambda: print("Paste action"),
            "upload": lambda: print("Upload action"),
            "download": lambda: print("Download action"),
            "refresh": lambda: print("Refresh action"),
            "help": self._cmd_about,
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
                "calibrate": None,
                "diag": self._cmd_diag,
                "comm": self._cmd_comm,
                "about": self._cmd_about,
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

    def _set_connection(self, connected: bool):
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

    def _cmd_new(self):
        if ask_yes_no(
            self,
            "New Configuration",
            "Start a new configuration?\n"
            "Unsaved changes will be lost.",
        ):
            self._rack.clear()

    def _cmd_open(self):
        self._rack.load_configuration()

    def _cmd_save(self):
        self._rack.save_configuration()

    def _cmd_save_as(self):
        show_info(
            self,
            "Save As",
            "Save As ready.",
        )

    def _cmd_rack_setup(self):

        def handle_rack_config(cfg: dict):
            print(
                f"Rack configuration: {cfg}"
            )

            # You can apply the configuration here

        open_rack_setup(
            self,
            self.F,
            on_ok=handle_rack_config,
        )

    def _cmd_direct_connect(self):
        # Update connection status only if
        # the user actually pressed Connect
        if DirectConnectDialog(
            self,
            self.F,
        ).show():
            self._set_connection(True)

    def _cmd_network_connect(self):
        if NetworkConnectDialog(
            self,
            self.F,
        ).show():
            self._set_connection(True)

    def _cmd_disconnect(self):
        if disconnect_device(self):
            self._set_connection(False)

    def _cmd_diag(self):
        show_info(
            self,
            "Diagnostics",
            "System OK — no faults detected.",
        )

    def _cmd_comm(self):
        show_info(
            self,
            "Communication Settings",
            "Communication settings ready.",
        )

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
