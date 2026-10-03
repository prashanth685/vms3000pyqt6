"""
menubar.py — VMS 3000
Dark-navy menu bar with fixed-width items and crisp separators.
"""

from typing import Optional

from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QMainWindow, QMenu, QMenuBar

from theme import T


def _menu_qss() -> str:
    return f"""
        QMenuBar {{
            background:{T['menu_bg']}; color:{T['menu_fg']};
            border:none; padding:0px;
        }}
        QMenuBar::item {{
            background:transparent; color:{T['menu_fg']};
            padding:6px 12px;
        }}
        QMenuBar::item:selected, QMenuBar::item:pressed {{
            background:{T['menu_active_bg']}; color:{T['menu_active_fg']};
        }}
        QMenu {{
            background:{T['menu_drop_bg']}; color:{T['menu_fg']};
            border:1px solid {T['menu_sep']};
        }}
        QMenu::item {{ padding:5px 30px 5px 16px; }}
        QMenu::item:selected {{
            background:{T['menu_active_bg']}; color:{T['menu_active_fg']};
        }}
        QMenu::item:disabled {{ color:#8ea3bf; }}
        QMenu::separator {{
            height:1px; background:{T['menu_sep']}; margin:4px 6px;
        }}
    """


def build_menubar(root: QMainWindow, fonts: dict, commands: dict) -> QMenuBar:
    """
    Attach a dark-navy menu bar to *root*.

    Expected command keys:
        new, open, save, save_as, direct_connect, network_connect,
        disconnect, connect, calibrate, diag, comm, about
    """
    mb = root.menuBar()
    mb.setNativeMenuBar(False)          # keep the themed in-window bar on macOS
    mb.setFont(fonts["menu"])
    mb.setStyleSheet(_menu_qss())

    def _add(menu: QMenu, label: str, cmd=None, accel: str = "",
             enabled: bool = True, bind: bool = False) -> QAction:
        """
        Add a menu entry.  *accel* is always displayed; it is only bound as a
        real keyboard shortcut when *bind* is True and a command is attached.
        """
        act = QAction(label, menu)
        if accel:
            if bind and cmd:
                act.setShortcut(QKeySequence(accel))
            else:
                act.setText(f"{label}\t{accel}")
        act.setEnabled(enabled)
        if cmd:
            act.triggered.connect(lambda _checked=False, f=cmd: f())
        menu.addAction(act)
        return act

    def _drop(label: str, items: list) -> QMenu:
        m = mb.addMenu(label)
        m.setFont(fonts["menu"])
        for item in items:
            if item is None:
                m.addSeparator()
            else:
                lbl, cmd, *rest = item
                enabled = rest[0] if rest else True
                accel = rest[1] if len(rest) > 1 else ""
                _add(m, lbl, cmd, accel, enabled)
        return m

    # ── File ────────────────────────────────────────────────────────
    file_menu = mb.addMenu("File")
    file_menu.setFont(fonts["menu"])

    _add(file_menu, "New",        commands.get("new"),     "Ctrl+N",       bind=True)
    _add(file_menu, "Open…",      commands.get("open"),    "Ctrl+O",       bind=True)
    _add(file_menu, "Save",       commands.get("save"),    "Ctrl+S",       bind=True)
    _add(file_menu, "Save As…",   commands.get("save_as"), "Ctrl+Shift+S", bind=True)

    # Connection submenu
    connection_menu = file_menu.addMenu("Connection")
    connection_menu.setFont(fonts["menu"])
    _add(connection_menu, "Direct Connect",  commands.get("direct_connect"))
    _add(connection_menu, "Network Connect", commands.get("network_connect"))
    _add(connection_menu, "Disconnect",      commands.get("disconnect"))

    file_menu.addSeparator()
    _add(file_menu, "Print…", None, "Ctrl+P")
    file_menu.addSeparator()
    _add(file_menu, "Exit", root.close, "Alt+F4")

    # ── Edit ────────────────────────────────────────────────────────
    _drop("Edit", [
        ("Undo",       None, False, "Ctrl+Z"),
        ("Redo",       None, False, "Ctrl+Y"),
        None,
        ("Cut",        None, True,  "Ctrl+X"),
        ("Copy",       None, True,  "Ctrl+C"),
        ("Paste",      None, True,  "Ctrl+V"),
        None,
        ("Select All", None, True,  "Ctrl+A"),
    ])

    # ── Utilities ───────────────────────────────────────────────────
    _drop("Utilities", [
        ("Connect",           commands.get("connect"),    True),
        ("Disconnect",        commands.get("disconnect"), True),
        None,
        ("Calibrate…",        commands.get("calibrate"),  True),
        ("Diagnostics…",      commands.get("diag"),       True),
        ("Firmware Update…",  None,                       True),
    ])

    # ── Options ─────────────────────────────────────────────────────
    _drop("Options", [
        ("Preferences…",            None,                  True),
        ("Communication Settings…", commands.get("comm"),  True),
        ("Rack Address…",           None,                  True),
        None,
        ("Theme",                   None,                  False),
    ])

    # ── View ────────────────────────────────────────────────────────
    _drop("View", [
        ("Zoom In",      None, True, "Ctrl++"),
        ("Zoom Out",     None, True, "Ctrl+-"),
        ("Reset Zoom",   None, True, "Ctrl+0"),
        None,
        ("Full Screen",  None, True, "F11"),
        ("Reset Layout", None, True),
    ])

    # ── Help ────────────────────────────────────────────────────────
    _drop("Help", [
        ("Help Topics",       None,                   True, "F1"),
        ("Quick Start Guide", None,                   True),
        None,
        ("Check for Updates", None,                   True),
        ("About VMS 3000",    commands.get("about"),  True),
    ])

    return mb
