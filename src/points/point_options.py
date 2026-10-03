"""
point_options.py — VMS 3000  •  Point Options Context Menu
Theme-matched to the industrial SCADA palette (navy/steel/amber/teal).
Provides right-click context menu for modules with Options, Setpoints and Point Names.
"""

from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QMenu

T = {
    # ── Context menu ───────────────────────────────────────────────────────
    "menu_bg":          "#ffffff",
    "menu_fg":          "#1a2533",
    "menu_active_bg":   "#e4edf9",
    "menu_active_fg":   "#1a2533",
    "menu_border":      "#c9d3e0",
    "menu_sep":         "#d7dbe0",

    # ── Text ──────────────────────────────────────────────────────────────
    "text":             "#1a2533",
    "text_dim":         "#5a6a7a",
    "text_white":       "#ffffff",

    # ── Accent ────────────────────────────────────────────────────────────
    "accent":           "#1a4fa0",
    "accent_light":     "#3a6fcc",
}


class PointOptionsContextMenu:
    """Right-click context menu with Options, Setpoints and Point Names entries."""

    def __init__(self, parent, fonts, slot_num, on_options=None, on_setpoints=None,
                 on_point_names=None):
        """
        Args:
            parent: Parent widget (usually the rack view)
            fonts: Font dictionary from main application
            slot_num: Slot number for the module
            on_options: Callback when Options is selected
            on_setpoints: Callback when Setpoints is selected
            on_point_names: Callback when Point Names is selected
        """
        self._parent = parent
        self._fonts = fonts or {}
        self._slot_num = slot_num
        self._on_options = on_options
        self._on_setpoints = on_setpoints
        self._on_point_names = on_point_names

        self._menu = QMenu(parent)
        self._menu.setStyleSheet(f"""
            QMenu {{
                background:{T['menu_bg']}; color:{T['menu_fg']};
                border:1px solid {T['menu_border']};
            }}
            QMenu::item {{ padding:5px 26px 5px 14px; }}
            QMenu::item:selected {{
                background:{T['menu_active_bg']}; color:{T['menu_active_fg']};
            }}
            QMenu::separator {{ height:1px; background:{T['menu_sep']}; margin:3px 4px; }}
        """)
        f = self._fonts.get("normal") or self._fonts.get("sm")
        if f is not None:
            self._menu.setFont(f)

        self._build_menu()

    def _build_menu(self):
        """Build the context menu items based on available callbacks."""
        # Options option
        if self._on_options:
            self._menu.addAction("Options...").triggered.connect(
                lambda _c=False: self._on_options_click())

        # Separator if we have options and will have more items
        if self._on_options and (self._on_setpoints or self._on_point_names):
            self._menu.addSeparator()

        # Setpoints option
        if self._on_setpoints:
            self._menu.addAction("Setpoints...").triggered.connect(
                lambda _c=False: self._on_setpoints_click())

        # Separator if we have setpoints and point names
        if self._on_setpoints and self._on_point_names:
            self._menu.addSeparator()

        # Point Names option
        if self._on_point_names:
            self._menu.addAction("Point Names...").triggered.connect(
                lambda _c=False: self._on_point_names_click())

    def _on_options_click(self):
        """Handle Options menu item click."""
        if self._on_options:
            self._on_options(self._slot_num)

    def _on_setpoints_click(self):
        """Handle Setpoints menu item click."""
        if self._on_setpoints:
            self._on_setpoints(self._slot_num)

    def _on_point_names_click(self):
        """Handle Point Names menu item click."""
        if self._on_point_names:
            self._on_point_names(self._slot_num)

    def show(self, x, y):
        """Display the context menu at the specified screen coordinates."""
        self._menu.exec(QPoint(int(x), int(y)))

    def destroy(self):
        """Destroy the menu."""
        self._menu.deleteLater()
