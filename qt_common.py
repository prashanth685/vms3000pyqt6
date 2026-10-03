"""
qt_common.py — VMS 3000  •  Shared PyQt6 helpers

Everything that several windows/dialogs have in common lives here so the
individual modules stay short:

    make_fonts() / pick_font()      font dictionary (replaces tkinter.font)
    ThemedDialog                    navy title strip + teal rule + body + footer
    make_button() / style_button()  flat themed push buttons
    themed_group()                  the accent-coloured "groove" group box
    show_help_dialog()              the little read-only help window
    show_info / show_warning / ...  message-box wrappers (replaces messagebox)
    scaled_pixmap()                 cached, scaled image loading (replaces PIL/ImageTk)
"""

from __future__ import annotations

import os
import tempfile
from typing import Callable, Iterable, Optional

from PyQt6.QtCore import Qt, QSize, QRectF
from PyQt6.QtGui import QFont, QColor, QPixmap, QGuiApplication, QPainter, QPen, QPolygonF, QPalette
from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QGroupBox, QMessageBox, QLineEdit, QSizePolicy,
)

from theme import T

# ══════════════════════════════════════════════════════════════════════════
#  Paths
# ══════════════════════════════════════════════════════════════════════════

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(PROJECT_ROOT, "src", "images")


# ══════════════════════════════════════════════════════════════════════════
#  Fonts
# ══════════════════════════════════════════════════════════════════════════

def qfont(family: str = "Segoe UI", size: int = 9, bold: bool = False,
          italic: bool = False) -> QFont:
    """Build a QFont from a point size (same numbers the tkinter code used)."""
    f = QFont(family)
    f.setPointSize(size)
    f.setBold(bold)
    f.setItalic(italic)
    return f


def make_fonts() -> dict:
    """Application-wide font table (same keys the tkinter version used)."""
    return {
        "menu":  qfont("Segoe UI", 11),
        "ui":    qfont("Segoe UI", 10),
        "ui_b":  qfont("Segoe UI", 10, bold=True),
        "sm":    qfont("Segoe UI", 9),
        "sm_b":  qfont("Segoe UI", 9, bold=True),
        "xs":    qfont("Segoe UI", 8),
        "xs_b":  qfont("Segoe UI", 8, bold=True),
        "vms":   qfont("Segoe UI", 13, bold=True),
        "mono":  qfont("Courier New", 9),
        "num":   qfont("Segoe UI", 9, bold=True),
    }


def pick_font(fonts: Optional[dict], key: str, family: str = "Segoe UI",
              size: int = 9, bold: bool = False, italic: bool = False) -> QFont:
    """
    Return fonts[key] if the caller supplied one, otherwise build a fallback.
    Mirrors the old ``_f(key, family, size, weight)`` helper.
    """
    if isinstance(fonts, dict):
        f = fonts.get(key)
        if isinstance(f, QFont):
            return QFont(f)
    return qfont(family, size, bold, italic)


# ══════════════════════════════════════════════════════════════════════════
#  Runtime-generated indicator images (combo arrows, check boxes)
#
#  Qt style sheets strip the native indicator from combo boxes / check boxes
#  as soon as the widget is styled, so we draw tiny PNGs once and reference
#  them with ``image: url(...)``.
# ══════════════════════════════════════════════════════════════════════════

_ASSET_DIR = os.path.join(tempfile.gettempdir(), "vms3000_qt_assets")


def _asset(name: str, w: int, h: int, draw: Callable) -> str:
    os.makedirs(_ASSET_DIR, exist_ok=True)
    path = os.path.join(_ASSET_DIR, name)
    if not os.path.exists(path):
        pm = QPixmap(w, h)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        draw(p)
        p.end()
        pm.save(path, "PNG")
    return path.replace("\\", "/")


def arrow_url(color: str = "#000000") -> str:
    """Small down-pointing triangle for combo boxes."""
    def draw(p):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        p.drawPolygon(QPolygonF([QPointF(1, 1.5), QPointF(9, 1.5), QPointF(5, 6.5)]))
    return _asset(f"arrow_{color.strip('#')}.png", 10, 8, draw)


