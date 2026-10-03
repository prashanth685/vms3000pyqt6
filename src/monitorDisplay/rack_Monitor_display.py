"""
rack_Monitor_display.py — VMS 3000  •  PSM Front Panel Display
Design matching the reference image - Power Supply Module front panel
"""

import os
import sys

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QWidget


# ══════════════════════════════════════════════════════════════════════════════
#  THEME  —  VMS 3000 Industrial SCADA colour palette
# ══════════════════════════════════════════════════════════════════════════════

T = {
    # ── Panel colours ───────────────────────────────────────────────────
    "panel_bg":        "#1a3a5c",   # Dark blue panel background
    "panel_dark":      "#0a2040",   # Darker blue for shadows
    "panel_light":     "#2a5080",   # Lighter blue for highlights

    # ── Metal/brushed steel ─────────────────────────────────────────────
    "metal_dark":      "#3a4a5a",
    "metal_light":     "#5a6a7a",
    "metal_mid":       "#4a5a6a",

    # ── LEDs ──────────────────────────────────────────────────────────
    "led_green":       "#22c55e",
    "led_green_glow":  "#16a34a",
    "led_amber":       "#f59e0b",
    "led_red":         "#ef4444",
    "led_blue":        "#3b82f6",
    "led_off":         "#1a2a3a",

    # ── Text ──────────────────────────────────────────────────────────
    "text_white":      "#ffffff",
    "text_dim":        "#8a9ab8",
    "text_label":      "#c8d8e8",

    # ── Button ────────────────────────────────────────────────────────
    "btn_face":        "#4a5a6a",
    "btn_hover":       "#5a6a7a",
    "btn_press":       "#3a4a5a",

    # ── Switch ────────────────────────────────────────────────────────
    "switch_bg":       "#2a3a4a",
    "switch_knob":     "#5a6a7a",
}


def _c(hex_, alpha=None):
    col = QColor(hex_)
    if alpha is not None:
        col.setAlpha(alpha)
    return col


class _Canvas(QWidget):
    """Fixed-size widget with a few drawing helpers that mirror Canvas.create_*."""

    def __init__(self, width, height, bg, parent=None):
        super().__init__(parent)
        self._w, self._h = width, height
        self._bg = bg
        self.setFixedSize(width, height)

    def sizeHint(self):
        return QSize(self._w, self._h)

    # -- primitives ------------------------------------------------------
    @staticmethod
    def _pen(p, outline, width=1):
        if outline:
            p.setPen(QPen(_c(outline) if isinstance(outline, str) else outline, width))
        else:
            p.setPen(Qt.PenStyle.NoPen)

    def rect(self, p, x0, y0, x1, y1, fill=None, outline=None, width=1):
        self._pen(p, outline, width)
        p.setBrush(_c(fill) if fill else Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(x0, y0, x1 - x0, y1 - y0))

    def oval(self, p, x0, y0, x1, y1, fill=None, outline=None, width=1, alpha=None):
        self._pen(p, outline, width)
        p.setBrush(_c(fill, alpha) if fill else Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(x0, y0, x1 - x0, y1 - y0))

    def line(self, p, x0, y0, x1, y1, fill, width=1, alpha=None):
        p.setPen(QPen(_c(fill, alpha), width))
        p.drawLine(QPointF(x0, y0), QPointF(x1, y1))

    def text(self, p, x, y, txt, fill, size, bold=False, family="Arial", anchor="center"):
        f = QFont(family)
        f.setPointSize(size)
        f.setBold(bold)
        p.setFont(f)
        p.setPen(_c(fill))
        flags = {"center": Qt.AlignmentFlag.AlignCenter,
                 "w": Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter}[anchor]
        big = 400
        if anchor == "center":
            r = QRectF(x - big / 2, y - big / 2, big, big)
        else:
            r = QRectF(x, y - big / 2, big, big)
        p.drawText(r, flags, txt)

    def polygon(self, p, pts, fill, outline=None, width=1):
        self._pen(p, outline, width)
        p.setBrush(_c(fill))
        p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in pts]))


# ══════════════════════════════════════════════════════════════════════════════
#  PSM FRONT PANEL CLASS
# ══════════════════════════════════════════════════════════════════════════════

