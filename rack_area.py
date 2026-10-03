"""
rack_area.py — VMS 3000  •  Interactive rack view

Draws the PSM column, the 12 slot cards (module photos), slot numbers and
handles click / right-click / hover on the slots.
"""

import datetime
import json
import math
import os
import sys

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget,
)

from theme import T
from qt_common import (
    pick_font, qfont, scaled_pixmap, show_error, show_info, show_warning,
)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from popups.configuration_settings import ConfigurationSettingsPopup
from popups.monitors import CascadingMenu
from popups.module_switch_confirmation import ModuleSwitchConfirmationPopup
from snapshot.racksnapshot import get_module_config, is_image_display_module
from points.point_options import PointOptionsContextMenu
from points.setpoins import SetpointsDialog
from points.proximiter12m_ridial import ProximityMonitor3000ConfigDialog
from points.relay_config import RelayConfigDialog
from points.sixm_option import SixMOptionsDialog   # (kept for the 3000/6M options dialog)

SLOT_COUNT = 12

# Modules that consume 2 slots and show the Measurement Module image
DIS_MODULE = "3000/12M/DIS"
VMM_MODULE = "VMM-6M"    # single-slot image (existing behaviour)
RLY_MODULE = "3000/RLY"  # single-slot Relay module image (fallback exact name)
SIXM_MODULE = "3000/6M"  # 3000/6M module

SELECT_COLOR = "#f0b040"


def _is_6m_module(module: str) -> bool:
    """Check if module is a 3000/6M module."""
    if not module:
        return False
    if module == SIXM_MODULE:
        return True
    upper = module.upper()
    return "6M" in upper and "3000" in upper


def _is_relay_module(module: str) -> bool:
    """
    Flexible Relay-module check. Matches the exact RLY_MODULE string OR
    any module name containing 'RLY' / 'RELAY' (case-insensitive).
    """
    if not module:
        return False
    if module == RLY_MODULE:
        return True
    upper = module.upper()
    return "RLY" in upper or "RELAY" in upper


def _find_image_case_insensitive(base_dir, filename, subfolders):
    """
    Search a list of subfolders (relative to base_dir) for `filename`,
    ignoring case. Returns the first match found on disk, or None.
    """
    target = filename.lower()
    for sub in subfolders:
        folder = os.path.join(base_dir, *sub) if sub else base_dir
        if not os.path.isdir(folder):
            continue
        try:
            entries = os.listdir(folder)
        except OSError:
            continue
        for f in entries:
            if f.lower() == target:
                return os.path.join(folder, f)
    return None


def _load_photo(filename, target_w, target_h):
    """Load src/images/<filename> stretched to (w, h); None when unavailable."""
    return scaled_pixmap(filename, target_w, target_h)


def _col(hex_, alpha=None):
    c = QColor(hex_)
    if alpha is not None:
        c.setAlpha(alpha)
    return c


# ══════════════════════════════════════════════════════════════════════════
#  The painted canvas
# ══════════════════════════════════════════════════════════════════════════

class _RackCanvas(QWidget):

    def __init__(self, area: "RackArea"):
        super().__init__()
        self._area = area
        self._hits = []                 # [(QRectF, key, slot_num, right_clickable)]
        self._hover_key = None
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(200, 120)

    # ── Hit testing ────────────────────────────────────────────────
    def _hit(self, pos):
        for rect, key, slot_num, rclick in reversed(self._hits):
            if rect.contains(pos):
                return key, slot_num, rclick
        return None

    def mouseMoveEvent(self, e):
        h = self._hit(e.position())
        key = h[0] if h else None
        if key != self._hover_key:
            if self._hover_key is not None:
                self._area._hover(self._hover_key, False)
            self._hover_key = key
            if key is not None:
                self._area._hover(key, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor if h else Qt.CursorShape.ArrowCursor)

    def leaveEvent(self, e):
        if self._hover_key is not None:
            self._area._hover(self._hover_key, False)
            self._hover_key = None

    def mousePressEvent(self, e):
        h = self._hit(e.position())
        if not h:
            return
        key, slot_num, rclick = h
        gp = e.globalPosition().toPoint()
        if e.button() == Qt.MouseButton.LeftButton:
            self._area._click(key, slot_num, gp)
        elif e.button() == Qt.MouseButton.RightButton and rclick:
            self._area._right_click(key, slot_num, gp)

    # ── Painting ───────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        p.fillRect(self.rect(), _col(T["win_bg"]))
        self._hits = []
        self._area._draw(self, p)
        p.end()


