"""
sixm_option.py — VMS 3000  •  3000/6M Options Configuration Dialog

Visual match to the "Proximity Monitor 3000 Configuration" reference screenshot,
adapted for the 3000/6M module:
  - pale steel-grey window background, dark navy titlebar with red close button
  - flat, thin-bordered white display fields for SLOT / RACK TYPE / CONFIGURATION ID
    (no group-box borders — every section header is a plain bold label sitting
    above its control)
  - "Channel Pair Type" — bold label right-aligned above a full-width, solid navy
    combobox bar with white text
  - Channel boxes — bold label above a thin rectangular border containing an
    "Active" checkbox and an "Options" button
  - classic raised, beveled buttons
  - bold blue-navy italic "VMS 3000" logo, bottom right
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QVBoxLayout,
    QWidget,
)

from qt_common import (
    ClassicTitleBar, center_on_screen, checkbox_qss, classic_combo_qss, pick_font,
    plain_label, raised_button, sunken_label, vline,
)
from points.channel_configuration import ChannelConfigurationDialog

# ══════════════════════════════════════════════════════════════════════════
#  PALETTE — colours matched from the reference screenshot
# ══════════════════════════════════════════════════════════════════════════

C = {
    "win_bg":          "#f0f0f0",
    "titlebar":        "#1a3a5c",
    "titlebar_text":   "#ffffff",
    "close_bg":        "#c0392b",

    "group_label":     "#000000",

    "field_bg":        "#ffffff",   # SLOT / RACK TYPE / CONFIG ID display box
    "field_border":    "#8a8f98",

    "box_bg":          "#f0f0f0",   # Channel N thin-border box background
    "box_border":      "#8a8f98",

    "combo_white_bg":  "#ffffff",
    "combo_white_fg":  "#1a3a8c",

    "combo_sel_bg":    "#1a3a5c",   # full-width navy "Channel Pair Type" bar
    "combo_sel_fg":    "#ffffff",

    "btn_face":        "#e7e9ec",
    "btn_hover":       "#f2f4f6",
    "btn_press":       "#cfd4da",
    "btn_border":      "#5a5a5a",
    "btn_disabled_fg": "#8895a6",

    "text":            "#000000",
    "text_dim":        "#4a5568",

    "vms_logo":        "#17408a",
}

FONT_NAME = "Segoe UI"


class SixMOptionsDialog:
    """Configuration dialog for a 3000/6M Module (VMS 3000)."""

    def __init__(self, parent, slot_num=6, fonts=None,
                 rack_type="VMM/6M/DISP", config_id=""):
        self._parent = parent
        self._slot_num = slot_num
        self._fonts = fonts if isinstance(fonts, dict) else {}
        self._rack_type = rack_type
        self._config_id = config_id
        self._dialog = None

    def _f(self, key, size=9, bold=False, italic=False, family=FONT_NAME):
        return pick_font(self._fonts, key, family, size, bold, italic)

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def show(self):
        d = QDialog(self._parent)
        self._dialog = d
        d.setObjectName("sixmDlg")
        d.setWindowTitle("3000/6M Options Configuration")
        d.setModal(True)
        d.setStyleSheet(f"QDialog#sixmDlg {{ background:{C['win_bg']}; }}"
                        f"QLabel {{ background:transparent; }}"
                        + checkbox_qss(C['text']))

        root = QVBoxLayout(d)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(ClassicTitleBar(
            "3000/6M Options Configuration", self._on_cancel,
            self._f("title", 11, bold=True), self._f("close", 8)))

        body = QVBoxLayout()
        body.setContentsMargins(14, 10, 14, 10)
        root.addLayout(body, 1)

        self._create_identity_row(body)

        pair_row = QHBoxLayout()
        pair_row.setContentsMargins(0, 14, 0, 0)
        body.addLayout(pair_row, 1)
        pair_row.addWidget(self._build_channel_pair_group(
            "Channel Pair 1 and 2", "Channel 1", "Channel 2", 1, 2), 1)
        pair_row.addSpacing(10)
        pair_row.addWidget(vline(C["box_border"], 1))
        pair_row.addSpacing(10)
        pair_row.addWidget(self._build_channel_pair_group(
            "Channel Pair 3 and 4", "Channel 3", "Channel 4", 3, 4), 1)

        self._create_buttons(body)

        d.adjustSize()
        hint = d.sizeHint()
        d.setFixedSize(max(960, hint.width()), hint.height())
        center_on_screen(d)
        d.exec()

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _section_label(self, title, align=Qt.AlignmentFlag.AlignLeft):
        """Section header — bold plain label, NOT a group-box border."""
        return plain_label(title, self._f("label_b", 9, True), C["group_label"],
                           align=align | Qt.AlignmentFlag.AlignVCenter)

    def _btn(self, text, cmd, width=None, enabled=True):
        return raised_button(text, cmd, width_chars=width, enabled=enabled,
                             font=self._f("field", 9), colors=C)

    # ------------------------------------------------------------------ #
    #  Identity row                                                        #
    # ------------------------------------------------------------------ #

    def _create_identity_row(self, parent):
        row = QHBoxLayout()
        parent.addLayout(row)

        for label, value, chars in (
            ("SLOT:", str(self._slot_num), 5),
            ("RACK TYPE:", self._rack_type, 14),
            ("CONFIGURATION ID:", self._config_id, 14),
        ):
            cell = QVBoxLayout()
            cell.setSpacing(2)
            cell.addWidget(plain_label(label, self._f("label_b", 9, True), C["text"]))
            # flat, thin-bordered white box — matches the reference
            cell.addWidget(sunken_label(value, self._f("field", 9), bg=C["field_bg"],
                                        border=C["field_border"], chars=chars, thin=True),
                           0, Qt.AlignmentFlag.AlignLeft)
            cell.addStretch(1)
            row.addLayout(cell)
            row.addSpacing(16)

        row.addSpacing(14)
        right = QVBoxLayout()
        right.setSpacing(2)
        right.addWidget(self._section_label("Slot Input / Output Module Type"))
        combo = QComboBox()
        combo.setFont(self._f("field", 9))
        combo.addItem("3000/6M Module")
        combo.setStyleSheet(classic_combo_qss(C["combo_white_bg"], C["combo_white_fg"],
                                              C["field_border"], C["btn_face"],
                                              C["titlebar"], "#ffffff"))
        right.addWidget(combo)
        right.addStretch(1)
        row.addLayout(right, 1)

    # ------------------------------------------------------------------ #
    #  Channel Pair group                                                  #
    # ------------------------------------------------------------------ #

    def _build_channel_pair_group(self, title, ch_a_name, ch_b_name, ch_a_num, ch_b_num):
        group = QWidget()
        gl = QVBoxLayout(group)
        gl.setContentsMargins(0, 0, 0, 0)

        # Header row: pair title (left) + "Channel Pair Type" (right)
        header = QHBoxLayout()
        header.addWidget(self._section_label(title))
        header.addStretch(1)
        header.addWidget(self._section_label("Channel Pair Type", Qt.AlignmentFlag.AlignRight))
        gl.addLayout(header)

        # Full-width solid-navy combobox bar
        pair_type = QComboBox()
        pair_type.setFont(self._f("field", 9))
        pair_type.addItems(["Radial Vibration", "Axial Vibration", "Thrust Position", "Not Used"])
        pair_type.setStyleSheet(classic_combo_qss(C["combo_sel_bg"], C["combo_sel_fg"],
                                                  C["field_border"], C["combo_sel_bg"],
                                                  C["titlebar"], "#ffffff", "#ffffff")
                                + "QComboBox { padding:4px 6px; }")
        gl.addWidget(pair_type)
        gl.addSpacing(6)

        body = QHBoxLayout()
        gl.addLayout(body, 1)
        body.addWidget(self._build_channel_box(ch_a_name, ch_a_num), 1)

        mid = QVBoxLayout()
        mid.addSpacing(28)
        mid.addWidget(self._btn("\u21d2", None, width=3, enabled=False))
        mid.addSpacing(4)
        mid.addWidget(self._btn("Copy", None, width=8))
        mid.addSpacing(4)
        mid.addWidget(self._btn("\u21d0", None, width=3, enabled=False))
        mid.addStretch(1)
        body.addSpacing(8)
        body.addLayout(mid)
        body.addSpacing(8)

        body.addWidget(self._build_channel_box(ch_b_name, ch_b_num), 1)

        arrows = QVBoxLayout()
        arrows.setContentsMargins(0, 6, 0, 0)
        arrows.addWidget(self._btn("\u21d2", None, width=3, enabled=False),
                         0, Qt.AlignmentFlag.AlignHCenter)
        arrows.addWidget(self._btn("\u21d0", None, width=3, enabled=False),
                         0, Qt.AlignmentFlag.AlignHCenter)
        gl.addLayout(arrows)
        return group

    def _build_channel_box(self, name, channel_num):
        """Bold label above a thin rectangular border (label sits outside it)."""
        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(4)

        name_label = self._section_label(name)
        wl.addWidget(name_label)

        box = QFrame()
        box.setStyleSheet(
            f"QFrame#chBox {{ background:{C['box_bg']}; border:1px solid {C['box_border']}; }}"
        )
        box.setObjectName("chBox")
        bl = QVBoxLayout(box)
        bl.setContentsMargins(10, 10, 10, 10)
        wl.addWidget(box, 1)

        chk = QCheckBox("Active")
        chk.setFont(self._f("field", 9))
        chk.setChecked(True)
        bl.addWidget(chk)
        bl.addSpacing(8)

        options_btn = self._btn("Options", None, width=10)
        options_btn.clicked.connect(lambda _c=False: self._on_options(channel_num, chk))
        bl.addWidget(options_btn, 0, Qt.AlignmentFlag.AlignLeft)
        bl.addStretch(1)

        def _apply_active_state(*_):
            """Grey out title, checkbox label and Options button when inactive."""
            active = chk.isChecked()
            color = C["text"] if active else C["btn_disabled_fg"]
            name_label.setStyleSheet(f"color:{color}; background:transparent;")
            chk.setStyleSheet(checkbox_qss(color))
            options_btn.setEnabled(active)
            options_btn.setCursor(Qt.CursorShape.PointingHandCursor if active
                                  else Qt.CursorShape.ArrowCursor)

        chk.toggled.connect(_apply_active_state)
        _apply_active_state()
        return wrap

    # ------------------------------------------------------------------ #
    #  Bottom button bar                                                   #
    # ------------------------------------------------------------------ #

    def _create_buttons(self, parent):
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 12, 0, 0)
        bar.addWidget(self._btn("Ok", self._on_ok, width=10))
        bar.addSpacing(8)
        bar.addWidget(self._btn("Set defaults", self._on_set_defaults, width=12))
        bar.addSpacing(8)
        bar.addWidget(self._btn("Cancel", self._on_cancel, width=10))
        bar.addSpacing(60)
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

    def _on_options(self, channel_num, active_chk=None):
        """Open the Channel-N Configuration dialog for the given channel."""
        dialog = ChannelConfigurationDialog(
            self._dialog,
            channel_num,
            slot_num=self._slot_num,
            fonts=self._fonts,
            rack_type=self._rack_type,
            active=active_chk.isChecked() if active_chk is not None else True,
        )
        dialog.show()

    def _on_ok(self):
        print("OK pressed")
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
    SixMOptionsDialog(None, 6).show()   # (parent, slot_num)
