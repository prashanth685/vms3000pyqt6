"""
toolbar.py — VMS 3000 • Professional toolbar
Light icon band with grouped toolbar actions.
"""

import sys
import os
from typing import Optional

from PyQt6.QtCore import Qt, QPoint, QSize
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from theme import T
from icons import IconPainter

# Add src to path for UI components
sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
)

from ui.connection_dialog import ConnectionDialog
from ui.com_port_detector import get_available_com_ports


# ──────────────────────────────────────────────────────────────────────
# Icon groups
# ──────────────────────────────────────────────────────────────────────

_GROUPS = [
    [
        ("new", "New File          (Ctrl+N)"),
        ("open", "Open…             (Ctrl+O)"),
        ("save", "Save              (Ctrl+S)"),
        ("print", "Print…            (Ctrl+P)"),
    ],
    [
        ("cut", "Cut               (Ctrl+X)"),
        ("copy", "Copy              (Ctrl+C)"),
        ("paste", "Paste             (Ctrl+V)"),
    ],
    [
        ("settings", "Preferences"),
        ("connection", "Connection"),
        ("help", "Help              (F1)"),
    ],
]


class VmsToolbar(QWidget):
    """
    Professional VMS 3000 toolbar.

    Contains:
        - Toolbar action icons
        - Group separators
        - VMS 3000 badge
        - Rack Address input
    """

    def __init__(
        self,
        parent,
        fonts: dict,
        rack_addr: str = "1",
        command_callbacks: Optional[dict] = None,
        groups=None,
        with_connection_menu: bool = True,
    ):
        super().__init__(parent)

        self._fonts = fonts
        self._callbacks = command_callbacks or {}
        self._groups = groups if groups is not None else _GROUPS
        self._with_connection_menu = with_connection_menu

        self.icons = IconPainter(T["toolbar_bg"])
        self._buttons: dict = {}

        # ──────────────────────────────────────────────────────────────
        # Outer container
        # ──────────────────────────────────────────────────────────────

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.setStyleSheet(
            f"VmsToolbar {{ background:{T['toolbar_border']}; }}"
        )

        # ──────────────────────────────────────────────────────────────
        # Icon band
        # ──────────────────────────────────────────────────────────────

        band = QWidget()
        band.setStyleSheet(
            f"background:{T['toolbar_bg']};"
        )

        bl = QHBoxLayout(band)
        bl.setContentsMargins(6, 6, 6, 6)
        bl.setSpacing(4)

        # Add grouped toolbar buttons
        for g_idx, group in enumerate(self._groups):

            # Separator between groups
            if g_idx:
                bl.addWidget(self._sep())

            for key, tip in group:
                bl.addWidget(
                    self._icon_btn(key, tip)
                )

        # ──────────────────────────────────────────────────────────────
        # Right-side controls
        # ──────────────────────────────────────────────────────────────

        # Separator before badge
        bl.addWidget(self._sep())

        # VMS 3000 badge
        bl.addWidget(self._badge())

        # Separator before Rack Address
        bl.addWidget(self._sep())

        # Rack Address
        self._add_rack_addr(bl, rack_addr)

        # Push everything to the left
        bl.addStretch(1)

        outer.addWidget(band)

        # 1 px bottom spacing/border
        outer.addSpacing(1)

    # ──────────────────────────────────────────────────────────────────
    # Toolbar helpers
    # ──────────────────────────────────────────────────────────────────

    def _sep(self) -> QFrame:
        """
        Create a thin vertical separator between toolbar groups.
        """

        frame = QFrame()

        frame.setFixedWidth(1)
        frame.setMinimumHeight(28)

        frame.setStyleSheet(
            f"background:{T['toolbar_sep']};"
        )

        return frame

    def _badge(self) -> QWidget:
        """
        VMS 3000 badge.
        """

        label = QLabel("VMS 3000")

        label.setFont(
            self._fonts["vms"]
        )

        label.setStyleSheet(
            f"""
            background:{T['titlebar']};
            color:#ffffff;
            padding:4px 12px;
            """
        )

        return label

    def _add_rack_addr(
        self,
        layout: QHBoxLayout,
        value: str,
    ) -> None:
        """
        Add Rack Address label and input field.
        """

        label = QLabel("Rack Address")

        label.setFont(
            self._fonts["ui"]
        )

        label.setStyleSheet(
            f"""
            color:{T['text_dim']};
            background:transparent;
            """
        )

        layout.addWidget(label)

        self.rack_edit = QLineEdit(value)

        self.rack_edit.setFont(
            self._fonts["ui_b"]
        )

        self.rack_edit.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.rack_edit.setFixedWidth(70)

        self.rack_edit.setStyleSheet(
            f"""
            QLineEdit {{
                background:#ffffff;
                color:{T['text']};
                border:2px inset {T['toolbar_border']};
                padding:2px;
            }}
            """
        )

        layout.addWidget(self.rack_edit)

    def rack_address(self) -> str:
        """
        Return the current Rack Address.
        """

        return self.rack_edit.text()

    # ──────────────────────────────────────────────────────────────────
    # Toolbar button
    # ──────────────────────────────────────────────────────────────────

    def _icon_btn(
        self,
        key: str,
        tip: str,
    ) -> QToolButton:
        """
        Create a toolbar icon button.
        """

        pixmap = self.icons.get(key)

        button = QToolButton()

        button.setIcon(
            self.icons.get_icon(key)
        )

        button.setIconSize(
            QSize(
                pixmap.width(),
                pixmap.height(),
            ) / pixmap.devicePixelRatio()
        )

        button.setToolTip(tip)

        button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        button.setAutoRaise(False)

        button.setStyleSheet(
            f"""
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
            """
        )

        button.clicked.connect(
            lambda _checked=False,
                   k=key,
                   b=button:
                self._handle_click(k, b)
        )

        self._buttons[key] = button

        return button

    # ──────────────────────────────────────────────────────────────────
    # Click handling
    # ──────────────────────────────────────────────────────────────────

    def _handle_click(
        self,
        key: str,
        button: QToolButton,
    ) -> None:
        """
        Handle toolbar button clicks.
        """

        # Connection button has its own dropdown menu
        if (
            key == "connection"
            and self._with_connection_menu
        ):
            self._show_connection_menu(button)
            return

        # Execute registered callback
        if key in self._callbacks:

            try:
                self._callbacks[key]()

            except Exception as e:
                print(
                    f"Error executing callback for {key}: {e}"
                )

        else:
            print(
                f"{key} clicked "
                f"(no callback registered)"
            )

    # ──────────────────────────────────────────────────────────────────
    # Connection menu
    # ──────────────────────────────────────────────────────────────────

    def _show_connection_menu(
        self,
        button: QToolButton,
    ) -> None:
        """
        Show connection dropdown menu below the button.
        """

        menu = QMenu(self)

        direct_action = menu.addAction(
            "Direct connect"
        )

        direct_action.triggered.connect(
            self._on_direct_connect
        )

        network_action = menu.addAction(
            "Network connect"
        )

        network_action.triggered.connect(
            self._on_network_connect
        )

        menu.addSeparator()

        disconnect_action = menu.addAction(
            "Disconnect"
        )

        disconnect_action.triggered.connect(
            self._on_disconnect
        )

        menu.exec(
            button.mapToGlobal(
                QPoint(
                    0,
                    button.height(),
                )
            )
        )

    # ──────────────────────────────────────────────────────────────────
    # Direct connection
    # ──────────────────────────────────────────────────────────────────

    def _on_direct_connect(self) -> None:
        """
        Open direct COM-port connection dialog.
        """

        try:
            com_ports = get_available_com_ports()

            dialog = ConnectionDialog(
                self.window(),
                com_ports,
            )

            result = dialog.show()

            if result:
                print(
                    f"Direct connect: {result}"
                )

        except Exception as e:
            print(
                f"Error opening direct connect dialog: {e}"
            )

    # ──────────────────────────────────────────────────────────────────
    # Network connection
    # ──────────────────────────────────────────────────────────────────

    def _on_network_connect(self) -> None:
        """
        Handle network connection.
        """

        print("Network connect clicked")

        # TODO:
        # Implement network connection functionality

    # ──────────────────────────────────────────────────────────────────
    # Disconnect
    # ──────────────────────────────────────────────────────────────────

    def _on_disconnect(self) -> None:
        """
        Handle disconnect.
        """

        print("Disconnect clicked")

        # TODO:
        # Implement disconnect functionality


# ──────────────────────────────────────────────────────────────────────
# Toolbar builder
# ──────────────────────────────────────────────────────────────────────

def build_toolbar(
    parent,
    fonts: dict,
    rack_addr="1",
    command_callbacks=None,
) -> VmsToolbar:
    """
    Create the toolbar and add it to parent's layout.

    Parameters
    ----------
    parent:
        Parent QWidget.

    fonts:
        Font dictionary used by the toolbar.

    rack_addr:
        Initial Rack Address value.

    command_callbacks:
        Optional dictionary containing callbacks for toolbar actions.

    Returns
    -------
    VmsToolbar
        The created toolbar instance.
    """

    toolbar = VmsToolbar(
        parent=parent,
        fonts=fonts,
        rack_addr=str(rack_addr),
        command_callbacks=command_callbacks,
    )

    layout = (
        parent.layout()
        if parent is not None
        else None
    )

    if layout is not None:
        layout.addWidget(toolbar)

    return toolbar
