"""
setpoins.py — VMS 3000  •  Setpoints Configuration Dialog
"Setpoints - Radial Vibration (Slot N)"

Compact "card" UI with vertical meter-style gauges:
  - All gauges have an IDENTICAL fixed size and sit on the same baseline
  - White track with a white padding strip on the left & right inside the tube
  - Tick marks on BOTH inner edges, sitting inside the white strip
  - Thin black pointer line spanning the full tube width
  - Red triangular secondary pointer on the right side
  - Colour zone fills only the middle of the tube

    from points.setpoins import SetpointsDialog
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QWidget,
)

from qt_common import center_on_parent, checkbox_qss, hline, show_warning

# Import to access channel configurations
from points.channel_configuration import ChannelConfigurationDialog


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

# ---- Shared layout metrics: every column uses these so gauges line up ----
# GAUGE_H - 2*PAD_V should be a multiple of TICK_SPACING (176 - 16 = 160)
GAUGE_W      = 100     # widget width of every gauge
GAUGE_H      = 176     # widget height of every gauge
LABEL_H      = 32      # fixed height of the 2-line title above each entry
ENTRY_H      = 22      # fixed height of every value box (and its placeholder)
COMBO_H      = 24      # fixed height of the mode combos / matching spacer
COL_SPACING  = 4       # vertical spacing between widgets in a column

# ---- Dialog size ----
DIALOG_MIN_W, DIALOG_MIN_H = 680, 470
DIALOG_W, DIALOG_H         = 700, 480


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
        f"background:{T['card_header']}; color:{T['card_header_fg']}; padding:5px 10px;"
    )
    cl.addWidget(header)

    body = QWidget()
    body.setStyleSheet(f"background:{T['card_bg']};")
    bl = QVBoxLayout(body)
    bl.setContentsMargins(8, 8, 8, 8)
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
        QPushButton {{ background:{bg}; color:{fg}; border:1px solid {border}; padding:4px 8px; }}
        QPushButton:hover {{ background:{hov}; }}
        QPushButton:disabled {{ background:#eef1f6; color:#9aa0aa; border:1px solid #c7cfda; }}
    """)
    b.setEnabled(enabled)
    b.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
    if command is not None:
        b.clicked.connect(lambda _c=False, cb=command: cb())
    return b


# ══════════════════════════════════════════════════════════════════════════
#  VerticalGauge — fixed-size vertical meter with white padding strip
# ══════════════════════════════════════════════════════════════════════════

