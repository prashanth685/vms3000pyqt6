"""
rack_setup.py — VMS 3000  •  Rack Setup dialog
Card-type design matching the Configuration Settings popup.

Usage from main.py:

    from src.sidebar.rack_setup import open_rack_setup

    def handle_rack_config(cfg: dict):
        # cfg = {"system_type": "ch20", "rack_size": "full", "interface": "standard"}
        print(cfg)

    open_rack_setup(window, fonts, on_ok=handle_rack_config)
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QButtonGroup, QGroupBox, QRadioButton, QVBoxLayout

from qt_common import ThemedDialog, group_qss, pick_font

_SYSTEM_TYPES = [
    ("standard",         "Standard"),
    ("standard_display", "Standard With Local Display"),
    ("ch20",             "20 Channel With Local Display And Relay"),
]

_RACK_SIZES = [
    ("full", "Full Rack [12 Slots]"),
    ("mini", "Mini Rack [6 Slots]"),
]

_INTERFACES = [
    ("standard", "Standard Rack Interface Module"),
    ("ethernet", "Ethernet Interface Module"),
]

# System types that lock the rack to Full Rack / Standard Interface only.
_LOCKED_TYPES = {"ch20"}


def open_rack_setup(parent, fonts: dict = None, on_ok=None, on_cancel=None,
                    initial: dict = None):
    """Show the (modal) Rack Setup dialog. Returns the config dict, or None if cancelled."""
    fonts = fonts or {}
    initial = initial or {"system_type": "ch20", "rack_size": "full", "interface": "standard"}

    d = ThemedDialog(parent, "Rack Setup", fonts=fonts, size=(420, 500),
                     header_text="  Rack Setup")
    P = d.P
    f_group = pick_font(fonts, "_group", size=9, bold=True)
    f_item = pick_font(fonts, "ui", size=9)

    def _group(label):
        grp = QGroupBox(f"  {label}  ")
        grp.setFont(f_group)
        grp.setStyleSheet(group_qss(P))
        lay = QVBoxLayout(grp)
        lay.setSpacing(4)
        d.body_layout.addWidget(grp)
        d.body_layout.addSpacing(10)
        return grp, lay

    def _radios(lay, items, current):
        group = QButtonGroup(d)
        widgets = {}
        for value, text in items:
            rb = QRadioButton(text)
            rb.setFont(f_item)
            rb.setCursor(Qt.CursorShape.PointingHandCursor)
            rb.setStyleSheet(
                f"QRadioButton {{ color:{P['text']}; background:transparent; padding:2px 0; }}"
                f"QRadioButton:disabled {{ color:{P['text_dim']}; }}"
                f"QRadioButton::indicator {{ width:12px; height:12px; border-radius:7px;"
                f" border:1px solid {P['btn_border']}; background:#ffffff; }}"
                f"QRadioButton::indicator:checked {{ background:qradialgradient(cx:.5, cy:.5, radius:.5,"
                f" fx:.5, fy:.5, stop:0 {P['accent']}, stop:.55 {P['accent']}, stop:.6 #ffffff, stop:1 #ffffff); }}"
                f"QRadioButton::indicator:disabled {{ background:#e5e9ef; border-color:#b4bfcc; }}"
            )
            rb.setChecked(value == current)
            group.addButton(rb)
            lay.addWidget(rb)
            widgets[value] = rb
        return group, widgets

    _, lay_sys = _group("System Type")
    sys_group, sys_w = _radios(lay_sys, _SYSTEM_TYPES, initial.get("system_type", "ch20"))

    _, lay_rack = _group("Rack Size")
    rack_group, rack_w = _radios(lay_rack, _RACK_SIZES, initial.get("rack_size", "full"))

    _, lay_if = _group("Interface Module")
    if_group, if_w = _radios(lay_if, _INTERFACES, initial.get("interface", "standard"))

    d.body_layout.addStretch(1)

    def _value(widgets):
        for v, w in widgets.items():
            if w.isChecked():
                return v
        return None

    # ── Dependency logic: 20-channel type locks rack size + interface ──
    def _apply_lock(*_a):
        locked = _value(sys_w) in _LOCKED_TYPES
        if locked:
            rack_w["full"].setChecked(True)
            if_w["standard"].setChecked(True)
        rack_w["mini"].setEnabled(not locked)
        if_w["ethernet"].setEnabled(not locked)

    for rb in sys_w.values():
        rb.toggled.connect(_apply_lock)
    _apply_lock()

    outcome = {"cfg": None}

    def _ok():
        cfg = {
            "system_type": _value(sys_w),
            "rack_size": _value(rack_w),
            "interface": _value(if_w),
        }
        outcome["cfg"] = cfg
        if on_ok:
            on_ok(cfg)
        d.accept()

    def _close():
        if on_cancel:
            on_cancel()
        d.reject()

    d.add_footer([d.footer_button("Ok", _ok, "primary"),
                  d.footer_button("Cancel", _close)])

    d.show_modal()
    return outcome["cfg"]


# ── Standalone test ─────────────────────────────────────────────────
if __name__ == "__main__":
    from qt_common import ensure_qapp, make_fonts

    app = ensure_qapp()
    print("Saved:", open_rack_setup(None, make_fonts(), on_ok=lambda cfg: print("Saved:", cfg)))
