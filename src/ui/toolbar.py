"""
toolbar.py — VMS 3000 Interactive Toolbar
Provides toolbar icons with connection functionality
"""

import os
import sys

from PyQt6.QtCore import Qt, QPoint, QSize
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QMenu, QToolButton, QWidget

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from icons import IconPainter
from src.ui.connection_dialog import ConnectionDialog
from src.ui.com_port_detector import get_available_com_ports


class Toolbar(QFrame):
    """Interactive toolbar with file operations and connection management."""

    def __init__(self, parent, bg_color="#f4f6f9"):
        super().__init__(parent)
        self.parent = parent
        self.bg_color = bg_color
        self.icon_painter = IconPainter(bg_hex=bg_color)
        self._callbacks = {}

        # Create toolbar frame (kept as ``self.frame`` for API compatibility)
        self.frame = self
        self.setFixedHeight(40)
        self.setFrameShape(QFrame.Shape.Panel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setStyleSheet(f"Toolbar {{ background:{bg_color}; }}")

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(4, 2, 4, 2)
        self._layout.setSpacing(2)

        # Build toolbar buttons
        self._build_toolbar()
        self._layout.addStretch(1)

        lay = parent.layout() if isinstance(parent, QWidget) else None
        if lay is not None:
            lay.addWidget(self)

    def _build_toolbar(self):
        """Build toolbar buttons with icons."""
        button_configs = [
            ("new", "New", self._on_new),
            ("open", "Open", self._on_open),
            ("save", "Save", self._on_save),
            ("print", "Print", self._on_print),
            ("settings", "Settings", self._on_settings),
            ("cut", "Cut", self._on_cut),
            ("copy", "Copy", self._on_copy),
            ("paste", "Paste", self._on_paste),
        ]

        for icon_name, tooltip, callback in button_configs:
            self._create_toolbar_button(icon_name, tooltip, callback)

        # Add separator
        sep = QFrame()
        sep.setFixedSize(2, 30)
        sep.setStyleSheet(f"background:{self.bg_color};")
        self._layout.addSpacing(8)
        self._layout.addWidget(sep)
        self._layout.addSpacing(8)

        # Add connection button with dropdown
        self._create_connection_button()

    def _make_button(self, icon_name, fallback_text, tooltip, callback):
        btn = QToolButton()
        try:
            pm = self.icon_painter.get(icon_name)
            btn.setIcon(self.icon_painter.get_icon(icon_name))
            btn.setIconSize(QSize(pm.width(), pm.height()) / pm.devicePixelRatio())
        except Exception:
            # Fallback if icon fails to load
            btn.setText(fallback_text)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QToolButton {{ background:{self.bg_color}; border:none; padding:4px 8px; }}"
            "QToolButton:hover, QToolButton:pressed { background:#e2e8f0; }"
        )
        btn.clicked.connect(lambda _c=False, cb=callback: cb())
        self._layout.addWidget(btn)
        return btn

    def _create_toolbar_button(self, icon_name, tooltip, callback):
        """Create a single toolbar button."""
        return self._make_button(icon_name, icon_name[0].upper(), tooltip, callback)

    def _create_connection_button(self):
        """Create connection button with dropdown menu."""
        self.connection_btn = self._make_button(
            "connection", "🔗", "Connection", self._show_connection_menu
        )

    def _show_connection_menu(self):
        """Show connection dropdown menu."""
        menu = QMenu(self)
        menu.addAction("Direct connect").triggered.connect(self._on_direct_connect)
        menu.addAction("Network connect").triggered.connect(self._on_network_connect)
        menu.addSeparator()
        menu.addAction("Disconnect").triggered.connect(self._on_disconnect)

        # Position menu below the button
        menu.exec(self.connection_btn.mapToGlobal(QPoint(0, self.connection_btn.height())))

    # ── Callback methods ──────────────────────────────────────────────────────

    def _dispatch(self, name, label):
        if name in self._callbacks:
            self._callbacks[name]()
        else:
            print(f"{label} clicked")

    def _on_new(self):
        self._dispatch("new", "New")

    def _on_open(self):
        self._dispatch("open", "Open")

    def _on_save(self):
        self._dispatch("save", "Save")

    def _on_print(self):
        self._dispatch("print", "Print")

    def _on_settings(self):
        self._dispatch("settings", "Settings")

    def _on_cut(self):
        self._dispatch("cut", "Cut")

    def _on_copy(self):
        self._dispatch("copy", "Copy")

    def _on_paste(self):
        self._dispatch("paste", "Paste")

    def _on_direct_connect(self):
        """Open direct connection dialog."""
        com_ports = get_available_com_ports()
        dialog = ConnectionDialog(self.window(), com_ports)
        result = dialog.show()
        if result:
            print(f"Direct connect: {result}")
            if "direct_connect" in self._callbacks:
                self._callbacks["direct_connect"](result)

    def _on_network_connect(self):
        self._dispatch("network_connect", "Network connect")

    def _on_disconnect(self):
        self._dispatch("disconnect", "Disconnect")

    # ── Public API for callbacks ───────────────────────────────────────────────

    def set_callback(self, action, callback):
        """Set callback for toolbar action."""
        self._callbacks[action] = callback
