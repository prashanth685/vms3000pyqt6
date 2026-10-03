"""
toolbar.py — VMS 3000  •  Professional toolbar
Dark-title-strip + light icon band.  Groups separated by hairline rules.
"""

import sys
import os
from typing import Callable, Optional

from PyQt6.QtCore import Qt, QPoint, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu, QToolButton, QVBoxLayout,
    QWidget,
)

from theme import T
from icons import IconPainter

# Add src to path for UI components
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from ui.connection_dialog import ConnectionDialog
from ui.com_port_detector import get_available_com_ports

# Icon groups: list of (key, tooltip)
_GROUPS = [
    [
        ("new",      "New File          (Ctrl+N)"),
        ("open",     "Open…             (Ctrl+O)"),
        ("save",     "Save              (Ctrl+S)"),
        ("print",    "Print…            (Ctrl+P)"),
    ],
    [
        ("cut",      "Cut               (Ctrl+X)"),
        ("copy",     "Copy              (Ctrl+C)"),
        ("paste",    "Paste             (Ctrl+V)"),
    ],
    [
        ("settings", "Preferences"),
        ("connection", "Connection"),
        ("help",     "Help              (F1)"),
    ],
]


class VmsToolbar(QWidget):
    """Title strip + icon band.  Exposes ``rack_edit`` (the Rack Address box)."""

    def __init__(self, parent, fonts: dict, rack_addr: str = "1",
                 command_callbacks: Optional[dict] = None,
                 groups=None, with_connection_menu: bool = True):
        super().__init__(parent)
        self._fonts = fonts
        self._callbacks = command_callbacks or {}
        self._groups = groups if groups is not None else _GROUPS
        self._with_connection_menu = with_connection_menu
        self.icons = IconPainter(T["toolbar_bg"])
        self._buttons: dict = {}

        # ── Outer container (provides the 1 px bottom border) ──────────
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.setStyleSheet(f"VmsToolbar {{ background:{T['toolbar_border']}; }}")

        # ── Title strip  (dark navy, 36 px tall) ───────────────────────
        strip = QWidget()
        strip.setFixedHeight(36)
        strip.setStyleSheet(f"background:{T['titlebar']};")
        sl = QHBoxLayout(strip)
        sl.setContentsMargins(12, 4, 12, 4)

        left = QLabel("VMS 3000  —  Rack Configuration Software  v0.5")
        left.setFont(fonts["ui_b"])
        left.setStyleSheet("color:#a8c8e8; background:transparent;")
        sl.addWidget(left)
        sl.addStretch(1)

        right = QLabel("Sarayu Infotech Solutions Pvt Ltd")
        right.setFont(fonts["ui"])
        right.setStyleSheet("color:#7090b0; background:transparent;")
        sl.addWidget(right)
        outer.addWidget(strip)

        # ── Icon band ──────────────────────────────────────────────────
        band = QWidget()
        band.setStyleSheet(f"background:{T['toolbar_bg']};")
        bl = QHBoxLayout(band)
        bl.setContentsMargins(6, 6, 6, 6)
        bl.setSpacing(4)

        for g_idx, group in enumerate(self._groups):
            if g_idx:
                bl.addWidget(self._sep())
            for key, tip in group:
                bl.addWidget(self._icon_btn(key, tip))

        # Right-side controls
        bl.addWidget(self._sep())
        bl.addWidget(self._badge())
        bl.addWidget(self._sep())
        self._add_rack_addr(bl, rack_addr)
        bl.addStretch(1)

        outer.addWidget(band)
        outer.addSpacing(1)

    # ── Helpers ─────────────────────────────────────────────────────────

    def _sep(self) -> QFrame:
        """Hairline vertical separator."""
        f = QFrame()
        f.setFixedWidth(1)
        f.setMinimumHeight(28)
        f.setStyleSheet(f"background:{T['toolbar_sep']};")
        return f

    def _badge(self) -> QWidget:
        """VMS 3000 badge pill."""
        lbl = QLabel("VMS 3000")
        lbl.setFont(self._fonts["vms"])
        lbl.setStyleSheet(
            f"background:{T['titlebar']}; color:#ffffff; padding:4px 12px;"
        )
        return lbl

    def _add_rack_addr(self, layout: QHBoxLayout, value: str) -> None:
        lbl = QLabel("Rack Address")
        lbl.setFont(self._fonts["ui"])
        lbl.setStyleSheet(f"color:{T['text_dim']}; background:transparent;")
        layout.addWidget(lbl)

        self.rack_edit = QLineEdit(value)
        self.rack_edit.setFont(self._fonts["ui_b"])
        self.rack_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rack_edit.setFixedWidth(70)
        self.rack_edit.setStyleSheet(
            f"QLineEdit {{ background:#ffffff; color:{T['text']};"
            f" border:2px inset {T['toolbar_border']}; padding:2px; }}"
        )
        layout.addWidget(self.rack_edit)

    def rack_address(self) -> str:
        return self.rack_edit.text()

    def _icon_btn(self, key: str, tip: str) -> QToolButton:
        pm = self.icons.get(key)
        btn = QToolButton()
        btn.setIcon(self.icons.get_icon(key))
        btn.setIconSize(QSize(pm.width(), pm.height()) / pm.devicePixelRatio())
        btn.setToolTip(tip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setAutoRaise(False)
        btn.setStyleSheet(f"""
            QToolButton {{
                background:{T['toolbar_bg']};
                border:1px solid {T['toolbar_border']};
                padding:4px 6px;
            }}
            QToolButton:hover {{
                background:{T['btn_hover']};
                border:1px solid {T['accent']};
            }}
            QToolButton:pressed {{
                background:{T['btn_press']};
                border:1px solid {T['accent']};
            }}
        """)
        btn.clicked.connect(lambda _c=False, k=key, b=btn: self._handle_click(k, b))
        self._buttons[key] = btn
        return btn

    # ── Click handling ──────────────────────────────────────────────────

    def _handle_click(self, key: str, button: QToolButton) -> None:
        """Handle toolbar button clicks."""

        # Special handling for connection button
        if key == "connection" and self._with_connection_menu:
            self._show_connection_menu(button)
            return

        # Check if there's a callback registered for this action
        if key in self._callbacks:
            try:
                self._callbacks[key]()
            except Exception as e:
                print(f"Error executing callback for {key}: {e}")
        else:
            # Default behavior for unregistered buttons
            print(f"{key} clicked (no callback registered)")

    def _show_connection_menu(self, button: QToolButton) -> None:
        """Show connection dropdown menu below the button."""
        menu = QMenu(self)
        menu.addAction("Direct connect").triggered.connect(self._on_direct_connect)
        menu.addAction("Network connect").triggered.connect(self._on_network_connect)
        menu.addSeparator()
        menu.addAction("Disconnect").triggered.connect(self._on_disconnect)
        menu.exec(button.mapToGlobal(QPoint(0, button.height())))

    def _on_direct_connect(self) -> None:
        """Open direct connection dialog."""
        try:
            com_ports = get_available_com_ports()
            dialog = ConnectionDialog(self.window(), com_ports)
            result = dialog.show()
            if result:
                print(f"Direct connect: {result}")
        except Exception as e:
            print(f"Error opening direct connect dialog: {e}")

    def _on_network_connect(self) -> None:
        """Handle network connect."""
        print("Network connect clicked")
        # TODO: Implement network connect functionality

    def _on_disconnect(self) -> None:
        """Handle disconnect."""
        print("Disconnect clicked")
        # TODO: Implement disconnect functionality


def build_toolbar(parent, fonts: dict, rack_addr="1", command_callbacks=None) -> VmsToolbar:
    """
    Create the toolbar and add it to *parent*'s layout (if it has one).

    ``rack_addr`` is the initial Rack Address text (a plain string; the old
    tk.StringVar is no longer needed — read it back with ``toolbar.rack_address()``).
    """
    tb = VmsToolbar(parent, fonts, str(rack_addr), command_callbacks)
    lay = parent.layout() if parent is not None else None
    if lay is not None:
        lay.addWidget(tb)
    return tb