def checkbox_urls(border: str = "#5a5a5a", fill: str = "#ffffff",
                  mark: str = "#1a3a5c") -> tuple:
    """(unchecked.png, checked.png) for a 13×13 check box indicator."""
    key = f"{border}{fill}{mark}".replace("#", "")

    def unchecked(p):
        p.setPen(QPen(QColor(border), 1))
        p.setBrush(QColor(fill))
        p.drawRect(QRectF(0.5, 0.5, 12, 12))

    def checked(p):
        unchecked(p)
        p.setPen(QPen(QColor(mark), 2))
        p.drawPolyline(QPolygonF([QPointF(3, 6.5), QPointF(5.5, 9.5), QPointF(10, 3.5)]))

    return (_asset(f"chk_off_{key}.png", 13, 13, unchecked),
            _asset(f"chk_on_{key}.png", 13, 13, checked))


def checkbox_qss(color: str = "#000000", hover_bg: Optional[str] = None,
                 padding: str = "0px", border: str = "#5a5a5a",
                 mark: str = "#1a3a5c") -> str:
    off, on = checkbox_urls(border=border, mark=mark)
    hover = f"QCheckBox:hover {{ background:{hover_bg}; }}" if hover_bg else ""
    return (
        f"QCheckBox {{ color:{color}; background:transparent; padding:{padding}; spacing:6px; }}"
        f"QCheckBox:disabled {{ color:#8895a6; }}"
        f"{hover}"
        f"QCheckBox::indicator {{ width:13px; height:13px; }}"
        f"QCheckBox::indicator:unchecked {{ image:url({off}); }}"
        f"QCheckBox::indicator:checked {{ image:url({on}); }}"
    )


def field_palette(widget: QWidget, base: str, text: str = "#000000") -> None:
    """Colour a spin box / similar widget through its palette, keeping the
    native Fusion arrows (a style sheet would remove them)."""
    pal = widget.palette()
    pal.setColor(QPalette.ColorRole.Base, QColor(base))
    pal.setColor(QPalette.ColorRole.Text, QColor(text))
    widget.setPalette(pal)


# ══════════════════════════════════════════════════════════════════════════
#  Small utilities
# ══════════════════════════════════════════════════════════════════════════

def qcolor(hex_or_name: str, alpha: Optional[int] = None) -> QColor:
    c = QColor(hex_or_name)
    if alpha is not None:
        c.setAlpha(alpha)
    return c


def char_width(font: QFont, n: int) -> int:
    """Pixel width of *n* '0' characters — Tk's ``width=N`` (in characters)."""
    from PyQt6.QtGui import QFontMetrics
    return QFontMetrics(font).horizontalAdvance("0") * n


def hline(color: str, height: int = 1) -> QFrame:
    f = QFrame()
    f.setFixedHeight(height)
    f.setStyleSheet(f"background:{color}; border:none;")
    return f


def vline(color: str, width: int = 1) -> QFrame:
    f = QFrame()
    f.setFixedWidth(width)
    f.setStyleSheet(f"background:{color}; border:none;")
    return f


def center_on_screen(widget: QWidget) -> None:
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return
    geo = screen.availableGeometry()
    fg = widget.frameGeometry()
    fg.moveCenter(geo.center())
    widget.move(fg.topLeft())


def center_on_parent(widget: QWidget, parent: Optional[QWidget]) -> None:
    """Centre on the top-level window of *parent*; fall back to the screen."""
    if parent is None:
        center_on_screen(widget)
        return
    win = parent.window()
    fg = widget.frameGeometry()
    fg.moveCenter(win.frameGeometry().center())
    widget.move(fg.topLeft())


def fixed_at_least(widget: QWidget, w: int, h: int) -> None:
    """
    Non-resizable window that is *at least* w×h but never smaller than its
    content needs (font metrics differ between platforms, so a hard-coded
    pixel size from the tkinter version could clip text).
    """
    widget.adjustSize()
    hint = widget.sizeHint()
    widget.setFixedSize(max(w, hint.width()), max(h, hint.height()))


# ══════════════════════════════════════════════════════════════════════════
#  Image loading (replaces PIL.ImageTk)
# ══════════════════════════════════════════════════════════════════════════

_PIXMAP_CACHE: dict = {}


def image_path(filename: str) -> str:
    return os.path.join(IMAGES_DIR, filename)


