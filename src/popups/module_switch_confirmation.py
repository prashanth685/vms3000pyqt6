"""
module_switch_confirmation.py — VMS 3000  •  Generic Module Switch Confirmation Popup
Confirmation dialog when switching between any modules
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel

from qt_common import ThemedDialog, pick_font

# Colour palette local to this popup (slightly different blues than the main theme)
PALETTE = {
    "win_bg":       "#eef1f4",
    "titlebar":     "#1d5fa8",
    "btn_face":     "#e7e9ec",
    "btn_hover":    "#f2f4f6",
    "btn_border":   "#5a5a5a",
    "text":         "#1a1a1a",
    "text_white":   "#ffffff",
    "text_dim":     "#9a9a9a",
    "accent":       "#1d5fa8",
    "accent_light": "#2f7dc4",
    "accent_teal":  "#0891b2",
}


class ModuleSwitchConfirmationPopup:
    """
    Generic confirmation popup when switching between any modules.

    Shows a message asking if the user wants to switch from current module
    to target module.
    """

    SUBTEXT = "The rest will remain the same."
    PALETTE = PALETTE

    def __init__(self, parent, fonts, current_module, target_module, on_confirm):
        """
        Args:
            parent: Parent widget
            fonts: Font dictionary
            current_module: Current module name (e.g., "3000/12M/DIS")
            target_module: Target module name (e.g., "3000/6M")
            on_confirm: Callback invoked with True (confirmed) or False (cancelled)
        """
        self._fonts = fonts
        self._parent = parent
        self._current_module = current_module
        self._target_module = target_module
        self._on_confirm = on_confirm
        self._dialog = None
        self._confirmed = False

        self._create_dialog()

    def _create_dialog(self):
        d = ThemedDialog(
            self._parent,
            "Module Switch Confirmation",
            fonts=self._fonts,
            palette=self.PALETTE,
            size=(400, 200),
            header_text="  Module Switch Confirmation  ",
            body_margins=(20, 20, 20, 20),
        )
        self._dialog = d

        # Main message
        msg = QLabel(
            f"Do you want to switch "
            f"{self._current_module} to {self._target_module}?"
        )
        msg.setFont(
            pick_font(
                self._fonts,
                "ui_b",
                size=11,
                bold=True,
            )
        )
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)

        d.body_layout.addWidget(msg)
        d.body_layout.addSpacing(10)

        # Subtext
        sub = QLabel(self.SUBTEXT)
        sub.setFont(
            pick_font(
                self._fonts,
                "sm",
                size=9,
            )
        )
        sub.setWordWrap(True)
        sub.setStyleSheet(
            f"color:{self.PALETTE['text_dim']}; "
            "background:transparent;"
        )
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        d.body_layout.addWidget(sub)
        d.body_layout.addSpacing(20)
        d.body_layout.addStretch(1)

        # ------------------------------------------------------------------
        # Yes / No buttons
        # Center the entire button group horizontally
        # ------------------------------------------------------------------
        row = QHBoxLayout()
        row.setSpacing(10)

        ub = pick_font(
            self._fonts,
            "ui_b",
            size=10,
            bold=True,
        )

        from qt_common import make_button

        yes_btn = make_button(
            "Yes",
            self._on_yes,
            "primary",
            ub,
            d.P,
            pad="8px 24px",
        )

        no_btn = make_button(
            "No",
            self._on_no,
            "normal",
            ub,
            d.P,
            pad="8px 24px",
        )

        # Add stretch on BOTH sides so buttons are centered
        row.addStretch(1)
        row.addWidget(yes_btn)
        row.addWidget(no_btn)
        row.addStretch(1)

        d.body_layout.addLayout(row)

        # Closing the window with the ✕ counts as "No"
        d.rejected.connect(self._on_rejected)

    def _on_yes(self):
        """Handle Yes button click."""
        self._confirmed = True

        if self._on_confirm:
            self._on_confirm(True)

        self._dialog.done(1)

    def _on_no(self):
        """Handle No button click."""
        self._confirmed = False

        if self._on_confirm:
            self._on_confirm(False)

        self._dialog.done(1)

    def _on_rejected(self):
        """
        Handle Esc / window-close.

        Dismiss without invoking the callback.
        """
        self._confirmed = False

    def show(self):
        """
        Display the dialog (modal) and return whether the user confirmed.
        """
        self._dialog.show_modal()
        return self._confirmed


# ══════════════════════════════════════════════════════════════════════════════
#  Standalone preview
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from qt_common import ensure_qapp, make_fonts

    app = ensure_qapp()

    popup = ModuleSwitchConfirmationPopup(
        None,
        make_fonts(),
        "3000/12M/DIS",
        "3000/6M",
        lambda c: print(f"Confirmed: {c}"),
    )

    print(f"Result: {popup.show()}")
