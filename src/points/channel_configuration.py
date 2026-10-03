"""
channel_configuration.py — VMS 3000  •  Channel-N Configuration dialog
(Transducer setup / Variables + Alarms)
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QStackedWidget, QTabBar, QVBoxLayout,
    QWidget,
)

from qt_common import (
    ClassicTitleBar, center_on_screen, checkbox_qss, field_palette, char_width, classic_combo_qss,
    fixed_at_least, pick_font, plain_label, raised_button, sunken_label,
)

# ══════════════════════════════════════════════════════════════════════════
#  PALETTE — kept consistent with proximiter12m_ridial.py / sixm_option.py
# ══════════════════════════════════════════════════════════════════════════

C = {
    "win_bg":          "#f0f0f0",
    "titlebar":        "#1a3a5c",
    "titlebar_text":   "#ffffff",
    "close_bg":        "#c0392b",

    "group_bg":        "#f0f0f0",
    "group_border":    "#8a8f98",
    "group_label":     "#000000",

    "field_bg":        "#eef1f5",
    "field_border":    "#6b7280",

    "combo_white_bg":  "#ffffff",
    "combo_white_fg":  "#1a3a8c",

    "btn_face":        "#e7e9ec",
    "btn_hover":       "#f2f4f6",
    "btn_press":       "#cfd4da",
    "btn_border":      "#5a5a5a",
    "btn_disabled_fg": "#8895a6",

    "tab_sel_bg":      "#f0f0f0",   # selected tab blends into the panel
    "tab_unsel_bg":    "#d7dbe0",   # unselected tab sits slightly "behind"
    "tab_border":      "#8a8f98",

    "text":            "#000000",
    "text_dim":        "#4a5568",

    "vms_logo":        "#17408a",
}

FONT_NAME = "Segoe UI"


def classic_group(title: str, font) -> QGroupBox:
    """Etched group box with a plain black bold title (classic look)."""
    g = QGroupBox(f" {title} ")
    g.setFont(font)
    g.setStyleSheet(f"""
        QGroupBox {{
            background:{C['group_bg']}; border:1px groove {C['group_border']};
            margin-top:9px; padding:10px 10px 8px 10px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin; subcontrol-position: top left;
            left:8px; padding:0 2px; color:{C['group_label']};
        }}
    """)
    return g


class ChannelConfigurationDialog:
    """Channel-N Configuration dialog (Transducer setup / Variables + Alarms)."""

    # ------------------------------------------------------------------ #
    #  Init                                                                #
    # ------------------------------------------------------------------ #

    def __init__(self, parent, channel_num, slot_num=6, fonts=None,
                 rack_type="", active=True, on_ok=None):
        self._parent = parent
        self._channel_num = channel_num
        self._slot_num = slot_num
        self._fonts = fonts if isinstance(fonts, dict) else {}
        self._rack_type = rack_type
        self._active = active
        self._dialog = None
        self._on_ok_callback = on_ok

    def _f(self, key, size=9, bold=False, italic=False, family=FONT_NAME):
        return pick_font(self._fonts, key, family, size, bold, italic)

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def show(self):
        d = QDialog(self._parent)
        self._dialog = d
        d.setObjectName("chanDlg")
        d.setWindowTitle(f"Channel-{self._channel_num} Configuration")
        d.setModal(True)
        d.setStyleSheet(f"QDialog#chanDlg {{ background:{C['win_bg']}; }}"
                        f"QLabel {{ background:transparent; }}"
                        + checkbox_qss(C['text']))

        root = QVBoxLayout(d)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(ClassicTitleBar(
            f"Channel-{self._channel_num} Configuration", self._on_cancel,
            self._f("title", 10, bold=True), self._f("close", 8),
        ))

        body = QVBoxLayout()
        body.setContentsMargins(14, 10, 14, 10)
        root.addLayout(body, 1)

        self._create_identity_row(body)
        self._create_tabs(body)
        self._create_buttons(body)

        self._tabbar.setCurrentIndex(1)     # "Variables + Alarms"

        d.adjustSize()
        d.setFixedSize(d.sizeHint())
        center_on_screen(d)
        d.exec()

    # ------------------------------------------------------------------ #
    #  Small widget helpers                                                #
    # ------------------------------------------------------------------ #

    def _lbl(self, text, bold=False, size=9, italic=False, fg=None, wrap=False):
        l = plain_label(text, self._f("label_b" if bold else "field", size, bold, italic),
                        fg or C["text"])
        l.setWordWrap(wrap)
        return l

    def _group(self, title):
        return classic_group(title, self._f("group", 9, bold=True))

    def _btn(self, text, cmd, width=None, enabled=True):
        return raised_button(text, cmd, width_chars=width, enabled=enabled,
                             font=self._f("field", 9), colors=C)

    def _combo(self, values, default, chars=20):
        cb = QComboBox()
        f = self._f("field", 9)
        cb.setFont(f)
        cb.addItems(values)
        cb.setCurrentText(default)
        cb.setStyleSheet(classic_combo_qss(C["combo_white_bg"], C["combo_white_fg"],
                                           C["field_border"], C["btn_face"],
                                           C["titlebar"], "#ffffff"))
        cb.setMinimumWidth(char_width(f, chars) + 28)
        return cb

    def _spinbox(self, value, chars=5, frm=-999, to=999):
        """Small numeric field (Clamp Value / Zero Position / Delay / etc.)."""
        sb = QDoubleSpinBox()
        text = str(value)
        sb.setDecimals(len(text.split(".")[1]) if "." in text else 0)
        sb.setRange(frm, to)
        sb.setSingleStep(1)
        sb.setValue(float(text))
        f = self._f("field", 9)
        sb.setFont(f)
        field_palette(sb, C["field_bg"], C["text"])
        sb.setFixedWidth(char_width(f, chars) + 34)
        return sb

    # ------------------------------------------------------------------ #
    #  Identity row — CHANNEL / 'ACTIVE' / SLOT / RACK TYPE                #
    # ------------------------------------------------------------------ #

    def _create_identity_row(self, parent):
        row = QHBoxLayout()
        row.setSpacing(0)

        row.addWidget(self._lbl("CHANNEL", bold=True))
        row.addSpacing(6)
        row.addWidget(sunken_label(str(self._channel_num), self._f("field", 9, True),
                                   bg=C["field_bg"], border=C["field_border"], chars=3,
                                   align=Qt.AlignmentFlag.AlignCenter))
        row.addSpacing(10)

        status = "'ACTIVE'" if self._active else "'INACTIVE'"
        row.addWidget(sunken_label(status, self._f("field", 9, True),
                                   bg=C["field_bg"], border=C["field_border"], chars=10,
                                   align=Qt.AlignmentFlag.AlignCenter))
        row.addSpacing(30)

        row.addWidget(self._lbl("SLOT", bold=True))
        row.addSpacing(6)
        row.addWidget(sunken_label(str(self._slot_num), self._f("field", 9),
                                   bg=C["field_bg"], border=C["field_border"], chars=6,
                                   align=Qt.AlignmentFlag.AlignCenter))
        row.addSpacing(30)

        row.addWidget(self._lbl("RACK TYPE", bold=True))
        row.addSpacing(6)
        row.addWidget(sunken_label(self._rack_type, self._f("field", 9),
                                   bg=C["field_bg"], border=C["field_border"], chars=16))
        row.addStretch(1)
        parent.addLayout(row)
        parent.addSpacing(8)

    # ------------------------------------------------------------------ #
    #  Tabs — real switching, not a "card"                                 #
    # ------------------------------------------------------------------ #

    def _create_tabs(self, parent):
        self._tabbar = QTabBar()
        self._tabbar.setDrawBase(False)
        self._tabbar.setFont(self._f("tab", 9))
        self._tabbar.addTab("Transducer setup")
        self._tabbar.addTab("Variables + Alarms")
        self._tabbar.setStyleSheet(f"""
            QTabBar::tab {{
                background:{C['tab_unsel_bg']}; color:{C['text']};
                border:1px outset {C['tab_border']}; padding:4px 10px; margin-right:2px;
            }}
            QTabBar::tab:selected {{
                background:{C['tab_sel_bg']}; font-weight:bold;
                border:1px solid {C['tab_border']}; border-bottom-color:{C['tab_sel_bg']};
            }}
        """)
        parent.addWidget(self._tabbar)

        # Both panels occupy the same cell; selecting a tab swaps the page.
        stack = QStackedWidget()
        t = QWidget()
        self._build_transducer_setup_tab(t)
        v = QWidget()
        self._build_variables_alarms_tab(v)
        stack.addWidget(t)
        stack.addWidget(v)
        # size to the larger page so the dialog doesn't jump between tabs
        stack.setSizePolicy(stack.sizePolicy().horizontalPolicy(),
                            stack.sizePolicy().verticalPolicy())
        parent.addWidget(stack, 1)
        self._tabbar.currentChanged.connect(stack.setCurrentIndex)
        self._stack = stack

    # ------------------------------------------------------------------ #
    #  "Variables + Alarms" tab                                            #
    # ------------------------------------------------------------------ #

    def _build_variables_alarms_tab(self, page):
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 8)
        panel = self._group("Variables + Alarm")
        lay.addWidget(panel)
        pl = QVBoxLayout(panel)
        pl.setSpacing(4)

        top = QHBoxLayout()
        pl.addLayout(top)

        # ---- Enable: Full Scale Range / Clamp Value for Direct & Gap ----
        enable = self._group("Enable")
        top.addWidget(enable, 1)
        grid = QGridLayout(enable)
        grid.setHorizontalSpacing(12)

        grid.addWidget(self._lbl("Full Scale Range", bold=True), 0, 1)
        grid.addWidget(self._lbl("Clamp Value", bold=True), 0, 2)

        direct_scale_values = [
            "0-10 mil pp", "0-15 mil pp", "0-20 mil pp", "0-100 mil pp",
            "0-150 \u00b5m pp", "0-200 \u00b5m pp", "0-400 \u00b5m pp", "0-500 \u00b5m pp",
        ]
        # Gap "full scale range" is a DC bias-voltage range rather than a
        # mil/µm span, so a plausible preset list is used.
        gap_scale_values = ["-24Vdc", "-20Vdc", "-18Vdc", "-16Vdc", "-12Vdc", "-10Vdc", "-8Vdc"]

        self._direct_row = self._build_enable_row(
            grid, 1, "Direct", direct_scale_values, "0-10 mil pp", "0")
        self._gap_row = self._build_enable_row(
            grid, 2, "Gap", gap_scale_values, "-24Vdc", "0")

        # ---- Zero Position (Gap) ----
        zero = self._group("Zero Position")
        top.addWidget(zero)
        zl = QVBoxLayout(zero)
        zrow = QHBoxLayout()
        zrow.addWidget(self._lbl("Zero Position\n(Gap)"))
        zrow.addSpacing(8)
        self._zero_spin = self._spinbox("-9.75", chars=6)
        zrow.addWidget(self._zero_spin)
        zrow.addSpacing(4)
        zrow.addWidget(self._lbl("Volts"))
        zl.addLayout(zrow)
        zl.addWidget(self._btn("Adjust", None, width=12, enabled=False),
                     0, Qt.AlignmentFlag.AlignHCenter)

        # ---- Alert Latching / Danger Latching ----
        latch = QHBoxLayout()
        latch.setContentsMargins(0, 8, 0, 4)
        self._alert_latch = QCheckBox("Alert Latching")
        self._alert_latch.setFont(self._f("field", 9))
        self._danger_latch = QCheckBox("Danger Latching")
        self._danger_latch.setFont(self._f("field", 9))
        latch.addWidget(self._alert_latch)
        latch.addSpacing(30)
        latch.addWidget(self._danger_latch)
        latch.addStretch(1)
        pl.addLayout(latch)

        # ---- Delay / Trip Multiply ----
        mid = QHBoxLayout()
        pl.addLayout(mid)

        delay = self._group("Delay")
        mid.addWidget(delay, 1)
        dl = QVBoxLayout(delay)
        for name, val, hint in (("Alert", "3", "1 - 60 s"), ("Danger", "1", "1.0 - 60.0")):
            r = QHBoxLayout()
            l = self._lbl(name)
            l.setFixedWidth(char_width(self._f("field", 9), 7))
            r.addWidget(l)
            r.addWidget(self._spinbox(val, chars=4))
            r.addSpacing(6)
            r.addWidget(self._lbl(hint))
            r.addStretch(1)
            dl.addLayout(r)

        trip = self._group("Trip Multiply")
        mid.addWidget(trip)
        tl = QHBoxLayout(trip)
        tl.addWidget(self._spinbox("1", chars=4))
        tl.addSpacing(6)
        tl.addWidget(self._lbl("1 to 3 (Step of\n0.25)"))

        # ---- Recorder Output ----
        rec = self._group("Recorder Output")
        pl.addWidget(rec)
        rl = QHBoxLayout(rec)
        rl.addWidget(self._combo(["NONE", "Recorder 1", "Recorder 2"], "NONE", 20))
        rl.addStretch(1)

    def _build_enable_row(self, grid, row, label, scale_values, scale_default, clamp_default):
        l = self._lbl(label)
        l.setFixedWidth(char_width(self._f("field", 9), 7))
        grid.addWidget(l, row, 0)
        scale_combo = self._combo(scale_values, scale_default, 14)
        grid.addWidget(scale_combo, row, 1)
        clamp_spin = self._spinbox(clamp_default, chars=5)
        grid.addWidget(clamp_spin, row, 2)
        return scale_combo, clamp_spin

    # ------------------------------------------------------------------ #
    #  "Transducer setup" tab — placeholder (not shown in screenshots)    #
    # ------------------------------------------------------------------ #

    def _build_transducer_setup_tab(self, page):
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 8)
        panel = self._group("Transducer Setup")
        lay.addWidget(panel)
        pl = QVBoxLayout(panel)

        pl.addWidget(self._lbl(
            "Transducer setup fields were not visible in the reference\n"
            "screenshots (both were captured on the Variables + Alarms tab).\n"
            "Placeholder fields are shown below — replace with the real\n"
            "labels/values whenever available.",
            size=8, italic=True, fg=C["text_dim"]))
        pl.addSpacing(10)

        grid = QGridLayout()
        pl.addLayout(grid)
        pl.addStretch(1)

        rows = [
            ("Transducer Type", ["Standard Proximitor", "Reverse Mount", "Extended Range"], "Standard Proximitor"),
            ("Probe Type", ["5 mm", "8 mm", "11 mm"], "8 mm"),
            ("Extension Cable Length", ["1 m", "3 m", "5 m", "9 m"], "5 m"),
            ("Sensitivity", ["100 mV/mil", "200 mV/mil", "7.87 mV/\u00b5m"], "200 mV/mil"),
        ]
        for r, (label, values, default) in enumerate(rows):
            l = self._lbl(label)
            l.setFixedWidth(char_width(self._f("field", 9), 20))
            grid.addWidget(l, r, 0)
            grid.addWidget(self._combo(values, default, 20), r, 1)
        grid.setColumnStretch(2, 1)

    # ------------------------------------------------------------------ #
    #  Bottom button bar                                                   #
    # ------------------------------------------------------------------ #

    def _create_buttons(self, parent):
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 4, 0, 0)

        bar.addWidget(self._btn("Ok", self._on_ok, width=10))
        bar.addSpacing(8)
        bar.addWidget(self._btn("Set defaults", self._on_set_defaults, width=12))
        bar.addSpacing(8)
        bar.addWidget(self._btn("Cancel", self._on_cancel, width=10))
        bar.addSpacing(40)
        bar.addWidget(self._btn("Print", self._on_print, width=10))
        bar.addSpacing(8)
        bar.addWidget(self._btn("Help", self._on_help, width=10))
        bar.addStretch(1)

        logo = QLabel("VMS 3000")
        logo.setFont(self._f("logo", 15, bold=True, italic=True))
        logo.setStyleSheet(f"color:{C['vms_logo']}; background:transparent;")
        bar.addWidget(logo)
        parent.addLayout(bar)

    # ------------------------------------------------------------------ #
    #  Handlers                                                            #
    # ------------------------------------------------------------------ #

    def _on_ok(self):
        print("OK pressed")
        if self._on_ok_callback:
            self._on_ok_callback(self._channel_num)
        self._dialog.accept()

    def _on_set_defaults(self):
        print("Set defaults pressed")

    def _on_cancel(self):
        self._dialog.reject()

    def _on_print(self):
        print("Print pressed")

    def _on_help(self):
        print("Help pressed")


# ══════════════════════════════════════════════════════════════════════
#  Standalone preview
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    from qt_common import ensure_qapp

    app = ensure_qapp()
    ChannelConfigurationDialog(None, 1, slot_num=10, rack_type="", active=True).show()
