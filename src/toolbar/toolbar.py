"""
toolbar.py — VMS 3000  •  Professional toolbar (legacy variant)
Dark-title-strip + light icon band.  Groups separated by hairline rules.

This variant has the extra Upload / Download / Refresh / Key buttons and no
connection drop-down.  It shares its implementation with the top-level
toolbar.py (VmsToolbar) and only differs in the button groups.
"""

import os
import sys

# Make sure the project root (theme.py, icons.py, toolbar.py ...) is importable
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.abspath(_ROOT))

from toolbar import VmsToolbar   # top-level toolbar.py

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
        ("upload",   "Upload to Device"),
        ("download", "Download from Device"),
        ("refresh",  "Refresh / Rescan"),
    ],
    [
        ("settings", "Preferences"),
        ("key",      "License / Key"),
        ("help",     "Help              (F1)"),
    ],
]


def build_toolbar(root, fonts, rack_addr="1", command_callbacks=None):
    """Create the legacy toolbar and add it to *root*'s layout (if any)."""
    tb = VmsToolbar(root, fonts, str(rack_addr), command_callbacks,
                    groups=_GROUPS, with_connection_menu=False)
    lay = root.layout() if root is not None else None
    if lay is not None:
        lay.addWidget(tb)
    return tb