class VerticalGauge(QWidget):
    """
    Vertical meter gauge — FIXED size so every gauge is identical.

      ┌──────────────────────────┐   ← black outer border
      │ ──  (white strip)    ──  │   ← ticks live here
      │ ── ┌──────────────┐  ── │
      │ ── │   colour     │  ── │   ← colour fills the middle
      │ ── └──────────────┘  ── │
      └──────────────────────────┘

    The tube is centred horizontally inside the widget (equal left/right
    margins). Left margin holds the top/bottom numbers, right margin holds
    the red triangle pointer.
    """

    TICK_SPACING = 10     # px between ticks
    WHITE_PAD    = 14     # width of the white padding strip inside the tube (px)
    TUBE_W       = 48     # width of the meter body (px)
    PAD_V        = 8      # vertical padding top/bottom (room for number labels)

    def __init__(self, fonts, colors, width=GAUGE_W, height=GAUGE_H, parent=None):
        super().__init__(parent)
        self._fonts = fonts
        self._colors = colors

        # Data
        self._zones = []
        self._top_text = ""
        self._bottom_text = ""
        self._pointer_frac = None
        self._pointer2_frac = None

        self.setFixedSize(width, height)

    def sizeHint(self):
        return QSize(self.width(), self.height())

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

        # ---- Geometry (all integers so lines stay crisp) ----
        tube_w = self.TUBE_W
        x = (w - tube_w) // 2                       # equal margins left & right
        y = self.PAD_V
        # tube height snapped to a multiple of the tick spacing so the first
        # and last ticks land exactly on the top / bottom border
        avail_h = h - 2 * self.PAD_V
        hh = (avail_h // self.TICK_SPACING) * self.TICK_SPACING

        black = QColor(T["gauge_border"])
        wp = self.WHITE_PAD

        # 1. White base + black outer border
        p.setPen(QPen(black, 1))
        p.setBrush(QColor(T["gauge_bg"]))
        p.drawRect(QRectF(x + 0.5, y + 0.5, tube_w, hh))

        # 2. Colour zones — inset by WHITE_PAD on left & right
        p.setPen(Qt.PenStyle.NoPen)
        for f0, f1, color in self._zones:
            y0 = y + 1 + f0 * (hh - 1)
            y1 = y + 1 + f1 * (hh - 1)
            p.setBrush(QColor(color))
            p.drawRect(QRectF(x + 1 + wp, y0, tube_w - 1 - 2 * wp, y1 - y0))

        # 3. Border redrawn on top (crisp edges)
        p.setPen(QPen(black, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(x + 0.5, y + 0.5, tube_w, hh))

        # 4. Tick marks — both sides, inside the white strip
        tick_len = max(2, min(wp - 2, 8))
        p.setPen(QPen(QColor(self._colors["gauge_tick"]), 1))
        n_ticks = hh // self.TICK_SPACING
        for i in range(n_ticks + 1):
            ty = y + i * self.TICK_SPACING + 0.5
            p.drawLine(QPointF(x + 1, ty), QPointF(x + 1 + tick_len, ty))
            p.drawLine(QPointF(x + tube_w - tick_len, ty), QPointF(x + tube_w, ty))

        # 5. Top / bottom numeric labels (left of the tube, right-aligned)
        small = self._fonts["small"]
        p.setFont(small)
        p.setPen(QColor(T["text"]))
        lh = QFontMetrics(small).height()
        p.drawText(QRectF(0, y - lh / 2, x - 4, lh),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   self._top_text)
        p.drawText(QRectF(0, y + hh - lh / 2, x - 4, lh),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   self._bottom_text)

        # 6. Primary pointer — thin line spanning the full tube
        if self._pointer_frac is not None:
            py = y + round(self._pointer_frac * hh) + 0.5
            p.setPen(QPen(QColor(self._colors["pointer"]), 1))
            p.drawLine(QPointF(x - 3, py), QPointF(x + tube_w + 4, py))

        # 7. Secondary pointer — small red triangle on the right
        if self._pointer2_frac is not None:
            py2 = y + round(self._pointer2_frac * hh) + 0.5
            tri_x = x + tube_w + 4
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(self._colors["pointer2"]))
            p.drawPolygon(QPolygonF([
                QPointF(tri_x, py2),
                QPointF(tri_x + 8, py2 - 5),
                QPointF(tri_x + 8, py2 + 5),
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

    def __init__(self, parent, fonts, slot_num, channel_num=1):
        self._parent = parent
        self._fonts = fonts
        self._slot_num = slot_num
        self._channel_num = channel_num
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

        # Scale unit label (mil or µm)
        self._scale_unit = "mil"

        # colour thresholds (overridden by channel configuration)
        self._green_threshold = 5
        self._yellow_threshold = 8

        # ---- gauge widget references ----
        self._gauge_direct1 = None
        self._gauge_direct2 = None
        self._gauge_gap = None

        # ---- label references for dynamic updating ----
        self._label_direct1 = None
        self._label_direct2 = None

        # ---- configurable colors ----
        self.colors = dict(_DEFAULT_COLORS)

        # ---- Load configured values from channel configuration ----
        self._load_channel_configuration()

    def _load_channel_configuration(self):
        """Load configured direct scale and clamp values from channel configuration."""
        config = ChannelConfigurationDialog.get_channel_config(self._channel_num)
        if config:
            direct_scale = config.get("direct_scale", "0-10 mil pp")
            direct_clamp = config.get("direct_clamp", 0)

            # Parse the scale to determine the range (keep original units)
            if "0-10" in direct_scale and "mil" in direct_scale:
                self.direct1_top = 10
                self.direct1_bottom = 0
                self._scale_unit = "mil"
            elif "0-15" in direct_scale:
                self.direct1_top = 15
                self.direct1_bottom = 0
                self._scale_unit = "mil"
            elif "0-20" in direct_scale:
                self.direct1_top = 20
                self.direct1_bottom = 0
                self._scale_unit = "mil"
            elif "0-100" in direct_scale and "mil" in direct_scale:
                self.direct1_top = 100
                self.direct1_bottom = 0
                self._scale_unit = "mil"
            elif "0-100" in direct_scale and "µm" in direct_scale:
                self.direct1_top = 100
                self.direct1_bottom = 0
                self._scale_unit = "µm"
            elif "150" in direct_scale and "µm" in direct_scale:
                self.direct1_top = 150
                self.direct1_bottom = 0
                self._scale_unit = "µm"
            elif "200" in direct_scale and "µm" in direct_scale:
                self.direct1_top = 200
                self.direct1_bottom = 0
                self._scale_unit = "µm"
            elif "400" in direct_scale and "µm" in direct_scale:
                self.direct1_top = 400
                self.direct1_bottom = 0
                self._scale_unit = "µm"
            elif "500" in direct_scale and "µm" in direct_scale:
                self.direct1_top = 500
                self.direct1_bottom = 0
                self._scale_unit = "µm"

            # Danger gauge always shares the same scale as Alert gauge
            self.direct2_top = self.direct1_top
            self.direct2_bottom = 0

            # Apply clamp value if it's set
            if direct_clamp > 0:
                self.direct1_value = min(direct_clamp, self.direct1_top)
                self.direct2_value = min(direct_clamp * 2, self.direct1_top)

            self._update_gauge_colors_from_config(direct_scale)

    def _update_gauge_colors_from_config(self, direct_scale):
        """Update gauge color thresholds based on the configured direct scale."""
        self._green_threshold = 5
        self._yellow_threshold = 8

        if "0-15" in direct_scale:
            self._green_threshold = 7.5
            self._yellow_threshold = 12
        elif "0-20" in direct_scale:
            self._green_threshold = 10
            self._yellow_threshold = 16
        elif "0-100" in direct_scale:
            self._green_threshold = 50
            self._yellow_threshold = 80
        elif "150" in direct_scale and "µm" in direct_scale:
            self._green_threshold = 75
            self._yellow_threshold = 120
        elif "200" in direct_scale and "µm" in direct_scale:
            self._green_threshold = 100
            self._yellow_threshold = 160
        elif "400" in direct_scale and "µm" in direct_scale:
            self._green_threshold = 200
            self._yellow_threshold = 320
        elif "500" in direct_scale and "µm" in direct_scale:
            self._green_threshold = 250
            self._yellow_threshold = 400

    # ──────────────────────────────────────────────────────────────────
    def _direct_label_text(self):
        unit = "mil pp" if self._scale_unit == "mil" else "µm pp"
        return f"Direct\n{unit}"

    # ──────────────────────────────────────────────────────────────────
    def show(self):
        d = QDialog(self._parent)
        self._dialog = d
        d.setWindowTitle(f"Setpoints -Radial Vibration (Slot {self._slot_num})")
        d.setMinimumSize(DIALOG_MIN_W, DIALOG_MIN_H)
        d.resize(DIALOG_W, DIALOG_H)
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
        # Update labels with correct units after building UI
        unit_text = "mil pp" if self._scale_unit == "mil" else "µm pp"
        if self._label_direct1:
            self._label_direct1.setText(f"Direct\n{unit_text}")
        if self._label_direct2:
            self._label_direct2.setText(f"Direct {unit_text}")
        # Update entry boxes with loaded values
        self._entry_direct1.setText(str(self.direct1_value))
        self._entry_direct2.setText(str(self.direct2_value))
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

    def _placeholder(self, height):
        """Invisible widget used to keep every column the same height."""
        w = QWidget()
        w.setFixedHeight(height)
        w.setStyleSheet("background:transparent;")
        return w

    def _build_column(self, title_widget, entry, gauge, secondary, enabled_chk):
        """
        One gauge column. EVERY column has the same 5 slots, in the same order,
        with the same fixed heights, so gauges line up perfectly:

            title (LABEL_H) / entry (ENTRY_H) / gauge (GAUGE_H)
            / secondary slot (ENTRY_H) / enabled checkbox
        """
        col = QVBoxLayout()
        col.setSpacing(COL_SPACING)
        center = Qt.AlignmentFlag.AlignHCenter

        title_widget.setFixedHeight(LABEL_H)
        col.addWidget(title_widget, 0, center)
        col.addWidget(entry, 0, center)
        col.addWidget(gauge, 0, center)
        col.addWidget(secondary if secondary is not None
                      else self._placeholder(ENTRY_H), 0, center)
        col.addWidget(enabled_chk, 0, center)
        col.addStretch(1)
        return col

    def _build_ui(self):
        d = self._dialog
        main = QVBoxLayout(d)
        main.setContentsMargins(10, 10, 10, 10)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        main.addLayout(top_row, 1)

        # ═══════════════════════ Alert / Alarm 1 card ═══════════════════
        card1, c1 = make_card("Alert / Alarm 1", self._f_head)
        top_row.addWidget(card1, 1)

        # spacer same height as the combo row of the Danger card
        c1.addWidget(self._placeholder(COMBO_H))
        c1.addSpacing(8)

        cols1 = QHBoxLayout()
        cols1.setSpacing(16)
        c1.addLayout(cols1, 1)

        # --- Direct (Alert/Alarm 1) ---
        self._label_direct1 = self._label(self._direct_label_text(), self._f_bold)
        self._entry_direct1 = self._value_box(self.direct1_value)
        self._entry_direct1.textEdited.connect(lambda _t: self._on_direct1_realtime())
        self._entry_direct1.editingFinished.connect(self._on_direct1_validate)
        self._gauge_direct1 = VerticalGauge(self._fonts_map, self.colors)
        self._en_direct1 = self._enabled_check()
        cols1.addLayout(self._build_column(
            self._label_direct1, self._entry_direct1, self._gauge_direct1,
            None, self._en_direct1), 1)
        self._update_direct1_gauge()

        # --- Gap Vdc (Alert/Alarm 1) ---
        self._entry_gap = self._value_box(self.gap_value)
        self._entry_gap.textEdited.connect(lambda _t: self._on_gap_realtime())
        self._entry_gap.editingFinished.connect(self._on_gap_validate)
        self._gauge_gap = VerticalGauge(self._fonts_map, self.colors)
        self._gap_secondary_box = self._value_box(self.gap_secondary)
        self._gap_secondary_box.textEdited.connect(lambda _t: self._on_gap_secondary_realtime())
        self._gap_secondary_box.editingFinished.connect(self._on_gap_secondary_validate)
        self._en_gap = self._enabled_check()
        cols1.addLayout(self._build_column(
            self._label("Gap\nVdc", self._f_bold), self._entry_gap, self._gauge_gap,
            self._gap_secondary_box, self._en_gap), 1)
        self._update_gap_gauge()

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
        c2.addSpacing(8)

        cols2 = QHBoxLayout()
        c2.addLayout(cols2, 1)

        self._label_direct2 = self._label(self._direct_label_text(), self._f_bold)
        self._entry_direct2 = self._value_box(self.direct2_value)
        self._entry_direct2.textEdited.connect(lambda _t: self._on_direct2_realtime())
        self._entry_direct2.editingFinished.connect(self._on_direct2_validate)
        self._gauge_direct2 = VerticalGauge(self._fonts_map, self.colors)
        self._en_direct2 = self._enabled_check()
        cols2.addStretch(1)
        cols2.addLayout(self._build_column(
            self._label_direct2, self._entry_direct2, self._gauge_direct2,
            None, self._en_direct2))
        cols2.addStretch(1)
        self._update_direct2_gauge()

        # ═══════════════════════ Bottom bar ═══════════════════════
        main.addSpacing(8)
        main.addWidget(hline(T["group_border"], 1))
        main.addSpacing(6)

        bottom = QHBoxLayout()
        main.addLayout(bottom)

        chan_combo = self._combo(["channel 1", "channel 2", "channel 3", "channel 4"],
                                 f"channel {self._channel_num}")
        chan_combo.currentTextChanged.connect(self._on_channel_change)
        bottom.addWidget(chan_combo)
        bottom.addSpacing(8)

        monitor_combo = self._combo(["3000/12M/DIS", "3000/12M/DIS-A", "3000/12M/DIS-B"],
                                    self.monitor_selection)
        monitor_combo.currentTextChanged.connect(self._on_monitor_change)
        bottom.addWidget(monitor_combo)
        bottom.addSpacing(12)

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
            bottom.addSpacing(4)

    # ──────────────────────────────────────────────────────────────────
    #  Helpers
    # ──────────────────────────────────────────────────────────────────
    def _combo(self, values, current):
        cb = QComboBox()
        cb.setFont(self._f_small)
        cb.addItems(values)
        cb.setCurrentText(current)
        cb.setFixedHeight(COMBO_H)
        cb.setStyleSheet("QComboBox { background:#ffffff; color:#1a2533; padding:2px 6px; }")
        return cb

    def _value_box(self, value):
        e = QLineEdit(str(value))
        e.setAlignment(Qt.AlignmentFlag.AlignCenter)
        e.setFont(self._f_norm)
        e.setFixedSize(QFontMetrics(self._f_norm).horizontalAdvance("0") * 6 + 16, ENTRY_H)
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

    def _on_channel_change(self, text):
        """Handle channel selection change - reload configuration for the new channel."""
        if "channel" in text.lower():
            self._channel_num = int(text.split()[-1])
            self._load_channel_configuration()
            self._entry_direct1.setText(str(self.direct1_value))
            self._entry_direct2.setText(str(self.direct2_value))
            self._entry_gap.setText(str(self.gap_value))
            self._gap_secondary_box.setText(str(self.gap_secondary))
            if self._label_direct1:
                self._label_direct1.setText(self._direct_label_text())
            if self._label_direct2:
                self._label_direct2.setText(self._direct_label_text())
            self._update_direct1_gauge()
            self._update_direct2_gauge()
            self._update_gap_gauge()

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
            (lambda v: v >= self.direct1_top, f"value cannot be '{self.direct1_top}'"),
            (lambda v: v >= self.direct2_value, "Alert value must be less than Danger value"),
        ])

    def _on_direct2_realtime(self):
        self._realtime(self._entry_direct2, "direct2_value", self._update_direct2_gauge)

    def _on_direct2_validate(self):
        self._validate(self._entry_direct2, "direct2_value", 6, self._update_direct2_gauge, [
            (lambda v: v >= self.direct2_top, f"value cannot be '{self.direct2_top}'"),
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
    def _direct_color(self, value):
        if value <= self._green_threshold:
            return self.colors["gauge_green"]
        if value <= self._yellow_threshold:
            return self.colors["gauge_yellow"]
        return self.colors["gauge_red"]

    def _update_direct1_gauge(self):
        if self._gauge_direct1:
            self._gauge_direct1.configure_gauge(
                zones=[(0.00, 1.00, self._direct_color(self.direct1_value))],
                top_text=str(self.direct1_top),
                bottom_text=str(self.direct1_bottom),
                pointer_frac=self._frac(self.direct1_value, self.direct1_top, self.direct1_bottom),
            )

    def _update_direct2_gauge(self):
        if self._gauge_direct2:
            self._gauge_direct2.configure_gauge(
                zones=[(0.00, 1.00, self._direct_color(self.direct2_value))],
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
        if self.monitor_selection == "3000/12M/DIS":
            self._update_direct1_gauge()
            self._update_direct2_gauge()
            self._update_gap_gauge()
        else:
            self._reset_gauge_display()

    # ──────────────────────────────────────────────────────────────────
    def _on_color_config(self):
        dlg = QDialog(self._dialog)
        dlg.setWindowTitle("Color Configuration")
        dlg.setModal(True)
        dlg.setObjectName("colorDlg")
        dlg.setStyleSheet(f"QDialog#colorDlg {{ background:{T['win_bg']}; }}")
        dlg.setFixedSize(400, 360)

        root = QVBoxLayout(dlg)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        titlebar = QLabel("  Color Configuration")
        titlebar.setFont(self._f_bold)
        titlebar.setFixedHeight(28)
        titlebar.setStyleSheet(f"background:{T['titlebar']}; color:{T['card_header_fg']};")
        root.addWidget(titlebar)

        wrap = QVBoxLayout()
        wrap.setContentsMargins(10, 10, 10, 10)
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
            preview.setFixedSize(35, 20)
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
        btns.setContentsMargins(10, 0, 10, 10)
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
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    host = QPushButton("Open Setpoints - Radial Vibration...")
    host.resize(300, 120)
    host.clicked.connect(lambda: SetpointsDialog(host, {}, slot_num=4).show())
    host.show()
    sys.exit(app.exec())