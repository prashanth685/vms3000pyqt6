"""
setpoins.py — VMS 3000  •  Setpoints Configuration Dialog
"Setpoints - Radial Vibration (Slot N)"

Professional "card" UI with vertical thermometer-style gauges:
  - White track background with a white padding strip on the left & right
    inside the tube (classic meter-face look)
  - Tick marks on BOTH inner edges, sitting inside the white strip
  - Thin black pointer line spanning the full tube width
  - Red triangular secondary pointer on the right side
  - Colour zones fill only the middle of the tube

    from points.setpoins import SetpointsDialog
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QWidget, QSizePolicy,
)

from qt_common import center_on_parent, checkbox_qss, hline, show_warning


# ══════════════════════════════════════════════════════════════════════════
#  THEME
# ══════════════════════════════════════════════════════════════════════════

T = {
    "win_bg":        "#eef1f6",
    "group_border":  "#c9d3e0",
    "titlebar":      "#1a3a5c",

    "text":          "#1a2533",
    "text_dim":      "#5a6a7a",

    "card_bg":       "#ffffff",
    "card_header":   "#0f6e7d",
    "card_header_fg": "#ffffff",

    "entry_bg":      "#ffffff",
    "entry_border":  "#000000",

    # ---- Gauge ----
    "gauge_bg":      "#ffffff",       # pure white track / padding
    "gauge_border":  "#000000",       # black outer border
    "gauge_yellow":  "#f2c318",
    "gauge_green":   "#2fa22a",
    "gauge_red":     "#e21f1f",
    "gauge_tick":    "#000000",       # black ticks
    "pointer":       "#000000",       # black pointer line
    "pointer2":      "#c8161d",       # red secondary triangle

    "btn_border":       "#b4bfcc",
    "btn_primary":      "#1a4fa0",
    "btn_primary_hov":  "#2a63bd",
    "btn_primary_fg":   "#ffffff",
    "btn_outline_fg":   "#1a3a5c",
    "btn_outline_bd":   "#a9b7c8",
    "btn_outline_hov":  "#e4edf9",

    "accent_teal":   "#0891b2",
    "vms_blue":      "#0d3fa0",

    "menu_bg":       "#1a3a5c",
    "menu_fg":       "#ffffff",
    "toolbar_bg":    "#eef1f6",
    "toolbar_border": "#c9d3e0",
    "card_border":   "#c9d3e0",
}

FONT_NAME = "Segoe UI"


def _font(size=9, bold=False, italic=False) -> QFont:
    f = QFont(FONT_NAME)
    f.setPointSize(size)
    f.setBold(bold)
    f.setItalic(italic)
    return f


# ══════════════════════════════════════════════════════════════════════════
#  Shared card / button helpers
# ══════════════════════════════════════════════════════════════════════════

def make_card(title, header_font):
    """
    White card panel with a teal accent header strip.
    Returns (outer_widget, body_layout) — add outer_widget to a layout.
    """
    outer = QFrame()
    outer.setStyleSheet(f"QFrame#cardOuter {{ background:{T['group_border']}; }}")
    outer.setObjectName("cardOuter")
    ol = QVBoxLayout(outer)
    ol.setContentsMargins(1, 1, 1, 1)
    ol.setSpacing(0)

    card = QWidget()
    card.setStyleSheet(f"background:{T['card_bg']};")
    cl = QVBoxLayout(card)
    cl.setContentsMargins(0, 0, 0, 0)
    cl.setSpacing(0)
    ol.addWidget(card)

    spaced_title = " ".join(list(title.upper()))
    header = QLabel(spaced_title)
    header.setFont(header_font)
    header.setStyleSheet(
        f"background:{T['card_header']}; color:{T['card_header_fg']}; padding:6px 12px;"
    )
    cl.addWidget(header)

    body = QWidget()
    body.setStyleSheet(f"background:{T['card_bg']};")
    bl = QVBoxLayout(body)
    bl.setContentsMargins(10, 10, 10, 10)
    cl.addWidget(body, 1)
    return outer, bl


def make_pill_button(text, command, font, kind="outline", enabled=True):
    """Pill-style button: kind='primary' (solid navy) or 'outline' (bordered)."""
    if kind == "primary":
        bg, fg, hov, border = T["btn_primary"], T["btn_primary_fg"], T["btn_primary_hov"], T["btn_primary"]
    else:
        bg, fg, hov, border = T["card_bg"], T["btn_outline_fg"], T["btn_outline_hov"], T["btn_outline_bd"]

    b = QPushButton(f"  {text}  ")
    b.setFont(font)
    b.setAutoDefault(False)
    b.setStyleSheet(f"""
        QPushButton {{ background:{bg}; color:{fg}; border:1px solid {border}; padding:6px 12px; }}
        QPushButton:hover {{ background:{hov}; }}
        QPushButton:disabled {{ background:#eef1f6; color:#9aa0aa; border:1px solid #c7cfda; }}
    """)
    b.setEnabled(enabled)
    b.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
    if command is not None:
        b.clicked.connect(lambda _c=False, cb=command: cb())
    return b


# ══════════════════════════════════════════════════════════════════════════
#  VerticalGauge — vertical meter with white padding strip
# ══════════════════════════════════════════════════════════════════════════

class VerticalGauge(QWidget):
    """
    Vertical meter gauge.

    Inside the tube there is a WHITE PADDING STRIP on the left and right
    (controlled by WHITE_PAD). The coloured zone fills only the middle.
    Black tick marks sit inside the white strip (never on top of colour).

      ┌──────────────────────────┐   ← black outer border
      │ ││  (white strip)    ││  │   ← ticks live here
      │ ││ ┌──────────────┐  ││  │
      │ ││ │   colour     │  ││  │   ← colour fills the middle
      │ ││ └──────────────┘  ││  │
      └──────────────────────────┘

    Repaints on resize so it always looks like a real meter.
    """

    TICK_SPACING = 10     # 10-pixel tick spacing
    WHITE_PAD    = 16     # width of the white padding strip inside the tube (px)

    def __init__(self, fonts, colors, width=120, height=300, parent=None):
        super().__init__(parent)
        self._fonts = fonts
        self._colors = colors

        # Data
        self._zones = []
        self._top_text = ""
        self._bottom_text = ""
        self._pointer_frac = None
        self._pointer2_frac = None

        self.setMinimumSize(width, 120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def sizeHint(self):
        from PyQt6.QtCore import QSize
        return QSize(120, 300)

    # ------------------------------------------------------------------
    def set_colors(self, colors):
        self._colors = colors
        self.update()

    def configure_gauge(self, zones, top_text, bottom_text,
                        pointer_frac=None, pointer2_frac=None):
        self._zones = zones or []
        self._top_text = top_text
        self._bottom_text = bottom_text
        self._pointer_frac = pointer_frac
        self._pointer2_frac = pointer2_frac
        self.update()

    # ------------------------------------------------------------------
    def paintEvent(self, event):
        w = self.width()
        h = self.height()
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(T["card_bg"]))
        if w < 20 or h < 20:
            return

        # ---- Layout ----
        left_margin = 26       # room for top/bottom numeric labels
        right_margin = 20      # room for red triangle pointer
        pad_top = 4
        pad_bot = 4

        avail_w = w - left_margin - right_margin
        tube_w = max(32, min(50, avail_w))       # meter body width
        tube_h = h - pad_top - pad_bot
        tube_x = left_margin + (avail_w - tube_w) // 2
        tube_y = pad_top

        x, y = tube_x, tube_y
        hh = tube_h

        black = QColor(T["gauge_border"])

        # 1. White base + black outer border (the frame)
        p.setPen(QPen(black, 1))
        p.setBrush(QColor(T["gauge_bg"]))
        p.drawRect(QRectF(x + 0.5, y + 0.5, tube_w, hh))

        # 2. Colour zones — inset by WHITE_PAD px on left & right
        wp = self.WHITE_PAD
        p.setPen(Qt.PenStyle.NoPen)
        for f0, f1, color in self._zones:
            y0 = y + f0 * hh
            y1 = y + f1 * hh
            p.setBrush(QColor(color))
            p.drawRect(QRectF(x + 1 + wp, y0, (tube_w - 2 - 2 * wp), y1 - y0))

        # 3. Black outer border redrawn on top (keeps edges crisp)
        p.setPen(QPen(black, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(x + 0.5, y + 0.5, tube_w, hh))

        # 4. Tick marks — 10px spacing, inside the white strip
        tick_len = max(2, min(wp - 1, 6))
        p.setPen(QPen(QColor(self._colors["gauge_tick"]), 1))
        ty = y
        while ty <= y + hh + 0.5:
            p.drawLine(QPointF(x + 1, ty), QPointF(x + 1 + tick_len, ty))
            p.drawLine(QPointF(x + tube_w - 1 - tick_len, ty), QPointF(x + tube_w - 1, ty))
            ty += self.TICK_SPACING

        # 5. Top / bottom numeric labels (left of the tube, right-aligned)
        small = self._fonts["small"]
        p.setFont(small)
        p.setPen(QColor(T["text"]))
        fm = QFontMetrics(small)
        lh = fm.height()
        p.drawText(QRectF(0, y - lh / 2, x - 4, lh),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   self._top_text)
        p.drawText(QRectF(0, y + hh - lh / 2, x - 4, lh),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   self._bottom_text)

        # 6. Primary pointer — thin line spanning the full tube
        if self._pointer_frac is not None:
            py = y + self._pointer_frac * hh
            p.setPen(QPen(QColor(self._colors["pointer"]), 1))
            p.drawLine(QPointF(x - 3, py), QPointF(x + tube_w + 3, py))

        # 7. Secondary pointer — small red triangle on the right
        if self._pointer2_frac is not None:
            py2 = y + self._pointer2_frac * hh
            tri_x = x + tube_w + 3
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(self._colors["pointer2"]))
            p.drawPolygon(QPolygonF([
                QPointF(tri_x, py2),
                QPointF(tri_x + 7, py2 - 4),
                QPointF(tri_x + 7, py2 + 4),
            ]))
        p.end()


# ══════════════════════════════════════════════════════════════════════════
#  SetpointsDialog
# ══════════════════════════════════════════════════════════════════════════

_DEFAULT_COLORS = {
    "gauge_yellow": T["gauge_yellow"],
    "gauge_green":  T["gauge_green"],
    "gauge_red":    T["gauge_red"],
    "gauge_tick":   T["gauge_tick"],
    "pointer":      T["pointer"],
    "pointer2":     T["pointer2"],
}


class SetpointsDialog:
    """Setpoints - Radial Vibration configuration dialog for a DIS_MODULE channel."""

    def __init__(self, parent, fonts, slot_num):
        self._parent = parent
        self._fonts = fonts
        self._slot_num = slot_num
        self._dialog = None
        self._validating = False        # re-entrancy guard (message box steals focus)

        # ---- monitor selection ----
        self.monitor_selection = "3000/12M/DIS"

        # ---- live values (defaults match the reference screenshot) ----
        self.direct1_value = 3
        self.direct1_top, self.direct1_bottom = 10, 0

        self.gap_value = -15.6
        self.gap_top, self.gap_bottom = -24, 0
        self.gap_secondary = -8.4

        self.direct2_value = 6
        self.direct2_top, self.direct2_bottom = 10, 0

        # ---- gauge widget references ----
        self._gauge_direct1 = None
        self._gauge_direct2 = None
        self._gauge_gap = None

        # ---- configurable colors ----
        self.colors = dict(_DEFAULT_COLORS)

    # ──────────────────────────────────────────────────────────────────
    def show(self):
        d = QDialog(self._parent)
        self._dialog = d
        d.setWindowTitle(f"Setpoints -Radial Vibration (Slot {self._slot_num})")
        d.setMinimumSize(820, 560)
        d.resize(880, 620)
        d.setObjectName("spDialog")
        d.setStyleSheet(f"QDialog#spDialog {{ background:{T['win_bg']}; }}")
        d.setModal(True)

        self._f_norm  = _font(9)
        self._f_bold  = _font(9, bold=True)
        self._f_small = _font(8)
        self._f_head  = _font(8, bold=True)
        self._f_vms   = _font(13, bold=True, italic=True)

        self._fonts_map = {
            "norm": self._f_norm,
            "bold": self._f_bold,
            "small": self._f_small,
            "head": self._f_head,
        }

        self._build_ui()
        center_on_parent(d, self._parent)
        d.exec()

    # ──────────────────────────────────────────────────────────────────
    def _label(self, text, font=None, align=Qt.AlignmentFlag.AlignCenter):
        lbl = QLabel(text)
        lbl.setFont(font or self._f_norm)
        lbl.setAlignment(align)
        lbl.setStyleSheet(f"color:{T['text']}; background:transparent;")
        return lbl

    def _enabled_check(self):
        c = QCheckBox("Enabled")
        c.setFont(self._f_small)
        c.setChecked(True)
        c.setStyleSheet(checkbox_qss(T['text']))
        return c

    def _build_ui(self):
        d = self._dialog
        main = QVBoxLayout(d)
        main.setContentsMargins(12, 12, 12, 12)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)
        main.addLayout(top_row, 1)

        # ═══════════════════════ Alert / Alarm 1 card ═══════════════════
        card1, c1 = make_card("Alert / Alarm 1", self._f_head)
        top_row.addWidget(card1, 1)
        cols1 = QHBoxLayout()
        cols1.setSpacing(30)
        c1.addLayout(cols1, 1)

        # --- Direct mil pp (Alert/Alarm 1) ---
        col_direct1 = QVBoxLayout()
        cols1.addLayout(col_direct1, 1)
        col_direct1.addWidget(self._label("Direct\nmil pp", self._f_bold))

        self._entry_direct1 = self._value_box(self.direct1_value)
        col_direct1.addWidget(self._entry_direct1, 0, Qt.AlignmentFlag.AlignHCenter)
        self._entry_direct1.textEdited.connect(lambda _t: self._on_direct1_realtime())
        self._entry_direct1.editingFinished.connect(self._on_direct1_validate)

        self._gauge_direct1 = VerticalGauge(self._fonts_map, self.colors)
        col_direct1.addWidget(self._gauge_direct1, 1)
        self._update_direct1_gauge()

        self._en_direct1 = self._enabled_check()
        col_direct1.addWidget(self._en_direct1, 0, Qt.AlignmentFlag.AlignHCenter)

        # --- Gap Vdc (Alert/Alarm 1) ---
        col_gap = QVBoxLayout()
        cols1.addLayout(col_gap, 1)
        col_gap.addWidget(self._label("Gap\nVdc", self._f_bold))

        self._entry_gap = self._value_box(self.gap_value)
        col_gap.addWidget(self._entry_gap, 0, Qt.AlignmentFlag.AlignHCenter)
        self._entry_gap.textEdited.connect(lambda _t: self._on_gap_realtime())
        self._entry_gap.editingFinished.connect(self._on_gap_validate)

        self._gauge_gap = VerticalGauge(self._fonts_map, self.colors)
        col_gap.addWidget(self._gauge_gap, 1)
        self._update_gap_gauge()

        self._gap_secondary_box = self._value_box(self.gap_secondary)
        col_gap.addWidget(self._gap_secondary_box, 0, Qt.AlignmentFlag.AlignHCenter)
        self._gap_secondary_box.textEdited.connect(lambda _t: self._on_gap_secondary_realtime())
        self._gap_secondary_box.editingFinished.connect(self._on_gap_secondary_validate)

        self._en_gap = self._enabled_check()
        col_gap.addWidget(self._en_gap, 0, Qt.AlignmentFlag.AlignHCenter)

        # ═══════════════════════ Danger / Alarm 2 card ═══════════════════
        card2, c2 = make_card("Danger / Alarm 2", self._f_head)
        top_row.addWidget(card2, 1)

        mode_row = QHBoxLayout()
        mode1 = self._combo(["Direct", "Gap", "1X Amp", "2X Amp"], "Direct")
        mode2 = self._combo(["None", "Direct", "Gap"], "None")
        mode_row.addWidget(mode1)
        mode_row.addSpacing(10)
        mode_row.addWidget(mode2)
        mode_row.addStretch(1)
        c2.addLayout(mode_row)
        c2.addSpacing(12)

        col_direct2 = QVBoxLayout()
        c2.addLayout(col_direct2, 1)
        col_direct2.addWidget(self._label("Direct mil\npp", self._f_bold))

        self._entry_direct2 = self._value_box(self.direct2_value)
        col_direct2.addWidget(self._entry_direct2, 0, Qt.AlignmentFlag.AlignHCenter)
        self._entry_direct2.textEdited.connect(lambda _t: self._on_direct2_realtime())
        self._entry_direct2.editingFinished.connect(self._on_direct2_validate)

        self._gauge_direct2 = VerticalGauge(self._fonts_map, self.colors)
        col_direct2.addWidget(self._gauge_direct2, 1)
        self._update_direct2_gauge()

        self._en_direct2 = self._enabled_check()
        col_direct2.addWidget(self._en_direct2, 0, Qt.AlignmentFlag.AlignHCenter)

        # ═══════════════════════ Bottom bar ═══════════════════════
        main.addSpacing(12)
        main.addWidget(hline(T["group_border"], 1))
        main.addSpacing(10)

        bottom = QHBoxLayout()
        main.addLayout(bottom)

        chan_combo = self._combo(["channel 1", "channel 2", "channel 3", "channel 4"], "channel 1")
        bottom.addWidget(chan_combo)
        bottom.addSpacing(12)

        monitor_combo = self._combo(["3000/12M/DIS", "3000/12M/DIS-A", "3000/12M/DIS-B"],
                                    self.monitor_selection)
        monitor_combo.currentTextChanged.connect(self._on_monitor_change)
        bottom.addWidget(monitor_combo)
        bottom.addSpacing(16)

        vms_badge = QLabel("VMS 3000")
        vms_badge.setFont(self._f_vms)
        vms_badge.setStyleSheet(f"color:{T['vms_blue']}; background:transparent;")
        bottom.addWidget(vms_badge)
        bottom.addStretch(1)

        for text, cb, kind, enabled in (
            ("Colors",   self._on_color_config,  "outline", True),
            ("Cancel",   self._on_cancel,        "outline", True),
            ("Defaults", self._on_set_defaults,  "outline", False),
            ("Copy",     self._on_copy,          "outline", True),
            ("Ok",       self._on_ok,            "primary", True),
        ):
            bottom.addWidget(make_pill_button(text, cb, self._f_norm, kind, enabled))
            bottom.addSpacing(6)

    # ──────────────────────────────────────────────────────────────────
    #  Helpers
    # ──────────────────────────────────────────────────────────────────
    def _combo(self, values, current):
        cb = QComboBox()
        cb.setFont(self._f_small)
        cb.addItems(values)
        cb.setCurrentText(current)
        cb.setStyleSheet("QComboBox { background:#ffffff; color:#1a2533; padding:3px 6px; }")
        return cb

    def _value_box(self, value):
        e = QLineEdit(str(value))
        e.setAlignment(Qt.AlignmentFlag.AlignCenter)
        e.setFont(self._f_norm)
        e.setFixedWidth(QFontMetrics(self._f_norm).horizontalAdvance("0") * 6 + 16)
        e.setStyleSheet(
            f"QLineEdit {{ background:{T['entry_bg']}; color:{T['text']};"
            " border:2px inset #8a8f98; padding:1px; }"
        )
        return e

    @staticmethod
    def _frac(value, top, bottom):
        """Fraction of the gauge height from the TOP for a given value."""
        span = bottom - top
        if span == 0:
            return 0.0
        f = (value - top) / span
        return max(0.0, min(1.0, f))

    def _refresh_gauge(self, updater):
        if self.monitor_selection == "3000/12M/DIS":
            updater()
        else:
            self._reset_gauge_display()

    # ──────────────────────────────────────────────────────────────────
    #  Button handlers
    # ──────────────────────────────────────────────────────────────────
    def _on_ok(self):
        print(f"Ok - setpoints applied for slot {self._slot_num}")
        self._dialog.accept()

    def _on_copy(self):
        print(f"Copy setpoints for slot {self._slot_num}")

    def _on_cancel(self):
        self._dialog.reject()

    def _on_set_defaults(self):
        print(f"Set defaults for slot {self._slot_num}")

    def _on_monitor_change(self, text):
        self.monitor_selection = text
        if self.monitor_selection == "3000/12M/DIS":
            self._update_direct1_gauge()
            self._update_direct2_gauge()
            self._update_gap_gauge()
        else:
            self._reset_gauge_display()

    # --- generic helpers for the "realtime" (while typing) and "validate"
    #     (on Enter / focus-out) handlers -----------------------------------
    def _realtime(self, edit, attr, updater):
        try:
            value_str = edit.text()
            if value_str:
                value = float(value_str)
                setattr(self, attr, value)
                self._refresh_gauge(updater)
        except ValueError:
            pass

    def _reset_entry(self, edit, attr, default, updater):
        setattr(self, attr, default)
        edit.setText(str(default))
        self._refresh_gauge(updater)

    def _validate(self, edit, attr, default, updater, rules):
        """
        rules: list of (predicate(value) -> bool, message).  The first rule that
        matches pops the alert and resets the field to *default*.
        """
        if self._validating:
            return
        self._validating = True
        try:
            try:
                value = float(edit.text())
            except ValueError:
                self._reset_entry(edit, attr, default, updater)
                return
            for pred, message in rules:
                if pred(value):
                    self._show_alert_message(message)
                    self._reset_entry(edit, attr, default, updater)
                    return
            setattr(self, attr, value)
            self._refresh_gauge(updater)
        finally:
            self._validating = False

    def _on_direct1_realtime(self):
        self._realtime(self._entry_direct1, "direct1_value", self._update_direct1_gauge)

    def _on_direct1_validate(self):
        self._validate(self._entry_direct1, "direct1_value", 3, self._update_direct1_gauge, [
            (lambda v: v >= 10, "value cannot be '10' mil"),
            (lambda v: v >= self.direct2_value, "Alert value must be less than Danger value"),
        ])

    def _on_direct2_realtime(self):
        self._realtime(self._entry_direct2, "direct2_value", self._update_direct2_gauge)

    def _on_direct2_validate(self):
        self._validate(self._entry_direct2, "direct2_value", 6, self._update_direct2_gauge, [
            (lambda v: v >= 10, "value cannot be '10' mil"),
            (lambda v: v <= self.direct1_value, "Danger value must be greater than Alert value"),
        ])

    def _on_gap_realtime(self):
        self._realtime(self._entry_gap, "gap_value", self._update_gap_gauge)

    def _on_gap_validate(self):
        self._validate(self._entry_gap, "gap_value", -15.6, self._update_gap_gauge, [
            (lambda v: v > 0 or v < -24, "value must be between -24 and 0 Vdc"),
        ])

    def _on_gap_secondary_realtime(self):
        self._realtime(self._gap_secondary_box, "gap_secondary", self._update_gap_gauge)

    def _on_gap_secondary_validate(self):
        self._validate(self._gap_secondary_box, "gap_secondary", -8.4, self._update_gap_gauge, [
            (lambda v: v > 0 or v < -24, "value must be between -24 and 0 Vdc"),
        ])

    def _show_alert_message(self, message="value cannot be '10' mil"):
        show_warning(self._dialog, "Alert", message)

    # ──────────────────────────────────────────────────────────────────
    #  Gauge update helpers
    # ──────────────────────────────────────────────────────────────────
    def _update_direct1_gauge(self):
        if self._gauge_direct1:
            if self.direct1_value <= 5:
                color = self.colors["gauge_green"]
            elif self.direct1_value <= 8:
                color = self.colors["gauge_yellow"]
            else:
                color = self.colors["gauge_red"]

            self._gauge_direct1.configure_gauge(
                zones=[(0.00, 1.00, color)],
                top_text=str(self.direct1_top),
                bottom_text=str(self.direct1_bottom),
                pointer_frac=self._frac(self.direct1_value, self.direct1_top, self.direct1_bottom),
            )

    def _update_direct2_gauge(self):
        if self._gauge_direct2:
            if self.direct2_value <= 5:
                color = self.colors["gauge_green"]
            elif self.direct2_value <= 8:
                color = self.colors["gauge_yellow"]
            else:
                color = self.colors["gauge_red"]

            self._gauge_direct2.configure_gauge(
                zones=[(0.00, 1.00, color)],
                top_text=str(self.direct2_top),
                bottom_text=str(self.direct2_bottom),
                pointer_frac=self._frac(self.direct2_value, self.direct2_top, self.direct2_bottom),
            )

    def _update_gap_gauge(self):
        if self._gauge_gap:
            if self.gap_value >= -15:
                color = self.colors["gauge_green"]
            elif self.gap_value >= -20:
                color = self.colors["gauge_yellow"]
            else:
                color = self.colors["gauge_red"]

            self._gauge_gap.configure_gauge(
                zones=[(0.00, 1.00, color)],
                top_text=str(self.gap_top),
                bottom_text=str(self.gap_bottom),
                pointer_frac=self._frac(self.gap_value, self.gap_top, self.gap_bottom),
                pointer2_frac=self._frac(self.gap_secondary, self.gap_top, self.gap_bottom),
            )

    def _reset_gauge_display(self):
        if self._gauge_direct1:
            self._gauge_direct1.configure_gauge(
                zones=[(0.00, 0.85, self.colors["gauge_yellow"]),
                       (0.85, 1.00, self.colors["gauge_green"])],
                top_text=str(self.direct1_top),
                bottom_text=str(self.direct1_bottom),
                pointer_frac=self._frac(self.direct1_value, self.direct1_top, self.direct1_bottom),
            )

        if self._gauge_direct2:
            self._gauge_direct2.configure_gauge(
                zones=[(0.00, 0.20, self.colors["gauge_red"]),
                       (0.20, 1.00, self.colors["gauge_green"])],
                top_text=str(self.direct2_top),
                bottom_text=str(self.direct2_bottom),
                pointer_frac=self._frac(self.direct2_value, self.direct2_top, self.direct2_bottom),
            )

        if self._gauge_gap:
            self._gauge_gap.configure_gauge(
                zones=[(0.00, 0.12, self.colors["gauge_yellow"]),
                       (0.12, 0.62, self.colors["gauge_green"]),
                       (0.62, 1.00, self.colors["gauge_yellow"])],
                top_text=str(self.gap_top),
                bottom_text=str(self.gap_bottom),
                pointer_frac=self._frac(self.gap_value, self.gap_top, self.gap_bottom),
                pointer2_frac=self._frac(self.gap_secondary, self.gap_top, self.gap_bottom),
            )

    def _apply_colors(self):
        """Push the (possibly edited) colour table into the gauges and redraw."""
        for g in (self._gauge_direct1, self._gauge_direct2, self._gauge_gap):
            if g is not None:
                g.set_colors(self.colors)
        self._refresh_gauge(lambda: None)
        if self.monitor_selection == "3000/12M/DIS":
            self._update_direct1_gauge()
            self._update_direct2_gauge()
            self._update_gap_gauge()

    # ──────────────────────────────────────────────────────────────────
    def _on_color_config(self):
        dlg = QDialog(self._dialog)
        dlg.setWindowTitle("Color Configuration")
        dlg.setModal(True)
        dlg.setObjectName("colorDlg")
        dlg.setStyleSheet(f"QDialog#colorDlg {{ background:{T['win_bg']}; }}")
        dlg.setFixedSize(450, 400)

        root = QVBoxLayout(dlg)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        titlebar = QLabel("  Color Configuration")
        titlebar.setFont(self._f_bold)
        titlebar.setFixedHeight(32)
        titlebar.setStyleSheet(f"background:{T['titlebar']}; color:{T['card_header_fg']};")
        root.addWidget(titlebar)

        wrap = QVBoxLayout()
        wrap.setContentsMargins(12, 12, 12, 12)
        root.addLayout(wrap, 1)

        card, cl = make_card("GAUGE COLORS", self._f_head)
        wrap.addWidget(card, 1)

        color_edits = {}
        color_labels = {
            "gauge_yellow": "Gauge Yellow",
            "gauge_green": "Gauge Green",
            "gauge_red": "Gauge Red",
            "gauge_tick": "Gauge Tick",
            "pointer": "Pointer",
            "pointer2": "Secondary Pointer",
        }

        for key, label in color_labels.items():
            row = QHBoxLayout()
            lbl = self._label(label, self._f_norm, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            lbl.setFixedWidth(QFontMetrics(self._f_norm).horizontalAdvance("0") * 18)
            row.addWidget(lbl)

            edit = QLineEdit(self.colors[key])
            edit.setFont(self._f_norm)
            edit.setFixedWidth(QFontMetrics(self._f_norm).horizontalAdvance("0") * 10 + 16)
            edit.setStyleSheet("QLineEdit { background:#ffffff; border:2px inset #b4bfcc; padding:1px; }")
            row.addWidget(edit)

            preview = QFrame()
            preview.setFixedSize(35, 22)
            preview.setStyleSheet(f"background:{self.colors[key]}; border:1px solid #000;")
            row.addWidget(preview)
            row.addStretch(1)
            cl.addLayout(row)

            def on_change(text, pv=preview):
                if QColor(text).isValid():
                    pv.setStyleSheet(f"background:{text}; border:1px solid #000;")
            edit.textChanged.connect(on_change)
            color_edits[key] = edit

        cl.addStretch(1)

        def apply_colors():
            for key, edit in color_edits.items():
                text = edit.text().strip()
                # ignore invalid colour strings instead of breaking the gauge
                if QColor(text).isValid():
                    self.colors[key] = text
            self._apply_colors()
            dlg.accept()

        def reset_colors():
            self.colors.clear()
            self.colors.update(_DEFAULT_COLORS)
            dlg.accept()
            self._apply_colors()

        btns = QHBoxLayout()
        btns.setContentsMargins(12, 0, 12, 12)
        btns.addStretch(1)
        btns.addWidget(make_pill_button("Cancel", dlg.reject, self._f_norm, "outline"))
        btns.addWidget(make_pill_button("Reset", reset_colors, self._f_norm, "outline"))
        btns.addWidget(make_pill_button("Apply", apply_colors, self._f_norm, "primary"))
        root.addLayout(btns)

        center_on_parent(dlg, self._dialog)
        dlg.exec()


# ══════════════════════════════════════════════════════════════════════════
#  Standalone demo
# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication, QPushButton

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    host = QPushButton("Open Setpoints - Radial Vibration...")
    host.resize(300, 120)
    host.clicked.connect(lambda: SetpointsDialog(host, {}, slot_num=4).show())
    host.show()
    sys.exit(app.exec())