def scaled_pixmap(filename: str, w: int, h: int, keep_aspect: bool = False,
                  base_dir: Optional[str] = None) -> Optional[QPixmap]:
    """
    Load ``src/images/<filename>`` scaled to (w, h). Returns None when the
    file is missing or unreadable. Results are cached per (file, size, mode).
    keep_aspect=False stretches to fill (rack cards);
    keep_aspect=True   fits inside the box ("contain").
    """
    w = max(1, int(round(w)))
    h = max(1, int(round(h)))
    folder = base_dir or IMAGES_DIR
    key = (folder, filename, w, h, keep_aspect)
    if key in _PIXMAP_CACHE:
        return _PIXMAP_CACHE[key]
    if len(_PIXMAP_CACHE) > 256:        # resizing the window creates many sizes
        _PIXMAP_CACHE.clear()

    path = os.path.join(folder, filename)
    pm: Optional[QPixmap] = None
    if os.path.exists(path):
        src = QPixmap(path)
        if not src.isNull():
            mode = (Qt.AspectRatioMode.KeepAspectRatio if keep_aspect
                    else Qt.AspectRatioMode.IgnoreAspectRatio)
            pm = src.scaled(w, h, mode, Qt.TransformationMode.SmoothTransformation)
    _PIXMAP_CACHE[key] = pm
    return pm


# ══════════════════════════════════════════════════════════════════════════
#  Message boxes (replaces tkinter.messagebox)
# ══════════════════════════════════════════════════════════════════════════

def show_info(parent, title: str, text: str) -> None:
    QMessageBox.information(parent, title, text)


def show_warning(parent, title: str, text: str) -> None:
    QMessageBox.warning(parent, title, text)


def show_error(parent, title: str, text: str) -> None:
    QMessageBox.critical(parent, title, text)


