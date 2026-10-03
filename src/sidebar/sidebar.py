"""
sidebar.py — VMS 3000 • Professional navy sidebar
Modern navigation buttons with unique accent colors.
"""

from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from theme import T
from qt_common import hline, qfont


_NAV_ITEMS = [
    # (label, sub-label, cmd_key, accent_color)
    ("Rack Setup",  "Configure slots",  "rack_setup", "#19C3B1"),  # Teal
    ("Load",        "Open config file", "load",       "#4F8CFF"),  # Blue
    ("Save",        "Save config file", "save",       "#A56EFF"),  # Purple
]


def build_sidebar(parent, fonts: dict, commands: dict) -> QFrame:
    """Create the sidebar and add it to *parent*'s layout."""
    sb = QFrame()
    sb.setObjectName("sidebar")
    sb.setFixedWidth(220)
    sb.setStyleSheet(f"QFrame#sidebar {{ background:{T['sidebar_bg']}; }}")

    lay = QVBoxLayout(sb)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)

    # ── Top accent line ────────────────────────────────────────────
    lay.addWidget(hline(T["accent_teal"], 3))

    # ── Section header ────────────────────────────────────────────
    hdr = QWidget()
    hdr.setStyleSheet(f"background:{T['sidebar_dark']};")
    hl = QVBoxLayout(hdr)
    hl.setContentsMargins(14, 14, 14, 14)
    t = QLabel("N A V I G A T I O N")
    t.setFont(qfont("Segoe UI", 8, bold=True))
    t.setStyleSheet("color:#6B87A3; background:transparent;")
    hl.addWidget(t)
    lay.addWidget(hdr)

    # ── Navigation buttons ───────────────────────────────────────
    for label, sublabel, key, accent_color in _NAV_ITEMS:
        lay.addSpacing(4)
        row = QHBoxLayout()
        row.setContentsMargins(8, 0, 8, 0)
        row.addWidget(NavButton(fonts, label, sublabel, commands.get(key), accent_color))
        lay.addLayout(row)
        lay.addSpacing(4)

    # ── Spacer ────────────────────────────────────────────────────
    lay.addStretch(1)

    # ── Status section ────────────────────────────────────────────
    lay.addWidget(_status_block(fonts))

    # ── Bottom brand ──────────────────────────────────────────────
    lay.addWidget(_brand_block(fonts))

    pl = parent.layout() if parent is not None else None
    if pl is not None:
        pl.addWidget(sb)
    return sb


class NavButton(QFrame):
    """
    Modern two-line navigation button.

      • Unique accent color
      • Dark card background
      • Hover highlight / pressed state
      • Coloured left indicator and status dot
    """

    NORMAL_BG = "#172A3D"
    HOVER_BG = "#20384F"
    PRESSED_BG = "#102235"

    def __init__(self, fonts: dict, label: str, sublabel: str,
                 cmd: Optional[Callable], accent_color: str):
        super().__init__()
        self._cmd = cmd
        self._pressed = False
        self._hover = False
        self.setObjectName("navBtn")
        self.setFixedHeight(62)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        # Left accent indicator
        accent = QFrame()
        accent.setFixedWidth(4)
        accent.setStyleSheet(f"background:{accent_color};")
        h.addWidget(accent)

        # Content area
        inner = QVBoxLayout()
        inner.setContentsMargins(12, 9, 12, 9)
        inner.setSpacing(2)
        self._main = QLabel(label)
        self._main.setFont(fonts["ui_b"])
        self._sub = QLabel(sublabel)
        self._sub.setFont(qfont("Segoe UI", 8))
        inner.addWidget(self._main)
        inner.addWidget(self._sub)
        h.addLayout(inner, 1)

        # Small coloured status dot
        dot = QLabel("●")
        dot.setFont(qfont("Segoe UI", 7))
        dot.setStyleSheet(f"color:{accent_color}; background:transparent;")
        h.addWidget(dot)
        h.addSpacing(12)

        for w in (accent, self._main, self._sub, dot):
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._restyle()

    def _restyle(self):
        bg = (self.PRESSED_BG if self._pressed
              else self.HOVER_BG if self._hover else self.NORMAL_BG)
        self.setStyleSheet(f"QFrame#navBtn {{ background:{bg}; }}")
        hi = self._hover or self._pressed
        self._main.setStyleSheet(
            f"color:{'#FFFFFF' if hi else '#F2F7FC'}; background:transparent;")
        self._sub.setStyleSheet(
            f"color:{'#9DB4C9' if hi else '#7891A8'}; background:transparent;")

    def enterEvent(self, e):
        self._hover = True
        self._restyle()

    def leaveEvent(self, e):
        self._hover = False
        self._pressed = False
        self._restyle()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self._restyle()

    def mouseReleaseEvent(self, e):
        was_pressed = self._pressed
        self._pressed = False
        self._restyle()
        if was_pressed and e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint()):
            if self._cmd:
                self._cmd()


def _status_block(fonts: dict) -> QWidget:
    """Modern device connection status."""
    blk = QWidget()
    blk.setStyleSheet(f"background:{T['sidebar_dark']};")
    bl = QVBoxLayout(blk)
    bl.setContentsMargins(14, 13, 14, 13)

    t = QLabel("DEVICE STATUS")
    t.setFont(qfont("Segoe UI", 8, bold=True))
    t.setStyleSheet("color:#6B87A3; background:transparent;")
    bl.addWidget(t)
    bl.addSpacing(9)

    row = QHBoxLayout()
    row.setSpacing(0)
    dot = QLabel("●")
    dot.setFont(qfont("Segoe UI", 10))
    dot.setStyleSheet(f"color:{T['led_red']}; background:transparent;")
    txt = QLabel("  Not Connected")
    txt.setFont(qfont("Segoe UI", 9))
    txt.setStyleSheet(f"color:{T['sidebar_text']}; background:transparent;")
    row.addWidget(dot)
    row.addWidget(txt)
    row.addStretch(1)
    bl.addLayout(row)
    return blk


def _brand_block(fonts: dict) -> QWidget:
    """Bottom company branding."""
    brand = QWidget()
    brand.setStyleSheet(f"background:{T['sidebar_dark']};")
    bl = QVBoxLayout(brand)
    bl.setContentsMargins(0, 14, 0, 14)
    bl.setSpacing(0)

    bl.addWidget(hline(T["accent_teal"], 1))
    bl.addSpacing(10)

    a = QLabel("SARAYU INFOTECH")
    a.setFont(qfont("Segoe UI", 8, bold=True))
    a.setAlignment(Qt.AlignmentFlag.AlignCenter)
    a.setStyleSheet("color:#6B87A3; background:transparent;")
    b = QLabel("SOLUTIONS PVT LTD")
    b.setFont(qfont("Segoe UI", 8))
    b.setAlignment(Qt.AlignmentFlag.AlignCenter)
    b.setStyleSheet("color:#465E76; background:transparent;")
    bl.addWidget(a)
    bl.addWidget(b)
    return brand