# ══════════════════════════════════════════════════════════════════════════
#  RackArea
# ══════════════════════════════════════════════════════════════════════════

class RackArea(QWidget):

    DEFAULT_HINT = "Click any slot to assign module"

    def __init__(self, parent, fonts, hint=None):
        super().__init__(parent)
        self._fonts = fonts
        self._hint_cb = hint            # optional callable(str); label is built-in too
        self._selected = None
        self._slot_data: dict = {}

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 10, 0, 10)
        lay.setSpacing(6)

        self._canvas = _RackCanvas(self)
        lay.addWidget(self._canvas, 1)

        hint_bar = QHBoxLayout()
        hint_bar.setContentsMargins(6, 0, 0, 0)
        icon = QLabel("ℹ")
        icon.setFont(qfont("Segoe UI", 10))
        icon.setStyleSheet(f"color:{T['accent']}; background:transparent;")
        hint_bar.addWidget(icon)
        hint_bar.addSpacing(4)
        self._hint_label = QLabel(self.DEFAULT_HINT)
        self._hint_label.setFont(qfont("Segoe UI", 10))
        self._hint_label.setStyleSheet(f"color:{T['text_hint']}; background:transparent;")
        hint_bar.addWidget(self._hint_label)
        hint_bar.addStretch(1)
        lay.addLayout(hint_bar)

        self._psm_images = {}

    # ── Hint ────────────────────────────────────────────────────────
    def set_hint(self, text: str):
        self._hint_label.setText(text)
        if self._hint_cb:
            self._hint_cb(text)

    # ── Public ──────────────────────────────────────────────────────
    def clear(self):
        self._slot_data.clear()
        self._selected = None
        self.draw()

    def draw(self):
        self._canvas.update()

    def _redraw_now(self):
        self._canvas.repaint()

    def get_slot_data(self) -> dict:
        return dict(self._slot_data)

    def save_configuration(self, name: str = None):
        """Save current rack configuration to local system."""
        if not name:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"rack_config_{timestamp}.json"
        else:
            default_name = f"{name}.json"

        file_path, _ = QFileDialog.getSaveFileName(
            self._canvas, "Save Configuration", default_name,
            "JSON files (*.json);;All files (*)",
        )
        if not file_path:
            return None
        if "." not in os.path.basename(file_path):
            file_path += ".json"

        try:
            config = {
                "timestamp": datetime.datetime.now().isoformat(),
                "slot_data": self._slot_data,
                "slot_count": SLOT_COUNT,
            }
            with open(file_path, "w") as f:
                json.dump(config, f, indent=2)
            show_info(self._canvas, "Save Configuration", f"Configuration saved to {file_path}")
            return file_path
        except Exception as e:
            show_error(self._canvas, "Save Error", f"Failed to save configuration: {e}")
            return None

    def load_configuration(self):
        """Load rack configuration from local system."""
        file_path, _ = QFileDialog.getOpenFileName(
            self._canvas, "Load Configuration", "",
            "JSON files (*.json);;All files (*)",
        )
        if not file_path:
            return None

        try:
            with open(file_path, "r") as f:
                config = json.load(f)

            self._slot_data.clear()
            self._slot_data.update(config.get("slot_data", {}))
            self._selected = None
            self.draw()
            show_info(self._canvas, "Load Configuration", f"Configuration loaded from {file_path}")
            return config
        except Exception as e:
            show_error(self._canvas, "Load Error", f"Failed to load configuration: {e}")
            return None

    # ── Layout constants ────────────────────────────────────────────
    def _layout(self, W: int, H: int) -> dict:
        PSM_W = 140  # width for PSM (0-index) column images
        PAD_X = 14
        TOP_Y = 32
        PAD_BOT = 10
        SHELL_H = H - TOP_Y - PAD_BOT

        slot_x0 = PAD_X + PSM_W + 8
        slot_w_total = W - PAD_X * 2 - PSM_W - 8 - PAD_X
        sw = slot_w_total / SLOT_COUNT

        return dict(
            PAD_X=PAD_X, TOP_Y=TOP_Y, PAD_BOT=PAD_BOT,
            SHELL_H=SHELL_H, PSM_W=PSM_W,
            slot_x0=slot_x0, sw=sw,
            W=W, H=H,
        )

    # ── Main draw ───────────────────────────────────────────────────
    def _draw(self, cv: _RackCanvas, p: QPainter):
        W, H = cv.width(), cv.height()
        if W < 200 or H < 120:
            return

        L = self._layout(W, H)
        self._draw_rack_shell(p, L)
        self._draw_slot_headers(p, L)
        self._draw_psm_top(p, L)
        self._draw_psm_bottom(p, L)

        skip_next = False
        for slot in range(SLOT_COUNT):
            if skip_next:
                skip_next = False
                continue
            slot_num = slot + 1
            key = f"0_{slot_num}"
            module = self._slot_data.get(key)
            if module == DIS_MODULE:
                self._draw_dis_module(cv, p, L, slot)
                skip_next = True
            else:
                self._draw_slot(cv, p, L, slot)

    # ── small paint helpers ─────────────────────────────────────────
    @staticmethod
    def _rect(p, x1, y1, x2, y2, fill=None, outline=None, width=1):
        p.setPen(QPen(_col(outline), width) if outline else Qt.PenStyle.NoPen)
        p.setBrush(_col(fill) if fill else Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(x1, y1, x2 - x1, y2 - y1))

    @staticmethod
    def _oval(p, x1, y1, x2, y2, fill=None, outline=None, width=1, alpha=None):
        p.setPen(QPen(_col(outline), width) if outline else Qt.PenStyle.NoPen)
        p.setBrush(_col(fill, alpha) if fill else Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(x1, y1, x2 - x1, y2 - y1))

    @staticmethod
    def _line(p, x1, y1, x2, y2, color, width=1):
        p.setPen(QPen(_col(color), width))
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    @staticmethod
    def _text(p, x, y, txt, color, font, anchor="center"):
        p.setFont(font)
        p.setPen(_col(color))
        big = 600
        if anchor == "center":
            r = QRectF(x - big / 2, y - big / 2, big, big)
            flags = Qt.AlignmentFlag.AlignCenter
        else:   # "w"
            r = QRectF(x, y - big / 2, big, big)
            flags = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        p.drawText(r, flags, txt)

    # ── Rack shell ──────────────────────────────────────────────────
    def _draw_rack_shell(self, p, L):
        x1 = L["PAD_X"]
        y1 = L["TOP_Y"] - 6
        x2 = L["W"] - L["PAD_X"]
        y2 = y1 + L["SHELL_H"]

        self._rect(p, x1, y1, x2, y2, fill=T["rack_shell_bot"])
        self._rect(p, x1 + 6, y1 + 6, x2 - 6, y2 - 6, fill=T["rack_row"],
                   outline="#0a0f18", width=1)

    # ── Slot number headers ─────────────────────────────────────────
    def _draw_slot_headers(self, p, L):
        skip_next = False
        font = pick_font(self._fonts, "num", size=9, bold=True)
        for i in range(1, SLOT_COUNT + 1):
            if skip_next:
                skip_next = False
                continue

            if i == 1:
                continue

            key = f"0_{i}"
            module = self._slot_data.get(key)
            is_selected = (self._selected == key)

            fill_color = "#cc2222" if is_selected else "#888888"
            display_num = i - 1

            if module == DIS_MODULE:
                # DIS occupies raw slots i and i+1 (displayed numbers i-1 and
                # i). Show the pair's FIRST / lower displayed number.
                cx = L["slot_x0"] + (i - 1 + 1.0) * L["sw"]
                self._text(p, cx, L["TOP_Y"] - 14, str(display_num), fill_color, font)
                skip_next = True
            else:
                cx = L["slot_x0"] + (i - 1 + 0.5) * L["sw"]
                self._text(p, cx, L["TOP_Y"] - 14, str(display_num), fill_color, font)

    # ── Hand-drawn PSM panel (fallback when the photo is missing) ───
    def _draw_psm_panel(self, p, L, px1, py1, px2, py2, label):
        mx = (px1 + px2) // 2

        self._rect(p, px1, py1, px2, py2, fill=T["psm_body"], outline=T["slot_edge_sh"], width=2)
        self._line(p, px1, py1, px2, py1, "#2a4060")
        self._line(p, px1, py1, px1, py2, "#1e3050")

        logo_cx, logo_cy, logo_r = mx, py1 + 14, 10
        self._oval(p, logo_cx - logo_r, logo_cy - logo_r, logo_cx + logo_r, logo_cy + logo_r,
                   fill="#1a5fa0", outline="#4a9fd0")
        for ang in range(0, 180, 45):
            x0 = logo_cx + logo_r * math.cos(math.radians(ang))
            y0 = logo_cy + logo_r * math.sin(math.radians(ang))
            x1b = logo_cx - logo_r * math.cos(math.radians(ang))
            y1b = logo_cy - logo_r * math.sin(math.radians(ang))
            self._line(p, x0, y0, x1b, y1b, "#4ab0e0")
        self._oval(p, logo_cx - logo_r, logo_cy - 3, logo_cx + logo_r, logo_cy + 3, outline="#4ab0e0")

        strip_y = logo_cy + logo_r + 2
        self._rect(p, px1, strip_y, px2, strip_y + 14, fill=T["psm_brand"])
        self._text(p, mx, strip_y + 7, "Sarayu", "#ffffff", qfont("Segoe UI", 8, True, True))

        vy = strip_y + 18
        for i, word in enumerate(["Vibration", "Monitoring", "System"]):
            self._text(p, mx, vy + i * 11, word, T["psm_label"], qfont("Segoe UI", 6))

        volts = ["+5V", "+12V", "-12V", "+24V", "-24V"]
        vled_y0 = vy + 36
        lx = px1 + 6
        for i, lbl in enumerate(volts):
            ly = vled_y0 + i * 12
            self._oval(p, lx - 1, ly - 1, lx + 7, ly + 7, fill=T["led_green"], alpha=128)
            self._oval(p, lx + 1, ly + 1, lx + 5, ly + 5, fill=T["led_green"], outline="#ffffff")
            self._text(p, lx + 10, ly + 3, lbl, "#8ab8d8", qfont("Courier New", 5), anchor="w")

        num_y = vled_y0 + len(volts) * 12 + 6
        self._text(p, mx, num_y, "3000", T["psm_3000"], qfont("Segoe UI", 14, True))

        self._rect(p, px1 + 4, py2 - 20, px2 - 4, py2 - 4, fill=T["psm_plate"], outline="#1e3050")
        self._text(p, mx, py2 - 12, label, T["psm_plate_text"], qfont("Segoe UI", 6, True))

        return num_y + 16

    # ── Image panels (PSM top / bottom) ─────────────────────────────
    def _draw_psm_top(self, p, L):
        x1 = L["PAD_X"] + 14
        y1 = L["TOP_Y"] + 2
        x2 = x1 + L["PSM_W"] - 4
        top_end = L["TOP_Y"] + int(L["SHELL_H"] * 0.50)

        photo = _load_photo("Powersupply.jpg", max(1, x2 - x1), max(1, top_end - y1))
        if photo is not None:
            self._rect(p, x1, y1, x2, top_end, fill="#0a0e14")
            p.drawPixmap(int(x1), int(y1), photo)
        else:
            self._draw_psm_panel(p, L, x1, y1, x2, top_end, "VMS-3000 PSM")

    def _draw_psm_middle(self, p, L):
        x1 = L["PAD_X"] + 14
        x2 = x1 + L["PSM_W"] - 4
        top_end = L["TOP_Y"] + int(L["SHELL_H"] * 0.45)
        bot_st = L["TOP_Y"] + int(L["SHELL_H"] * 0.55)
        if bot_st - top_end < 10:
            bot_st = top_end + 10

        photo = _load_photo("Configuration_Module.jpg", max(1, x2 - x1), max(1, bot_st - top_end))
        if photo is not None:
            self._rect(p, x1, top_end + 2, x2, bot_st - 2, fill="#0a0e14")
            p.drawPixmap(int(x1), int(top_end + 2), photo)
        else:
            self._rect(p, x1, top_end + 2, x2, bot_st - 2, fill="#0d1a28")

    def _draw_psm_bottom(self, p, L):
        x1 = L["PAD_X"] + 14
        x2 = x1 + L["PSM_W"] - 4
        bot_st = L["TOP_Y"] + int(L["SHELL_H"] * 0.50)
        y2 = L["TOP_Y"] + L["SHELL_H"] - 12

        photo = _load_photo("Powersupply.jpg", max(1, x2 - x1), max(1, y2 - bot_st))
        if photo is not None:
            self._rect(p, x1, bot_st, x2, y2, fill="#0a0e14")
            p.drawPixmap(int(x1), int(bot_st), photo)
            return

        content_y = self._draw_psm_panel(p, L, x1, bot_st, x2, y2, "VMS-3000 CPU")

        box_x1, box_x2 = x1 + 6, x2 - 6
        box_y1 = content_y
        box_y2 = box_y1 + 30
        self._rect(p, box_x1, box_y1, box_x2, box_y2, fill="#0a1520", outline="#1e3050")

        status_leds = [
            ("PSM",  T["led_green"], 0, 0),
            ("TuRn", T["led_amber"], 0, 1),
            ("TIS",  T["led_red"],   1, 0),
            ("CMFD", T["led_blue"],  1, 1),
        ]
        cell_w = (box_x2 - box_x1) // 2
        cell_h = (box_y2 - box_y1) // 2
        for lbl, col, row, col_i in status_leds:
            cx_led = box_x1 + col_i * cell_w + 5
            cy_led = box_y1 + row * cell_h + 8
            self._oval(p, cx_led, cy_led, cx_led + 6, cy_led + 6, fill=col, outline="#ffffff")
            self._text(p, cx_led + 9, cy_led + 3, lbl, "#8ab8d8", qfont("Courier New", 5), anchor="w")

        run_y = box_y2 + 6
        mx = (box_x1 + box_x2) // 2
        self._oval(p, mx - 10, run_y, mx + 10, run_y + 12, fill="#183018", outline="#1e3050", width=2)
        self._oval(p, mx - 6, run_y + 2, mx + 6, run_y + 10, fill=T["led_green"], outline="#ffffff")
        self._text(p, mx, run_y + 18, "RUN", "#4af04a", qfont("Courier New", 5, True))

        db9_y = run_y + 26
        db9_x1, db9_x2, db9_h = mx - 14, mx + 14, 18
        self._rect(p, db9_x1, db9_y, db9_x2, db9_y + db9_h, fill="#1a2a3a", outline="#3a5a7a")
        pr_y = db9_y + 4
        for npins in (5, 4):
            spacing = (db9_x2 - db9_x1 - 6) / max(npins - 1, 1)
            for k in range(npins):
                px = db9_x1 + 3 + int(k * spacing)
                self._oval(p, px, pr_y, px + 3, pr_y + 3, fill="#000000", outline="#5a7a9a")
            pr_y += 7
        self._text(p, mx, db9_y + db9_h + 6, "PROG", "#6a9aba", qfont("Courier New", 5))

        bar_y = db9_y + db9_h + 14
        bar_x1, bar_x2, bar_h = mx - 12, mx + 12, 22
        self._rect(p, bar_x1, bar_y, bar_x2, bar_y + bar_h, fill="#1a0000", outline="#3a0000")
        seg_count = 8
        seg_h = (bar_h - 4) / seg_count
        for seg in range(seg_count):
            intensity = "#ff0000" if seg < 5 else "#660000"
            sy = bar_y + 2 + int(seg * seg_h)
            self._rect(p, bar_x1 + 3, sy, bar_x2 - 3, sy + max(1, int(seg_h) - 1), fill=intensity)

    # ══════════════════════════════════════════════════════════════════
    #  Slot geometry + generic "image card" drawing
    # ══════════════════════════════════════════════════════════════════
    @staticmethod
    def _slot_box(L, slot_idx, span=1):
        sw = L["sw"]
        sx1 = int(L["slot_x0"] + slot_idx * sw + 3)
        if span == 2:
            sx2 = int(L["slot_x0"] + (slot_idx + 2) * sw - 6)
        else:
            sx2 = int(sx1 + sw - 6)
        sy1 = L["TOP_Y"] + 2
        sy2 = L["TOP_Y"] + L["SHELL_H"] - 12
        return sx1, sy1, sx2, sy2

    def _register(self, cv, rect, key, slot_num, rclick):
        cv._hits.append((QRectF(*rect[:2], rect[2] - rect[0], rect[3] - rect[1]),
                         key, slot_num, rclick))

    def _selection_outline(self, p, sx1, sy1, sx2, sy2):
        self._rect(p, sx1, sy1, sx2, sy2, outline=SELECT_COLOR, width=3)

    def _draw_image_card(self, cv, p, L, slot_idx, filename, fallback_fill,
                         fallback_lines, is_sel, rclick, span=1):
        """Photo (or coloured fallback with text) filling the slot, + selection ring."""
        slot_num = slot_idx + 1
        key = f"0_{slot_num}"
        sx1, sy1, sx2, sy2 = self._slot_box(L, slot_idx, span)

        photo = _load_photo(filename, max(1, sx2 - sx1), max(1, sy2 - sy1))
        if photo is not None:
            self._rect(p, sx1, sy1, sx2, sy2, fill="#0a0e14")
            p.drawPixmap(sx1, sy1, photo)
        else:
            self._rect(p, sx1, sy1, sx2, sy2, fill=fallback_fill)
            mx, my = (sx1 + sx2) // 2, (sy1 + sy2) // 2
            for dy, txt, color, font in fallback_lines:
                self._text(p, mx, my + dy, txt, color, font)

        if is_sel:
            self._selection_outline(p, sx1, sy1, sx2, sy2)

        self._register(cv, (sx1, sy1, sx2, sy2), key, slot_num, rclick)

    # ══════════════════════════════════════════════════════════════════
    #  3000/12M/DIS — double-wide Measurement Module card
    # ══════════════════════════════════════════════════════════════════
    def _draw_dis_module(self, cv, p, L, slot_idx):
        key = f"0_{slot_idx + 1}"
        self._draw_image_card(
            cv, p, L, slot_idx, "Measurement_Module.jpg", "#1a4fa0",
            [(-8, "VMS-3000", "#ffffff", qfont("Segoe UI", 9, True)),
             (8, "3000/12M/DIS", "#aaccff", qfont("Segoe UI", 7))],
            self._selected == key, True, span=2)

    # ── Slot card ───────────────────────────────────────────────────
    def _draw_slot(self, cv, p, L, slot_idx):
        slot_num = slot_idx + 1
        key = f"0_{slot_num}"
        is_sel = (self._selected == key)
        module = self._slot_data.get(key)

        if _is_relay_module(module):
            self._draw_image_card(
                cv, p, L, slot_idx, "Relay_Module.jpg", "#1a4fa0",
                [(0, "3000/RLY", "#ffffff", qfont("Segoe UI", 8, True))], is_sel, True)
            return

        if _is_6m_module(module):
            self._draw_image_card(
                cv, p, L, slot_idx, "VMM-6M.jpg", "#5a8a5a",
                [(0, "3000/6M", "#ffffff", qfont("Segoe UI", 8, True))], is_sel, True)
            return

        if module and is_image_display_module(module):
            # VMM-6M detailed module — single-slot image card (left-click only)
            self._draw_image_card(
                cv, p, L, slot_idx, "VMM-6M.jpg", "#1a4fa0",
                [(0, "VMM-6M", "#ffffff", qfont("Segoe UI", 8, True))], is_sel, False)
            return

        sx1, sy1, sx2, sy2 = self._slot_box(L, slot_idx)
        slot_w, slot_h = max(1, sx2 - sx1), max(1, sy2 - sy1)
        mx = (sx1 + sx2) // 2

        # Slot 1 is the fixed Configuration/status panel (RUN dial, DB9 port,
        # DIP switches, LEDs) — it always shows Configuration_Module.jpg.
        if slot_num == 1:
            photo = _load_photo("Configuration_Module.jpg", slot_w, slot_h)
        else:
            photo = _load_photo("NO_Module.jpg", slot_w, slot_h)

        if photo is not None:
            p.drawPixmap(sx1, sy1, photo)
        else:
            # Fallback blue rectangle if image fails to load
            if is_sel:
                face_col, edge_col = T["slot_sel_face"], T["slot_sel"]
            else:
                face_col, edge_col = T["slot_face"], T["slot_edge_sh"]

            self._rect(p, sx1, sy1, sx2, sy2, fill=face_col, outline=edge_col, width=2)

            cap_w, cap_h = 22, 8
            self._rect(p, mx - cap_w // 2, sy1 + 8, mx + cap_w // 2, sy1 + 8 + cap_h,
                       fill=T["slot_cap"] if not is_sel else "#fde68a", outline=edge_col)

            panel_y1 = sy1 + 8 + cap_h + 8
            panel_y2 = sy2 - 10
            self._rect(p, sx1 + 6, panel_y1, sx2 - 6, panel_y2, fill=face_col, outline=edge_col)

            if module:
                short = module.split()[0]
                self._text(p, mx, (panel_y1 + panel_y2) // 2, short, T["slot_mod_fg"],
                           qfont("Courier New", 7, True))

            self._rect(p, sx1 + 4, sy2 - 6, sx2 - 4, sy2 - 2, fill="#0a1520")

        if is_sel:
            self._selection_outline(p, sx1, sy1, sx2, sy2)

        self._register(cv, (sx1, sy1, sx2, sy2), key, slot_num, False)

    # ── Interaction ─────────────────────────────────────────────────
    def _hover(self, key: str, entering: bool):
        if self._selected == key:
            return
        slot_n = key.split("_")[1]
        assigned = self._slot_data.get(key)
        if entering:
            self.set_hint(
                f"Slot {slot_n}  —  "
                + (f"Module: {assigned}" if assigned else "Empty — click to assign module")
            )
        else:
            self.set_hint(self.DEFAULT_HINT)

    def _click(self, key: str, slot_num: int, pos=None):
        self._selected = key
        self._redraw_now()
        self.set_hint(f"Slot {slot_num} selected")

        if slot_num == 1:
            self._config_settings_dialog()
        else:
            self._module_dialog(key, slot_num, pos)

    def _right_click(self, key: str, slot_num: int, pos):
        """Right-click on DIS / 6M / Relay modules shows the point context menu."""
        module = self._slot_data.get(key)
        fonts = self._fonts

        # DIS_MODULE and 3000/6M: Options, Setpoints, Point Names
        if module == DIS_MODULE or _is_6m_module(module):
            model = "12M/DIS" if module == DIS_MODULE else "6M"

            def on_options(slot):
                ProximityMonitor3000ConfigDialog(self._canvas, slot, model=model).show()

            def on_setpoints(slot):
                SetpointsDialog(self._canvas, fonts, slot).show()

            def on_point_names(slot):
                # TODO: Implement Point Names dialog
                print(f"Point Names for slot {slot}")

            menu = PointOptionsContextMenu(
                self._canvas, fonts, slot_num,
                on_options=on_options, on_setpoints=on_setpoints,
                on_point_names=on_point_names,
            )
            menu.show(pos.x(), pos.y())

        # RELAY_MODULE: only Setpoints
        elif _is_relay_module(module):
            def on_setpoints(slot):
                RelayConfigDialog(self._canvas, slot, module, "A1",
                                  rack_config=self._slot_data).show()

            menu = PointOptionsContextMenu(
                self._canvas, fonts, slot_num, on_setpoints=on_setpoints,
            )
            menu.show(pos.x(), pos.y())

    # ── Configuration Settings dialog (for slot 1) ──────────────────
    def _config_settings_dialog(self):
        ConfigurationSettingsPopup(self._canvas, self._fonts).show()
        self._selected = None
        self.draw()
        self.set_hint("Configuration Settings closed")

    # ── Module assignment — cascading flyout menu ────────────────────

    # Raw slots where a DIS module may start. DIS occupies (slot_num,
    # slot_num+1) — a sliding window, NOT fixed non-overlapping pairs.
    # Raw slot 1 is reserved for Configuration Settings. Raw slot SLOT_COUNT
    # (the last physical slot, displayed as "11") CAN become the tail of a DIS
    # pair — the "6M/Relay only" restriction below only applies when the last
    # slot is selected directly on its own.
    _DIS_ALLOWED_START_SLOTS = tuple(range(2, SLOT_COUNT))
    # Raw slot 12 (displayed as "11") is the last physical slot. If it is
    # selected directly (not as the tail of a DIS pair), only 3000/6M or Relay
    # are permitted there.
    _LAST_SLOT_RESTRICTED = 12

    @staticmethod
    def _is_vmm_or_relay(selection: str) -> bool:
        if not selection:
            return False
        if selection == "No Modules":
            return True
        if selection == VMM_MODULE or selection == "3000/6M":
            return True
        return _is_relay_module(selection)

    def _module_dialog(self, key: str, slot_num: int, pos=None):
        def on_selection(selection):
            current_module = self._slot_data.get(key)

            # ── Rule: last slot (raw 12 / displayed 11) is restricted ──
            if slot_num == self._LAST_SLOT_RESTRICTED and not self._is_vmm_or_relay(selection):
                show_warning(self._canvas, "Module Selection",
                             "This slot only allows 3000/6M or Relay modules.")
                return

            # ── Rule: slot that's the tail of a DIS pair ──
            prev_module = self._slot_data.get(f"0_{slot_num - 1}")
            if prev_module == DIS_MODULE and selection != "No Modules":
                show_warning(self._canvas, "Module Selection",
                             "This slot is occupied by 3000/12M/DIS from the previous slot.\n"
                             "Please select a different slot.")
                return

            # ── Rule: DIS placement — allowed start slots, partner slot free ──
            if selection == DIS_MODULE:
                if slot_num not in self._DIS_ALLOWED_START_SLOTS:
                    show_warning(self._canvas, "Module Selection",
                                 "3000/12M/DIS cannot be placed starting at this slot.")
                    return

                partner_module = self._slot_data.get(f"0_{slot_num + 1}")
                # Allow DIS if partner slot is empty (None) or "No Modules"
                if partner_module is not None and partner_module != "No Modules":
                    show_warning(self._canvas, "Module Selection",
                                 "The next slot is already occupied.\n"
                                 "3000/12M/DIS needs this slot and the next one to be free.")
                    return

            if current_module and selection != "No Modules" and current_module != selection:
                def on_switch_confirmed(confirmed):
                    if confirmed:
                        self._slot_data[key] = selection
                        self._selected = key
                        self.draw()
                        self.set_hint(f"Slot {slot_num} → {self._slot_data.get(key, 'Empty')}")

                ModuleSwitchConfirmationPopup(
                    self._canvas, self._fonts, current_module, selection, on_switch_confirmed
                ).show()
                return

            if selection == "No Modules":
                self._slot_data.pop(key, None)
            else:
                self._slot_data[key] = selection
            self._selected = key
            self.draw()
            self.set_hint(f"Slot {slot_num} → {self._slot_data.get(key, 'Empty')}")

        # Cascading flyout menu (Monitors ▸ Proximeter/Tachometer ▸ Model,
        # Gateways, Relay ▸ Model, No Modules)
        menu = CascadingMenu(self._canvas, self._fonts, on_selection)

        if pos is not None:
            x, y = pos.x(), pos.y()
        else:
            # Fallback: anchor near the canvas if no click position is available
            g = self._canvas.mapToGlobal(self._canvas.rect().topLeft())
            x, y = g.x() + 40, g.y() + 40

        menu.show_menu(x, y)