def ask_yes_no(parent, title: str, text: str) -> bool:
    r = QMessageBox.question(
        parent, title, text,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return r == QMessageBox.StandardButton.Yes


# ══════════════════════════════════════════════════════════════════════════
#  Buttons
# ══════════════════════════════════════════════════════════════════════════

def _palette(palette: Optional[dict]) -> dict:
    return {**T, **(palette or {})}


def button_qss(bg: str, fg: str, hover_bg: str, hover_fg: str, border: str,
               pad: str = "6px 14px", disabled_bg: str = "#eef1f6",
               disabled_fg: str = "#9aa0aa") -> str:
    return f"""
        QPushButton {{
            background:{bg}; color:{fg};
            border:1px solid {border}; padding:{pad};
        }}
        QPushButton:hover   {{ background:{hover_bg}; color:{hover_fg}; }}
        QPushButton:pressed {{ background:{hover_bg}; color:{hover_fg}; }}
        QPushButton:disabled {{ background:{disabled_bg}; color:{disabled_fg}; }}
    """


def style_button(btn: QPushButton, kind: str = "normal",
                 palette: Optional[dict] = None, pad: str = "6px 14px") -> QPushButton:
    """kind: 'primary' (solid accent), 'amber' (warning), or 'normal'."""
    P = _palette(palette)
    if kind == "primary":
        qss = button_qss(P["accent"], P["text_white"], P["accent_light"],
                         P["text_white"], P["btn_border"], pad)
    elif kind == "amber":
        qss = button_qss(P["led_amber"], "#1a1a00", "#d48800", "#1a1a00",
                         P["btn_border"], pad)
    else:
        qss = button_qss(P["btn_face"], P["text"], P["btn_hover"], P["text"],
                         P["btn_border"], pad)
    btn.setStyleSheet(qss)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def make_button(text: str, callback: Optional[Callable] = None, kind: str = "normal",
                font: Optional[QFont] = None, palette: Optional[dict] = None,
                pad: str = "6px 14px", parent: Optional[QWidget] = None) -> QPushButton:
    b = QPushButton(text, parent)
    if font is not None:
        b.setFont(font)
    style_button(b, kind, palette, pad)
    b.setAutoDefault(False)
    b.setDefault(False)
    if callback is not None:
        b.clicked.connect(lambda _checked=False, cb=callback: cb())
    return b


# ══════════════════════════════════════════════════════════════════════════
#  Group box  (Tk LabelFrame, relief=groove)
# ══════════════════════════════════════════════════════════════════════════

def group_qss(P: dict, selector: str = "QGroupBox") -> str:
    return f"""
        {selector} {{
            background:{P['win_bg']};
            border:2px groove {P['btn_border']};
            margin-top:10px;
            padding:12px 12px 8px 12px;
        }}
        {selector}::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left:10px; padding:0 4px;
            color:{P['accent']};
        }}
    """


def themed_group(title: str, fonts: Optional[dict] = None,
                 palette: Optional[dict] = None) -> QGroupBox:
    P = _palette(palette)
    g = QGroupBox(f"  {title}  ")
    g.setFont(pick_font(fonts, "sm_b", size=9, bold=True))
    g.setStyleSheet(group_qss(P))
    return g


# ══════════════════════════════════════════════════════════════════════════
#  Entry fields (Tk Entry with teal focus ring)
# ══════════════════════════════════════════════════════════════════════════

def entry_qss(P: dict) -> str:
    return f"""
        QLineEdit {{
            background:#ffffff; color:{P['text']};
            border:2px solid {P['btn_border']};
            selection-background-color:{P['accent_light']};
            selection-color:{P['text_white']};
            padding:2px 4px;
        }}
        QLineEdit:hover {{ border-color:{P['accent_light']}; }}
        QLineEdit:focus {{ border-color:{P['accent_teal']}; }}
    """


def make_entry(text: str = "", *, password: bool = False, chars: int = 20,
               font: Optional[QFont] = None, palette: Optional[dict] = None) -> QLineEdit:
    P = _palette(palette)
    e = QLineEdit(text)
    if password:
        e.setEchoMode(QLineEdit.EchoMode.Password)
    if font is not None:
        e.setFont(font)
        e.setFixedWidth(char_width(font, chars) + 16)
    e.setStyleSheet(entry_qss(P))
    return e


# ══════════════════════════════════════════════════════════════════════════
#  Themed dialog:  navy title strip  +  teal rule  +  body  +  footer strip
# ══════════════════════════════════════════════════════════════════════════

class ThemedDialog(QDialog):
    """
    Base class for the card-style popups (Configuration Settings, Security
    Options, Rack Setup, Direct/Network Connect, confirmations, help ...).

        dlg = ThemedDialog(parent, "Title", fonts=fonts, size=(500, 530))
        dlg.body_layout.addWidget(...)
        dlg.add_footer([...buttons...], align="center")
        dlg.exec()
    """

    def __init__(self, parent, title: str, *, fonts: Optional[dict] = None,
                 palette: Optional[dict] = None, size: Optional[tuple] = None,
                 header_text: Optional[str] = None, badge: bool = True,
                 title_pt: int = 11, body_margins=(16, 12, 16, 12),
                 title_bar_pad: int = 10):
        super().__init__(parent)
        self.setObjectName("vmsDialog")
        self.setWindowTitle(title)
        self.setModal(True)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self.fonts = fonts if isinstance(fonts, dict) else {}
        self.P = _palette(palette)
        self._size = size
        self.result_value = None

        self.setStyleSheet(f"QDialog#vmsDialog {{ background:{self.P['win_bg']}; }}")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Navy title strip ───────────────────────────────────────────
        bar = QWidget()
        bar.setStyleSheet(f"background:{self.P['titlebar']};")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, title_bar_pad, 0, title_bar_pad)
        bl.setSpacing(0)

        self.title_label = QLabel(f"  {header_text if header_text is not None else title}")
        self.title_label.setFont(pick_font(self.fonts, "ui_b", size=title_pt, bold=True))
        self.title_label.setStyleSheet(f"color:{self.P['text_white']}; background:transparent;")
        bl.addWidget(self.title_label, 1)

        if badge:
            b = QLabel("  VMS 3000  ")
            b.setFont(pick_font(self.fonts, "ui_b", size=10, bold=True))
            b.setStyleSheet(
                f"background:{self.P['accent_light']}; color:{self.P['text_white']};"
                " padding:4px 6px;"
            )
            bl.addWidget(b)
            bl.addSpacing(12)
        root.addWidget(bar)

        # ── Teal accent rule ───────────────────────────────────────────
        root.addWidget(hline(self.P["accent_teal"], 3))

        # ── Body ───────────────────────────────────────────────────────
        self.body = QWidget()
        self.body.setStyleSheet(
            f"QWidget {{ background:{self.P['win_bg']}; }}"
            f"QLabel {{ background:transparent; color:{self.P['text']}; }}"
            + entry_qss(self.P)
        )
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(*body_margins)
        self.body_layout.setSpacing(0)
        root.addWidget(self.body, 1)

        self._root = root

    # ------------------------------------------------------------------ #
    def add_footer(self, buttons: Iterable[QWidget], align: str = "center",
                   right_widget: Optional[QWidget] = None) -> QWidget:
        """Recessed strip with a hairline on top, holding the button row."""
        self._root.addWidget(hline(self.P["status_border"], 1))
        strip = QWidget()
        strip.setStyleSheet(f"background:{self.P['status_bg']};")
        h = QHBoxLayout(strip)
        h.setContentsMargins(16, 12, 16, 12)
        h.setSpacing(8)
        if align == "center":
            h.addStretch(1)
        for b in buttons:
            h.addWidget(b)
        if align == "center":
            h.addStretch(1)
        else:
            h.addStretch(1)
            if right_widget is not None:
                h.addWidget(right_widget)
        self._root.addWidget(strip)
        return strip

    def footer_button(self, text: str, cb: Callable, kind: str = "normal") -> QPushButton:
        return make_button(text, cb, kind, pick_font(self.fonts, "ui_b", size=9, bold=True),
                           self.P)

    # ------------------------------------------------------------------ #
    def finalize(self) -> None:
        """Apply the requested size (never smaller than the content) and centre."""
        if self._size:
            fixed_at_least(self, *self._size)
        else:
            self.adjustSize()
            self.setFixedSize(self.sizeHint())
        center_on_parent(self, self.parent())

    def show_modal(self):
        """Block until closed. Returns True if accepted."""
        self.finalize()
        return self.exec() == QDialog.DialogCode.Accepted