class PSMFrontPanel(_Canvas):
    """
    PSM (Power Supply Module) Front Panel Display.

      • Top screw/latch
      • LED indicators: PWR, TX/RX, TM, CNFG
      • RST button
      • RUN/PROG rotary switch
      • Configuration Port slot
      • Monitor icon with VMS-3000 CNFG label
      • Bottom screw
    """

    def __init__(self, parent=None, width=120, height=400):
        super().__init__(width, height, T["panel_bg"], parent)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self._w, self._h

        # ── Panel body with gradient effect ─────────────────────────────
        self._draw_panel_body(p, w, h)

        # ── Top screw/latch ────────────────────────────────────────────
        self._draw_screw(p, w // 2, 15)

        # ── LED indicators section ───────────────────────────────────────
        led_y = 50
        led_spacing = 25
        self._draw_led(p, w // 2, led_y, "PWR", T["led_green"])
        self._draw_led(p, w // 2, led_y + led_spacing, "TX/RX", T["led_amber"])
        self._draw_led(p, w // 2, led_y + led_spacing * 2, "TM", T["led_blue"])
        self._draw_led(p, w // 2, led_y + led_spacing * 3, "CNFG", T["led_off"])

        # ── RST button ──────────────────────────────────────────────────
        self._draw_rst_button(p, w // 2, led_y + led_spacing * 4 + 15)

        # ── RUN/PROG rotary switch ───────────────────────────────────────
        switch_y = led_y + led_spacing * 4 + 50
        self._draw_rotary_switch(p, w // 2, switch_y)

        # ── Configuration Port slot ─────────────────────────────────────
        port_y = switch_y + 60
        self._draw_config_port(p, w // 2, port_y)

        # ── Monitor icon and label ───────────────────────────────────────
        icon_y = port_y + 50
        self._draw_monitor_icon(p, w // 2, icon_y)

        # ── Bottom screw ────────────────────────────────────────────────
        self._draw_screw(p, w // 2, h - 15)
        p.end()

    def _draw_panel_body(self, p, w, h):
        """Draw the main panel body with brushed metal effect."""
        self.rect(p, 0, 0, w, h, fill=T["panel_bg"])
        self.rect(p, 0, 0, w, 3, fill=T["panel_light"])            # top highlight
        self.rect(p, 0, h - 3, w, h, fill=T["panel_dark"])         # bottom shadow
        for x in range(0, w, 4):                                   # brushed metal
            self.line(p, x, 0, x, h, T["panel_light"], 1, alpha=64)

    def _draw_screw(self, p, x, y):
        r = 6
        self.oval(p, x - r, y - r, x + r, y + r, fill=T["metal_dark"],
                  outline=T["metal_light"])
        self.line(p, x - 3, y, x + 3, y, T["metal_light"])
        self.line(p, x, y - 3, x, y + 3, T["metal_light"])

    def _draw_led(self, p, x, y, label, color):
        r = 8
        lit = color != T["led_off"]
        if lit:                                                    # glow
            self.oval(p, x - r - 2, y - r - 2, x + r + 2, y + r + 2, fill=color, alpha=128)
        self.oval(p, x - r, y - r, x + r, y + r, fill=color, outline=T["metal_light"])
        self.text(p, x + r + 15, y, label, T["text_label"], 7, bold=True, anchor="w")

    def _draw_rst_button(self, p, x, y):
        bw, bh = 40, 20
        self.rect(p, x - bw // 2, y - bh // 2, x + bw // 2, y + bh // 2,
                  fill=T["btn_face"], outline=T["metal_light"])
        self.text(p, x, y, "RST", T["text_white"], 8, bold=True)

    def _draw_rotary_switch(self, p, x, y):
        r = 25
        self.oval(p, x - r, y - r, x + r, y + r, fill=T["switch_bg"],
                  outline=T["metal_light"], width=2)
        knob_r = 18
        self.oval(p, x - knob_r, y - knob_r, x + knob_r, y + knob_r,
                  fill=T["switch_knob"], outline=T["metal_dark"])
        # Knob indicator line (pointing to RUN)
        self.line(p, x, y - knob_r + 5, x, y - knob_r + 12, T["text_white"], 2)
        self.text(p, x, y - r - 8, "RUN", T["led_green"], 8, bold=True)
        self.text(p, x, y + r + 8, "PROG", T["text_dim"], 8, bold=True)

    def _draw_config_port(self, p, x, y):
        sw, sh = 50, 30
        self.rect(p, x - sw // 2, y - sh // 2, x + sw // 2, y + sh // 2,
                  fill=T["panel_dark"], outline=T["metal_light"])
        self.rect(p, x - sw // 2 + 3, y - sh // 2 + 3, x + sw // 2 - 3, y + sh // 2 - 3,
                  fill="#0a1020")
        self.text(p, x, y + sh // 2 + 12, "CONFIGURATION", T["text_dim"], 6)
        self.text(p, x, y + sh // 2 + 20, "PORT", T["text_dim"], 6)

    def _draw_monitor_icon(self, p, x, y):
        iw = ih = 30
        ix, iy = x - iw // 2, y - ih // 2
        # Document rectangle + lines
        self.rect(p, ix + 5, iy + 5, ix + iw - 5, iy + ih - 5, fill="#ffffff",
                  outline=T["metal_light"])
        for i in range(3):
            ly = iy + 10 + i * 6
            self.line(p, ix + 10, ly, ix + iw - 10, ly, T["text_dim"])
        # Hand cursor (simplified)
        hx, hy = ix + iw - 8, iy + ih - 8
        self.polygon(p, [(hx, hy), (hx + 6, hy - 4), (hx + 8, hy - 2),
                         (hx + 8, hy + 4), (hx + 4, hy + 8), (hx, hy + 6)],
                     fill=T["led_amber"], outline=T["metal_light"])
        self.text(p, x, y + ih // 2 + 15, "VMS-3000", T["text_white"], 9, bold=True)
        self.text(p, x, y + ih // 2 + 25, "CNFG", T["text_dim"], 7)


# ══════════════════════════════════════════════════════════════════════════════
#  VMM-6M MODULE DISPLAY CLASS
# ══════════════════════════════════════════════════════════════════════════════

class VMM6MModule(_Canvas):
    """
    VMM-6M Module Display.

      • Top white tab with screw
      • Blue oval logo
      • LED indicators: PWR, Tx/Rx, OK
      • ALARM section: OK, ALT, DAN, BYP
      • 4 BNC connectors
      • VMM-6M label
      • Bottom white tab with screw
    """

    def __init__(self, parent=None, width=100, height=350):
        super().__init__(width, height, "#1a4fa0", parent)

    def _tab_screw(self, p, cx, cy):
        self.oval(p, cx - 4, cy - 4, cx + 4, cy + 4, fill="#a0a0a0", outline="#808080")
        self.line(p, cx - 2, cy, cx + 2, cy, "#606060")
        self.line(p, cx, cy - 2, cx, cy + 2, "#606060")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self._w, self._h
        mx = w // 2

        # ── Module body (blue faceplate) ─────────────────────────────
        self.rect(p, 0, 0, w, h, fill="#1a4fa0", outline="#0a2f60", width=2)

        # ── Top white tab with screw ─────────────────────────────────
        tab_h = 12
        self.rect(p, 2, 2, w - 2, tab_h, fill="#e8e8e8", outline="#c0c0c0")
        self._tab_screw(p, mx, tab_h // 2)

        # ── Blue oval logo ───────────────────────────────────────────
        logo_y = tab_h + 8
        logo_w = min(30, w - 10)
        self.oval(p, mx - logo_w // 2, logo_y, mx + logo_w // 2, logo_y + logo_w,
                  fill="#2a6fc0", outline="#4a9fe0")

        # ── Top indicators (PWR, Tx/Rx, OK) ─────────────────────────
        ind_y = logo_y + logo_w + 8
        indicators = ["PWR", "Tx/Rx", "OK"]
        ind_spacing = (w - 20) // len(indicators)
        for i, lbl in enumerate(indicators):
            ix = 10 + i * ind_spacing + ind_spacing // 2
            self.oval(p, ix - 6, ind_y, ix + 6, ind_y + 12, fill="#888888", outline="#a0a0a0")
            self.text(p, ix, ind_y + 20, lbl, "#ffffff", 5, family="Segoe UI")

        # ── ALARM section with 4 indicators ─────────────────────────
        alarm_y = ind_y + 28
        alarm_box_h = 40
        self.rect(p, 4, alarm_y, w - 4, alarm_y + alarm_box_h, fill="#0a2040", outline="#1a4070")
        self.text(p, mx, alarm_y + 6, "ALARM", "#ffffff", 5, bold=True, family="Segoe UI")

        alarm_indicators = ["OK", "ALT", "DAN", "BYP"]
        alarm_spacing = (w - 12) // len(alarm_indicators)
        for i, lbl in enumerate(alarm_indicators):
            aix = 6 + i * alarm_spacing + alarm_spacing // 2
            aiy = alarm_y + 18
            self.oval(p, aix - 5, aiy, aix + 5, aiy + 10, fill="#888888", outline="#a0a0a0")
            self.text(p, aix, aiy + 14, lbl, "#ffffff", 4, family="Segoe UI")

        # ── BNC connectors (4 vertical) ─────────────────────────────
        conn_start_y = alarm_y + alarm_box_h + 8
        conn_spacing = (h - 12 - conn_start_y) // 4
        for i in range(4):
            cy = conn_start_y + i * conn_spacing + conn_spacing // 2
            self.oval(p, mx - 7, cy - 7, mx + 7, cy + 7, fill="#c0c0c0", outline="#808080")
            self.oval(p, mx - 4, cy - 4, mx + 4, cy + 4, fill="#404040", outline="#606060")

        # ── Bottom white tab with screw ─────────────────────────────
        bot_tab_y = h - 12
        self.rect(p, 2, bot_tab_y, w - 2, h - 2, fill="#e8e8e8", outline="#c0c0c0")
        self._tab_screw(p, mx, bot_tab_y + 5)

        # ── VMM-6M label ────────────────────────────────────────────
        self.text(p, mx, bot_tab_y - 8, "VMM-6M", "#ffffff", 6, bold=True, family="Segoe UI")
        p.end()


# ══════════════════════════════════════════════════════════════════════════════
#  Standalone preview
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication, QHBoxLayout

    app = QApplication(sys.argv)
    w = QWidget()
    w.setWindowTitle("PSM Front Panel Display")
    w.setStyleSheet("background:#1a1a1a;")
    lay = QHBoxLayout(w)
    lay.addWidget(PSMFrontPanel(width=120, height=400))
    lay.addWidget(VMM6MModule(width=100, height=350))
    w.show()
    sys.exit(app.exec())
