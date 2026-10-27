"""
configuration_settings.py — VMS 3000  •  Configuration Settings Popup
Theme-matched to the industrial SCADA palette (navy/steel/amber/teal).
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QVBoxLayout

from qt_common import (
    ThemedDialog, group_qss, make_entry, pick_font, show_help_dialog, char_width,
)
from .securityOption import SecurityOptionsPopup
from core.config_card import ConfigCard
from qt_common import show_warning


class ConfigurationSettingsPopup:
    """
    Configuration Settings popup — VMS 3000 SCADA theme.

      • Title row  : "Configuration Settings"  ·  [VMS 3000] badge
      • Password   : group-box  (Connect PW / Config PW)
      • Ethernet   : group-box  (Device Name / IP / Mask / GW / Port)
      • Buttons    : Ok  |  Security Opt  |  Cancel  |  Help
    """

    _HELP = (
        "Connect Password\n"
        "    Password required to connect to the rack device.\n\n"
        "Configuration Password\n"
        "    Password required to access configuration settings.\n\n"
        "Network Device Name\n"
        "    Unique identifier for the rack on the network.\n\n"
        "Rack IP Address\n"
        "    Static IP address assigned to the rack unit.\n\n"
        "Rack Subnet Mask\n"
        "    Subnet mask for network segmentation.\n\n"
        "Gateway\n"
        "    Default gateway for outbound network routing.\n\n"
        "Service Port Number\n"
        "    TCP port used for Modbus / service communication (default 502).\n\n"
        "Security Options\n"
        "    SSL/TLS         — Enables encrypted transport layer.\n"
        "    Data Encryption — Encrypts payload data in transit.\n"
        "    Two-Factor Auth — Requires second authentication factor.\n\n"
        "Refer to the VMS 3000 User Manual for full details."
    )

    def __init__(self, parent, fonts, card: ConfigCard = None):
        self._fonts = fonts
        self._parent = parent
        self._dialog = None
        self._vars = {}          # field-key → QLineEdit
        self.card = card or ConfigCard()
        self.accepted = False

        c = self.card
        self._defaults = {
            "connect_password":    c.connect_password,
            "config_password":     c.config_password,
            "network_device_name": c.device_name,
            "rack_ip_address":     c.ip,
            "rack_subnet_mask":    c.subnet,
            "gateway":             c.gateway,
            "service_port_number": str(c.service_port),
        }

        self._create_dialog()

    # ------------------------------------------------------------------ #

    def _create_dialog(self):
        d = ThemedDialog(self._parent, "Configuration Settings", fonts=self._fonts,
                         size=(500, 530), header_text="  Configuration Settings")
        self._dialog = d

        self._create_password_group(d)
        self._create_ethernet_group(d)
        d.body_layout.addStretch(1)

        # ── Button strip ──────────────────────────────────────────────
        d.add_footer([
            d.footer_button("Ok", self._on_ok, "primary"),
            d.footer_button("Security Opt", self._on_security_opt, "amber"),
            d.footer_button("Cancel", self._on_cancel),
            d.footer_button("Help", self._on_help),
        ])

    def _group(self, d, title) -> QVBoxLayout:
        """Styled group box matching the SCADA palette; returns its layout."""
        grp = QGroupBox(f"  {title}  ")
        grp.setFont(pick_font(self._fonts, "sm_b", size=9, bold=True))
        grp.setStyleSheet(group_qss(d.P))
        lay = QVBoxLayout(grp)
        lay.setSpacing(8)
        d.body_layout.addWidget(grp)
        d.body_layout.addSpacing(10)
        return lay

    def _create_password_group(self, d):
        lay = self._group(d, "Password")
        self._field(lay, "Connect Password :",       "connect_password", pw=True)
        self._field(lay, "Configuration Password :", "config_password",  pw=True)

    def _create_ethernet_group(self, d):
        lay = self._group(d, "Ethernet [TCP/IP]")
        self._field(lay, "Network Device Name :", "network_device_name", pw=False)
        self._field(lay, "Rack IP Address :",     "rack_ip_address",     pw=False)
        self._field(lay, "Rack Subnet Mask :",    "rack_subnet_mask",    pw=False)
        self._field(lay, "Gateway :",             "gateway",             pw=False)
        self._field(lay, "Service Port Number :", "service_port_number", pw=False)

    def _field(self, parent_layout, label_text, key, *, pw):
        """Two-column row: bold right-aligned label + highlighted entry."""
        row = QHBoxLayout()
        row.setSpacing(8)

        sm_b = pick_font(self._fonts, "sm_b", size=9, bold=True)
        lbl = QLabel(label_text)
        lbl.setFont(sm_b)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl.setFixedWidth(char_width(sm_b, 26))      # fixed width → entries share left edge
        row.addWidget(lbl)

        mono = pick_font(self._fonts, "mono", family="Consolas", size=10)
        entry = make_entry(self._defaults.get(key, ""), password=pw, chars=22, font=mono)
        self._vars[key] = entry
        row.addWidget(entry)
        row.addStretch(1)
        parent_layout.addLayout(row)

    # ------------------------------------------------------------------ #

    def values(self) -> dict:
        return {k: e.text() for k, e in self._vars.items()}

    def _on_ok(self):
        v = self.values()
        try:
            port = int(v["service_port_number"])
        except ValueError:
            port = -1
        new = ConfigCard.from_dict(self.card.to_dict())
        new.connect_password, new.config_password = v["connect_password"], v["config_password"]
        new.device_name, new.ip = v["network_device_name"], v["rack_ip_address"]
        new.subnet, new.gateway, new.service_port = v["rack_subnet_mask"], v["gateway"], port
        errs = new.validate()
        if errs:
            show_warning(self._dialog, "Configuration Settings", "\n".join(errs))
            return
        self.card, self.accepted = new, True
        self._dialog.accept()

    def _on_cancel(self):
        self._dialog.reject()

    def _on_security_opt(self):
        """Open Security Options popup dialog."""
        pop = SecurityOptionsPopup(self._dialog, self._fonts, self.card.security)
        pop.show()
        if pop.accepted:
            self.card.security = pop.security

    def _on_help(self):
        show_help_dialog(self._dialog, "Configuration Settings — Help", self._HELP,
                         size=(480, 400), fonts=self._fonts)

    def show(self):
        """Display the dialog and block until it is closed."""
        self._dialog.show_modal()
        return self.accepted


# ══════════════════════════════════════════════════════════════════════════════
#  Standalone preview
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from qt_common import ensure_qapp, make_fonts

    app = ensure_qapp()
    ConfigurationSettingsPopup(None, make_fonts()).show()