# ══════════════════════════════════════════════════════════════════════════
#  Read-only help window
# ══════════════════════════════════════════════════════════════════════════

def show_help_dialog(parent, title: str, text: str, size=(480, 400),
                     fonts: Optional[dict] = None, palette: Optional[dict] = None) -> None:
    dlg = ThemedDialog(parent, title, fonts=fonts, palette=palette, size=size,
                       badge=False, title_pt=10, title_bar_pad=9,
                       body_margins=(18, 14, 18, 14))
    lbl = QLabel(text)
    lbl.setFont(pick_font(fonts, "sm", size=9))
    lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
    lbl.setWordWrap(True)
    dlg.body_layout.addWidget(lbl, 1)
    dlg.body_layout.addSpacing(10)
    dlg.body_layout.addWidget(hline(dlg.P["status_border"], 1))
    dlg.body_layout.addSpacing(10)

    close = make_button("Close", dlg.accept, "primary",
                        pick_font(fonts, "ui_b", size=9, bold=True), dlg.P, pad="5px 14px")
    row = QHBoxLayout()
    row.addStretch(1)
    row.addWidget(close)
    row.addStretch(1)
    dlg.body_layout.addLayout(row)
    dlg.show_modal()


# ══════════════════════════════════════════════════════════════════════════
#  "Classic" raised-bevel controls (Proximity / Channel / 6M / Relay dialogs)
# ══════════════════════════════════════════════════════════════════════════

CLASSIC_BTN = {
    "btn_face": "#e7e9ec", "btn_hover": "#f2f4f6", "btn_press": "#cfd4da",
    "btn_border": "#5a5a5a", "btn_disabled_fg": "#8895a6", "text": "#000000",
}


