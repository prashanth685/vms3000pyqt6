"""
monitors.py — VMS 3000  •  Cascading Menu System
Cascading menu for module selection: Monitors → Proximeter/Tachometer → Models
"""

from PyQt6.QtWidgets import QMenu


class CascadingMenu:
    """
    Native OS-style cascading (flyout) menu for module selection.

    Structure (top → bottom, left → right):
      Level 1: Monitors, Gateways, Relay, No Modules
      Level 2 (Monitors): Proximeter Monitor, Tachometer Monitor
      Level 3 (Proximeter): 3000/12M/DIS, 3000/6M
      Level 3 (Tachometer): 3000/12M/TAC, 3000/6M/TAC
      Level 2 (Relay): 3000/RLY
    """

    _QSS = """
        QMenu { background:#f5f7fa; color:#1a2533; border:1px solid #b4bfcc; }
        QMenu::item { padding:5px 28px 5px 16px; }
        QMenu::item:selected { background:#3a6fcc; color:#ffffff; }
        QMenu::separator { height:1px; background:#d7dbe0; margin:3px 6px; }
    """

    def __init__(self, parent, fonts, on_selection):
        """
        Args:
            parent: Parent widget
            fonts: Font dictionary
            on_selection: Callback function when a selection is made
        """
        self._parent = parent
        self._fonts = fonts or {}
        self._on_selection = on_selection
        self._menu = None

    def _new_menu(self, parent_menu=None) -> QMenu:
        """Create a themed QMenu."""
        m = QMenu(parent_menu if parent_menu is not None else self._parent)
        m.setStyleSheet(self._QSS)
        f = self._fonts.get("sm")
        if f is not None:
            m.setFont(f)
        return m

    def _pick(self, name):
        return lambda _checked=False: self._on_selection(name)

    def show_menu(self, x, y):
        """Show the main cascading menu at the given screen coordinates."""
        main_menu = self._new_menu()
        self._menu = main_menu

        # Monitors ▸ (Proximeter Monitor ▸ / Tachometer Monitor ▸)
        self._add_monitors_submenu(main_menu)
        main_menu.addSeparator()

        # Gateways
        main_menu.addAction("Gateways").triggered.connect(self._pick("Gateways"))
        main_menu.addSeparator()

        # Relay ▸
        self._add_relay_submenu(main_menu)
        main_menu.addSeparator()

        # No Modules
        main_menu.addAction("No Modules").triggered.connect(self._pick("No Modules"))

        # Show menu at position (blocks until dismissed, like tk_popup)
        from PyQt6.QtCore import QPoint
        main_menu.exec(QPoint(int(x), int(y)))

    def _add_monitors_submenu(self, parent_menu):
        """Add Monitors submenu with cascading options."""
        monitors_menu = self._new_menu(parent_menu)
        monitors_menu.setTitle("Monitors")

        # Proximeter Monitor with its own submenu
        self._add_proximeter_submenu(monitors_menu)

        # Tachometer Monitor with its own submenu
        tach = self._new_menu(monitors_menu)
        tach.setTitle("Tachometer Monitor")
        tach.addAction("3000/12M/TAC").triggered.connect(self._pick("3000/12M/TAC"))
        tach.addAction("3000/6M/TAC").triggered.connect(self._pick("3000/6M/TAC"))
        monitors_menu.addMenu(tach)

        parent_menu.addMenu(monitors_menu)

    def _add_proximeter_submenu(self, parent_menu):
        """Add Proximeter Monitor submenu with model options."""
        prox = self._new_menu(parent_menu)
        prox.setTitle("Proximeter Monitor")
        prox.addAction("3000/12M/DIS").triggered.connect(self._pick("3000/12M/DIS"))
        prox.addAction("3000/6M").triggered.connect(self._pick("3000/6M"))
        parent_menu.addMenu(prox)

    def _add_relay_submenu(self, parent_menu):
        """Add Relay submenu with model options."""
        relay = self._new_menu(parent_menu)
        relay.setTitle("Relay")
        relay.addAction("3000/RLY").triggered.connect(self._pick("3000/RLY"))
        parent_menu.addMenu(relay)


# ══════════════════════════════════════════════════════════════════════════════
#  Standalone preview
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QLabel

    app = QApplication(sys.argv)

    class Host(QLabel):
        def mousePressEvent(self, e):
            p = e.globalPosition().toPoint()
            CascadingMenu(self, {}, lambda s: print(f"Selected: {s}")).show_menu(p.x(), p.y())

    w = Host("Click anywhere")
    w.resize(300, 200)
    w.show()
    sys.exit(app.exec())
