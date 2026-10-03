"""
securityOption.py — VMS 3000  •  Security Options Popup
Exact design matching the reference image + themed to industrial SCADA palette.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QLabel

from qt_common import (
    ThemedDialog, checkbox_qss, make_button, pick_font, show_help_dialog, group_qss,
)


class SecurityOptionsPopup:
    """
    Security Options popup — VMS 3000 SCADA theme.

      ┌─ Security Options ─────────────────────────────────────────────────────┐
      │  ┌─ Configuration Module Security Options ─────────────────────────┐   │
      │  │  ☑  Change Setpoints in Program-Mode Only                       │   │
      │  │  ☐  Disable Front Communication Port                            │   │
      │  │  ☐  Drive Rack Not OK Relay If Rack Address is Changed…         │   │
      │  │  ☐  Drive Rack Not OK Relay if a Module is Removed…             │   │
      │  │  ☐  Drive Rack Not OK Relay If Key Switch is Changes…           │   │
      │  │  ☐  Disable VSM 3000 RCS Configuration Download…               │   │
      │  └─────────────────────────────────────────────────────────────────┘   │
      │  [ Ok ]  [ Cancel ]  [ Help ]  [ Select all ]          [VMS 3000]      │
      └────────────────────────────────────────────────────────────────────────┘
    """

    _CHECKBOXES = [
        ("Change Setpoints in Program-Mode Only",
         "change_setpoints"),
        ("Disable Front Communication Port",
         "disable_front_comm"),
        ("Drive Rack Not OK Relay If Rack Address is Changed in Run Mode",
         "drive_relay_address_change"),
        ("Drive Rack Not OK Relay if a Module is Removed or Inserted into the Rack",
         "drive_relay_module_change"),
        ("Drive Rack Not OK Relay If Key Switch is Changes from Program to Run Mode",
         "drive_relay_keyswitch_change"),
        ("Disable VSM 3000 RCS Configuration Download in TCP/IP Communication Mode",
         "disable_rcs_download"),
    ]

    _HELP = (
        "Change Setpoints in Program-Mode Only\n"
        "    Allows setpoint changes only when system is in Program mode.\n\n"
        "Disable Front Communication Port\n"
        "    Disables communication through the front panel port.\n\n"
        "Drive Rack Not OK Relay If Rack Address is Changed in Run Mode\n"
        "    Triggers the Not OK relay if rack address changes during Run mode.\n\n"
        "Drive Rack Not OK Relay if a Module is Removed or Inserted into the Rack\n"
        "    Triggers the Not OK relay when modules are added or removed.\n\n"
        "Drive Rack Not OK Relay If Key Switch is Changes from Program to Run Mode\n"
        "    Triggers the Not OK relay when key switch changes to Run mode.\n\n"
        "Disable VSM 3000 RCS Configuration Download in TCP/IP Communication Mode\n"
        "    Prevents RCS configuration downloads over TCP/IP.\n\n"
        "Refer to the VMS 3000 User Manual for full security configuration details."
    )

    def __init__(self, parent, fonts):
        self._fonts = fonts
        self._parent = parent
        self._dialog = None
        self._vars = {}            # key → QCheckBox

        # Default states — first checkbox ticked, rest unchecked (matches image)
        self._defaults = {
            "change_setpoints":             True,
            "disable_front_comm":           False,
            "drive_relay_address_change":   False,
            "drive_relay_module_change":    False,
            "drive_relay_keyswitch_change": False,
            "disable_rcs_download":         False,
        }

        self._create_dialog()

    # ------------------------------------------------------------------ #

    def _create_dialog(self):
        d = ThemedDialog(self._parent, "Security Options", fonts=self._fonts,
                         size=(600, 370), header_text="  Security Options")
        self._dialog = d
        P = d.P

        # ── Security group box + checkboxes ───────────────────────────
        from PyQt6.QtWidgets import QGroupBox, QVBoxLayout
        grp = QGroupBox("  Configuration Module Security Options  ")
        grp.setFont(pick_font(self._fonts, "sm_b", size=9, bold=True))
        grp.setStyleSheet(group_qss(P))
        gl = QVBoxLayout(grp)
        gl.setSpacing(2)

        sm_b = pick_font(self._fonts, "sm_b", size=9, bold=True)
        for label_text, key in self._CHECKBOXES:
            chk = QCheckBox(f"  {label_text}")
            chk.setFont(sm_b)                               # BOLD labels
            chk.setChecked(self._defaults.get(key, False))
            chk.setCursor(Qt.CursorShape.PointingHandCursor)
            chk.setStyleSheet(checkbox_qss(P['text'], hover_bg=P['btn_hover'],
                                           padding="3px 2px", border=P['btn_border'],
                                           mark=P['accent']))
            gl.addWidget(chk)
            self._vars[key] = chk

        d.body_layout.addWidget(grp, 1)

        # ── Buttons: Ok | Cancel | Help | Select all    +   VMS 3000 badge ──
        ok = d.footer_button("Ok", self._on_ok, "primary")
        cancel = d.footer_button("Cancel", self._on_cancel)
        hlp = d.footer_button("Help", self._on_help)
        sel = d.footer_button("Select all", self._on_select_all)

        badge = QLabel("  VMS 3000  ")
        badge.setFont(pick_font(self._fonts, "ui_b", size=11, bold=True))
        badge.setStyleSheet(
            f"background:{P['accent']}; color:{P['text_white']}; padding:5px 10px;"
        )
        d.add_footer([ok, cancel, hlp, sel], align="left", right_widget=badge)

    # ------------------------------------------------------------------ #

    def _on_ok(self):
        print("Security Options saved:")
        for k, chk in self._vars.items():
            print(f"  {k}: {'Enabled' if chk.isChecked() else 'Disabled'}")
        self._dialog.accept()

    def _on_cancel(self):
        self._dialog.reject()

    def _on_select_all(self):
        for chk in self._vars.values():
            chk.setChecked(True)

    def _on_help(self):
        show_help_dialog(self._dialog, "Security Options — Help", self._HELP,
                         size=(500, 400), fonts=self._fonts)

    def values(self) -> dict:
        return {k: c.isChecked() for k, c in self._vars.items()}

    def show(self):
        """Display the dialog and block until it is closed."""
        return self._dialog.show_modal()


# ══════════════════════════════════════════════════════════════════════════════
#  Standalone preview
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from qt_common import ensure_qapp, make_fonts

    app = ensure_qapp()
    SecurityOptionsPopup(None, make_fonts()).show()