def raised_button(text: str, callback: Optional[Callable] = None, *,
                  width_chars: Optional[int] = None, enabled: bool = True,
                  font: Optional[QFont] = None, colors: Optional[dict] = None) -> QPushButton:
    """Classic raised, beveled push button."""
    C = {**CLASSIC_BTN, **(colors or {})}
    b = QPushButton(text)
    if font is not None:
        b.setFont(font)
    b.setAutoDefault(False)
    b.setStyleSheet(f"""
        QPushButton {{
            background:{C['btn_face']}; color:{C['text']};
            border:2px solid {C['btn_border']};
            border-top-color:#ffffff; border-left-color:#ffffff;
            padding:2px 8px;
        }}
        QPushButton:hover   {{ background:{C['btn_hover']}; }}
        QPushButton:pressed {{
            background:{C['btn_press']};
            border-top-color:{C['btn_border']}; border-left-color:{C['btn_border']};
            border-bottom-color:#ffffff; border-right-color:#ffffff;
        }}
        QPushButton:disabled {{ color:{C['btn_disabled_fg']}; background:{C['btn_face']}; }}
    """)
    if width_chars is not None and font is not None:
        b.setMinimumWidth(char_width(font, width_chars) + 12)
    b.setEnabled(enabled)
    b.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
    if callback is not None:
        b.clicked.connect(lambda _c=False, cb=callback: cb())
    return b


class ClassicTitleBar(QWidget):
    """26px navy strip with the title on the left and a red ✕ on the right."""

    def __init__(self, title: str, on_close: Callable, font: QFont, close_font: QFont,
                 bg: str = "#1a3a5c", fg: str = "#ffffff", close_bg: str = "#c0392b"):
        super().__init__()
        self.setFixedHeight(26)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background:{bg};")
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 4, 0)
        h.setSpacing(0)
        lbl = QLabel(f"  {title}")
        lbl.setFont(font)
        lbl.setStyleSheet(f"color:{fg}; background:transparent;")
        h.addWidget(lbl, 1)
        x = QPushButton("\u2715")
        x.setFont(close_font)
        x.setFixedSize(30, 20)
        x.setCursor(Qt.CursorShape.PointingHandCursor)
        x.setStyleSheet(
            f"QPushButton {{ background:{close_bg}; color:#ffffff; border:1px outset {close_bg}; }}"
            f"QPushButton:pressed {{ border-style:inset; }}"
        )
        x.clicked.connect(lambda _c=False: on_close())
        h.addWidget(x)


def sunken_label(text: str, font: QFont, *, bg: str = "#eef1f5", fg: str = "#000000",
                 border: str = "#6b7280", chars: Optional[int] = None,
                 align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                 bold: bool = False, thin: bool = False) -> QLabel:
    """Flat sunken read-only display box (SLOT / RACK TYPE / CONFIGURATION ID)."""
    lbl = QLabel(text)
    f = QFont(font)
    if bold:
        f.setBold(True)
    lbl.setFont(f)
    lbl.setAlignment(align)
    style = "solid" if thin else "inset"
    bw = 1 if thin else 2
    lbl.setStyleSheet(
        f"QLabel {{ background:{bg}; color:{fg}; border:{bw}px {style} {border};"
        " padding:2px 4px; }"
    )
    if chars:
        lbl.setMinimumWidth(char_width(f, chars) + 14)
    return lbl


def plain_label(text: str, font: QFont, fg: str = "#000000", bg: str = "transparent",
                align=None) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(font)
    lbl.setStyleSheet(f"color:{fg}; background:{bg};")
    if align is not None:
        lbl.setAlignment(align)
    return lbl


def classic_combo_qss(bg: str, fg: str, border: str, arrow_bg: str = "#e7e9ec",
                      list_sel_bg: str = "#1a3a5c", list_sel_fg: str = "#ffffff",
                      arrow_color: str = "#000000") -> str:
    return f"""
        QComboBox {{
            background:{bg}; color:{fg}; border:1px solid {border};
            padding:3px 6px;
        }}
        QComboBox::drop-down {{ border-left:1px solid {border}; width:18px; background:{arrow_bg}; }}
        QComboBox::down-arrow {{ image:url({arrow_url(arrow_color)}); width:10px; height:8px; }}
        QComboBox QAbstractItemView {{
            background:#ffffff; color:#000000;
            selection-background-color:{list_sel_bg}; selection-color:{list_sel_fg};
        }}
    """


def ensure_qapp(argv=None) -> QApplication:
    """Return the running QApplication, creating (Fusion-styled) one if needed."""
    app = QApplication.instance()
    if app is None:
        import sys
        app = QApplication(argv if argv is not None else sys.argv)
        app.setStyle("Fusion")
    return app
