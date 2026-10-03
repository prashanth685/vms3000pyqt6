"""
connection.py — VMS 3000  •  Connection Dialogs
Theme-matched to the industrial SCADA palette (navy/steel/amber/teal).
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout, QGroupBox, QLabel, QListWidget, QVBoxLayout,
)

from qt_common import (
    ThemedDialog, ask_yes_no, char_width, group_qss, make_button, make_entry,
    pick_font, show_help_dialog, show_info,
)


class _ConnectBase:
    """Shared plumbing for the Direct / Network connect dialogs."""

    TITLE = ""
    SIZE = (450, 320)
    GROUP = ""

    def __init__(self, parent, fonts):
        self._fonts = fonts
        self._parent = parent
        self._dialog = None
        self._vars = {}          # key → QLineEdit
        self._connected = False
        self._defaults = {}
        self._create_dialog()

    # -- building -------------------------------------------------------
    def _create_dialog(self):
        d = ThemedDialog(self._parent, self.TITLE, fonts=self._fonts, size=self.SIZE,
                         header_text=f"  {self.TITLE}")
        self._dialog = d

        grp = QGroupBox(f"  {self.GROUP}  ")
        grp.setFont(pick_font(self._fonts, "sm_b", size=9, bold=True))
        grp.setStyleSheet(group_qss(d.P))
        self._grp_layout = QVBoxLayout(grp)
        self._grp_layout.setSpacing(8)
        d.body_layout.addWidget(grp)
        d.body_layout.addStretch(1)

        self._fill_group()
        self._add_buttons(d)

    def _fill_group(self):
        raise NotImplementedError

    def _add_buttons(self, d):
        raise NotImplementedError

    def _field(self, label_text, key, *, pw=False, chars=18, extra=None):
        """Bold right-aligned label + highlighted entry (+ optional extra widget)."""
        row = QHBoxLayout()
        row.setSpacing(8)
        sm_b = pick_font(self._fonts, "sm_b", size=9, bold=True)
        lbl = QLabel(label_text)
        lbl.setFont(sm_b)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl.setFixedWidth(char_width(sm_b, 18))
        row.addWidget(lbl)

        mono = pick_font(self._fonts, "mono", family="Consolas", size=10)
        entry = make_entry(self._defaults.get(key, ""), password=pw, chars=chars, font=mono)
        self._vars[key] = entry
        row.addWidget(entry)
        if extra is not None:
            row.addWidget(extra)
        row.addStretch(1)
        self._grp_layout.addLayout(row)
        return entry

    def values(self) -> dict:
        return {k: e.text() for k, e in self._vars.items()}

    def _on_cancel(self):
        self._dialog.reject()

    def show(self):
        """Display the dialog (modal). Returns True if the user pressed Connect."""
        self._dialog.show_modal()
        return self._connected


# ══════════════════════════════════════════════════════════════════════════════
#  DIRECT CONNECT DIALOG
# ══════════════════════════════════════════════════════════════════════════════

class DirectConnectDialog(_ConnectBase):
    """Direct Connect dialog — direct connection to the rack via serial/USB."""

    TITLE = "Direct Connect"
    GROUP = "Connection Settings"
    SIZE = (450, 320)

    _HELP = (
        "Connect Password\n"
        "    Password required to connect to the rack device.\n\n"
        "Rack Address\n"
        "    Unique address of the rack (1-255). Click Browse to select.\n\n"
        "COM Port\n"
        "    Serial port for direct connection (COM1-COM16).\n\n"
        "Baud Rate\n"
        "    Communication speed for serial connection.\n\n"
        "Click Connect to establish the connection."
    )

    def __init__(self, parent, fonts):
        super().__init__(parent, fonts)

    def _create_dialog(self):
        self._defaults = {
            "connect_password": "",
            "rack_address": "1",
            "com_port": "COM1",
            "baud_rate": "9600",
        }
        super()._create_dialog()

    def _fill_group(self):
        self._field("Connect Password :", "connect_password", pw=True)

        browse = make_button("Browse…", self._on_browse_rack, "normal",
                             pick_font(self._fonts, "sm", size=8), self._dialog.P,
                             pad="4px 8px")
        self._field("Rack Address :", "rack_address", chars=10, extra=browse)

        self._field("COM Port :", "com_port")
        self._field("Baud Rate :", "baud_rate")

    def _add_buttons(self, d):
        d.add_footer([
            d.footer_button("Connect", self._on_connect, "primary"),
            d.footer_button("Browse", self._on_browse),
            d.footer_button("Cancel", self._on_cancel),
            d.footer_button("Help", self._on_help),
        ])

    def _on_browse_rack(self):
        """Browse for rack address - shows available rack addresses."""
        dlg = ThemedDialog(self._dialog, "Select Rack Address", fonts=self._fonts,
                           size=(300, 400), badge=False, title_pt=10, title_bar_pad=8,
                           header_text="  Rack Addresses", body_margins=(12, 12, 12, 12))
        P = dlg.P
        lbl = QLabel("Available Rack Addresses:")
        lbl.setFont(pick_font(self._fonts, "sm_b", size=9, bold=True))
        dlg.body_layout.addWidget(lbl)
        dlg.body_layout.addSpacing(8)

        lst = QListWidget()
        lst.setFont(pick_font(self._fonts, "mono", family="Consolas", size=9))
        lst.setStyleSheet(
            f"QListWidget {{ background:#ffffff; color:{P['text']}; border:1px solid {P['btn_border']}; }}"
            f"QListWidget::item:selected {{ background:{P['accent_light']}; color:{P['text_white']}; }}"
        )
        # Add addresses 1-255
        for i in range(1, 256):
            lst.addItem(f"Rack {i:03d}")
        dlg.body_layout.addWidget(lst, 1)
        dlg.body_layout.addSpacing(12)

        def _on_select():
            item = lst.currentItem()
            if item is not None:
                # Extract number from "Rack 001" format
                self._vars["rack_address"].setText(item.text().split()[1])
                dlg.accept()

        ub = pick_font(self._fonts, "ui_b", size=9, bold=True)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(make_button("Cancel", dlg.reject, "normal", ub, P, pad="6px 12px"))
        row.addWidget(make_button("Select", _on_select, "primary", ub, P, pad="6px 12px"))
        dlg.body_layout.addLayout(row)
        dlg.show_modal()

    def _on_connect(self):
        print("Direct Connect settings:")
        for k, v in self.values().items():
            print(f"  {k}: {v}")
        show_info(self._dialog, "Direct Connect", "Connecting to device...")
        self._connected = True
        self._dialog.accept()

    def _on_browse(self):
        """Browse for configuration file or device."""
        show_info(self._dialog, "Browse", "Browse functionality for Direct Connect.")

    def _on_help(self):
        show_help_dialog(self._dialog, "Direct Connect — Help", self._HELP,
                         size=(450, 350), fonts=self._fonts)


# ══════════════════════════════════════════════════════════════════════════════
#  NETWORK CONNECT DIALOG
# ══════════════════════════════════════════════════════════════════════════════

class NetworkConnectDialog(_ConnectBase):
    """Network Connect dialog — network connection to the rack via TCP/IP."""

    TITLE = "Network Connect"
    GROUP = "Network Settings"
    SIZE = (450, 320)

    def _create_dialog(self):
        self._defaults = {
            "connect_password": "",
            "rack_address": "1",
            "ip_address": "192.168.1.255",
            "port": "502",
        }
        super()._create_dialog()

    def _fill_group(self):
        self._field("IP Address :", "ip_address")
        self._field("Port :", "port")
        self._field("Timeout (sec) :", "timeout")

    def _add_buttons(self, d):
        d.add_footer([
            d.footer_button("Connect", self._on_connect, "primary"),
            d.footer_button("Cancel", self._on_cancel),
        ])

    def _on_connect(self):
        print("Network Connect settings:")
        for k, v in self.values().items():
            print(f"  {k}: {v}")
        show_info(self._dialog, "Network Connect", "Connecting to device...")
        self._connected = True
        self._dialog.accept()


# ══════════════════════════════════════════════════════════════════════════════
#  DISCONNECT FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def disconnect_device(parent):
    """Disconnect from the currently connected device."""
    result = ask_yes_no(parent, "Disconnect",
                        "Are you sure you want to disconnect from the device?")
    if result:
        print("Device disconnected")
        show_info(parent, "Disconnect", "Device disconnected successfully.")
        return True
    return False


# ══════════════════════════════════════════════════════════════════════════════
#  Standalone preview
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget
    from qt_common import ensure_qapp, make_fonts

    app = ensure_qapp()
    fonts = make_fonts()

    w = QWidget()
    w.setWindowTitle("VMS 3000 - Connection Test")
    w.resize(400, 300)
    lay = QHBoxLayout(w)
    for text, fn in (
        ("Direct Connect", lambda: DirectConnectDialog(w, fonts).show()),
        ("Network Connect", lambda: NetworkConnectDialog(w, fonts).show()),
        ("Disconnect", lambda: disconnect_device(w)),
    ):
        b = QPushButton(text)
        b.clicked.connect(lambda _c=False, f=fn: f())
        lay.addWidget(b)
    w.show()
    sys.exit(app.exec())
