"""
connection_dialog.py — VMS 3000 Direct Connection Dialog
Dialog for direct connect with Rack Address, COM Port, and Baud Rate
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QWidget,
)


class ConnectionDialog:
    """Direct Connect dialog as shown in the reference image."""

    def __init__(self, parent, available_com_ports=None, bg_color="#f4f6f9"):
        self.parent = parent
        self.available_com_ports = available_com_ports or []
        self.bg_color = bg_color
        self.dialog = None
        self.result = None

        # Default values
        self.rack_address = "1"
        self.com_port = available_com_ports[0] if available_com_ports else "COM1"
        self.baud_rate = "115200"
        self.password = ""

        # Widgets (created in _build_ui)
        self._password_edit = None
        self._rack_combo = None
        self._com_combo = None
        self._baud_combo = None

    def show(self):
        """Show the connection dialog (modal) and return the result."""
        self.dialog = QDialog(self.parent)
        self.dialog.setWindowTitle("Direct Connect")
        self.dialog.setModal(True)
        self.dialog.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.dialog.setObjectName("connDialog")
        self.dialog.setStyleSheet(f"QDialog#connDialog {{ background:{self.bg_color}; }}")

        self._build_ui()

        # Set minimum size to ensure all content is visible
        self.dialog.adjustSize()
        hint = self.dialog.sizeHint()
        self.dialog.setFixedSize(max(400, hint.width()), max(350, hint.height()))

        self._center_dialog()
        self.dialog.exec()
        return self.result

    def _center_dialog(self):
        """Center dialog on screen."""
        from qt_common import center_on_screen
        center_on_screen(self.dialog)

    # ------------------------------------------------------------------ #

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Arial", 10))
        lbl.setStyleSheet("color:black; background:transparent;")
        return lbl

    def _combo(self, values, current) -> QComboBox:
        cb = QComboBox()
        cb.setFont(QFont("Arial", 10))
        cb.addItems([str(v) for v in values])
        idx = cb.findText(str(current))
        if idx >= 0:
            cb.setCurrentIndex(idx)
        cb.setStyleSheet("QComboBox { background:#ffffff; color:black; padding:3px 6px; }")
        return cb

    def _btn(self, text, cb, bg, fg, bold, pad_x):
        b = QPushButton(text)
        f = QFont("Arial", 10)
        f.setBold(bold)
        b.setFont(f)
        b.setAutoDefault(False)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet(
            f"QPushButton {{ background:{bg}; color:{fg}; border:2px outset {bg};"
            f" padding:5px {pad_x}px; }}"
            f"QPushButton:pressed {{ border-style:inset; }}"
        )
        b.clicked.connect(lambda _c=False: cb())
        return b

    def _build_ui(self):
        """Build the dialog UI matching the reference image."""
        main = QVBoxLayout(self.dialog)
        main.setContentsMargins(20, 20, 20, 20)
        main.setSpacing(0)

        def block(label_text, widget, gap_after):
            main.addWidget(self._field_label(label_text))
            main.addSpacing(5)
            main.addWidget(widget)
            main.addSpacing(gap_after)

        # ── Connect Password ───────────────────────────────────────────
        self._password_edit = QLineEdit(self.password)
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_edit.setFont(QFont("Arial", 10))
        self._password_edit.setStyleSheet(
            "QLineEdit { background:#ffffff; color:black; border:1px solid #444; padding:2px 4px; }"
        )
        block("Connect Password:", self._password_edit, 15)

        # ── Rack Address ───────────────────────────────────────────────
        self._rack_combo = self._combo(range(1, 256), self.rack_address)   # 1-255
        block("Rack Address:", self._rack_combo, 15)

        # ── COM Port ───────────────────────────────────────────────────
        self._com_combo = self._combo(
            self.available_com_ports if self.available_com_ports else ["COM1"],
            self.com_port,
        )
        block("COM Port:", self._com_combo, 15)

        # ── Baud Rate ──────────────────────────────────────────────────
        self._baud_combo = self._combo(["9600", "19200", "57600", "115200"], self.baud_rate)
        block("Baud Rate:", self._baud_combo, 25)

        main.addStretch(1)

        # ── Buttons ────────────────────────────────────────────────────
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self._btn("Connect", self._on_connect, "#4a90e2", "white", True, 20))
        row.addWidget(self._btn("Browse", self._on_browse, "#e0e0e0", "black", False, 15))
        row.addWidget(self._btn("Cancel", self._on_cancel, "#e0e0e0", "black", False, 15))
        row.addStretch(1)
        row.addWidget(self._btn("Help", self._on_help, "#e0e0e0", "black", False, 15))
        main.addLayout(row)

    # ------------------------------------------------------------------ #

    def _on_connect(self):
        """Handle Connect button click."""
        self.password = self._password_edit.text()
        self.rack_address = self._rack_combo.currentText()
        self.com_port = self._com_combo.currentText()
        self.baud_rate = self._baud_combo.currentText()
        self.result = {
            "password": self.password,
            "rack_address": self.rack_address,
            "com_port": self.com_port,
            "baud_rate": self.baud_rate,
        }
        self.dialog.accept()

    def _on_browse(self):
        """Handle Browse button click."""
        print("Browse clicked")
        # TODO: Implement browse functionality

    def _on_cancel(self):
        """Handle Cancel button click."""
        self.result = None
        self.dialog.reject()

    def _on_help(self):
        """Handle Help button click."""
        print("Help clicked")
        # TODO: Implement help functionality
