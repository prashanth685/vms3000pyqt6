"""
proximiter12m_ridial.py — VMS 3000
Proximity Monitor 3000 Configuration Dialog (Proximeter I/O Module)

Visual match to the reference screenshot:
  - pale steel-blue window background, dark navy titlebar
  - flat sunken display fields for SLOT / RACK TYPE / CONFIGURATION ID
  - classic raised, beveled buttons (Ok, Options, Copy, arrows, etc.)
  - "Channel Pair Type" combobox shown with the navy highlighted look
  - bold blue-navy italic "VMS 3000" logo, bottom right
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QGridLayout, QHBoxLayout, QLabel,
    QVBoxLayout, QWidget,
)

from qt_common import (
    ClassicTitleBar, center_on_screen, checkbox_qss, classic_combo_qss, pick_font,
    plain_label, raised_button, sunken_label,
)
from points.channel_configuration import ChannelConfigurationDialog, classic_group

# ══════════════════════════════════════════════════════════════════════════
#  PALETTE — colours matched from the reference screenshot
# ══════════════════════════════════════════════════════════════════════════

C = {
    "win_bg":          "#f0f0f0",
    "titlebar":        "#1a3a5c",
    "titlebar_text":   "#ffffff",
    "close_bg":        "#c0392b",

    "group_bg":        "#f0f0f0",
    "group_border":    "#8a8f98",
    "group_label":     "#000000",

    "field_bg":        "#eef1f5",   # SLOT / RACK TYPE / CONFIG ID display box
    "field_border":    "#6b7280",

    "combo_white_bg":  "#ffffff",   # Slot I/O Module Type dropdown
    "combo_white_fg":  "#1a3a8c",

    "combo_sel_bg":    "#1a3a5c",   # highlighted "Radial Vibration" look
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


class ProximityMonitor3000ConfigDialog:
    """Configuration dialog for a Proximeter I/O Module (VMS 3000 DIS_MODULE)."""

    def __init__(self, parent, slot_num=6, fonts=None,
                 rack_type="VMM/12T/DISP", config_id="", model="12M/DIS"):
        self._parent = parent
        self._slot_num = slot_num
        self._fonts = fonts if isinstance(fonts, dict) else {}
        self._rack_type = rack_type
        self._config_id = config_id
        self._model = model  # "12M/DIS" or "6M"
        self._dialog = None

        # Track which channels have been configured
        self._configured_channels = set()

        # Copy-button references for enable/disable, keyed "A_to_B"
        self._copy_buttons = {}

    def _f(self, key, size=9, bold=False, italic=False, family=FONT_NAME):
        return pick_font(self._fonts, key, family, size, bold, italic)

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def show(self):
        d = QDialog(self._parent)
        self._dialog = d
        d.setObjectName("proxDlg")
        d.setWindowTitle("Proximity Monitor 3000 Configuration")
        d.setModal(True)
        d.setStyleSheet(f"QDialog#proxDlg {{ background:{C['win_bg']}; }}"
                        f"QLabel {{ background:transparent; }}"
                        + checkbox_qss(C['text']))

        root = QVBoxLayout(d)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(ClassicTitleBar(
            "Proximity Monitor 3000 Configuration", self._on_cancel,
            self._f("title", 10, bold=True), self._f("close", 8)))

        body = QVBoxLayout()
        body.setContentsMargins(14, 10, 14, 10)
        root.addLayout(body, 1)

        self._create_identity_row(body)

        # Both models currently show 2 channel pairs (1-2 and 3-4)
        num_pairs = 2
        columns = 2

        pairs = QGridLayout()
        pairs.setHorizontalSpacing(16)
        pairs.setVerticalSpacing(8)
        body.addSpacing(10)
        body.addLayout(pairs, 1)
        for c in range(columns):
            pairs.setColumnStretch(c, 1)

        for pair_idx in range(num_pairs):
            ch_a, ch_b = pair_idx * 2 + 1, pair_idx * 2 + 2
            grp = self._build_channel_pair_group(
                f"Channel Pair {ch_a} and {ch_b}",
                f"Channel {ch_a}", f"Channel {ch_b}", ch_a, ch_b)
            pairs.addWidget(grp, pair_idx // columns, pair_idx % columns)

        self._create_buttons(body)

        d.adjustSize()
        hint = d.sizeHint()
        d.setFixedSize(max(960, hint.width()), hint.height())
        center_on_screen(d)
        d.exec()

    # ------------------------------------------------------------------ #
    #  Small helpers                                                       #
    # ------------------------------------------------------------------ #

    def _lbl(self, text, bold=False):
        return plain_label(text, self._f("label_b" if bold else "field", 9, bold), C["text"])

    def _group(self, title):
        return classic_group(title, self._f("group", 9, bold=True))

    def _btn(self, text, cmd, width=None, enabled=True):
        return raised_button(text, cmd, width_chars=width, enabled=enabled,
                             font=self._f("field", 9), colors=C)

    def _combo_white(self):
        qss = classic_combo_qss(C["combo_white_bg"], C["combo_white_fg"], C["field_border"],
                                C["btn_face"], C["titlebar"], "#ffffff")
        return qss

    def _combo_selected(self):
        return classic_combo_qss(C["combo_sel_bg"], C["combo_sel_fg"], C["field_border"],
                                 C["btn_face"], C["titlebar"], "#ffffff")

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
            cell.addWidget(self._lbl(label, bold=True))
            cell.addWidget(sunken_label(value, self._f("field", 9), bg=C["field_bg"],
                                        border=C["field_border"], chars=chars),
                           0, Qt.AlignmentFlag.AlignLeft)
            cell.addStretch(1)
            row.addLayout(cell)
            row.addSpacing(16)

        row.addSpacing(14)
        right = self._group("Slot Input / Output Module Type")
        rl = QVBoxLayout(right)
        combo = QComboBox()
        combo.setFont(self._f("field", 9))
        combo.addItem("Proximeter I/O Module")
        combo.setStyleSheet(self._combo_white())
        rl.addWidget(combo)
        row.addWidget(right, 1)

    # ------------------------------------------------------------------ #
    #  Channel Pair group                                                  #
    # ------------------------------------------------------------------ #

    def _build_channel_pair_group(self, title, ch_a_name, ch_b_name, ch_a_num, ch_b_num):
        group = self._group(title)
        gl = QVBoxLayout(group)

        gl.addWidget(self._lbl("Channel Pair Type", bold=True), 0, Qt.AlignmentFlag.AlignRight)

        pair_type = QComboBox()
        pair_type.setFont(self._f("field", 9))
        pair_type.addItems(["Radial Vibration", "Axial Vibration", "Thrust Position", "Not Used"])
        pair_type.setStyleSheet(self._combo_selected())
        gl.addWidget(pair_type)
        gl.addSpacing(4)

        body = QHBoxLayout()
        gl.addLayout(body, 1)

        body.addWidget(self._build_channel_box(ch_a_name, ch_a_num), 1)

        mid = QVBoxLayout()
        mid.addSpacing(28)
        copy_a_to_b = self._btn("\u21d2", lambda: self._on_copy(ch_a_num, ch_b_num),
                                width=3, enabled=False)
        mid.addWidget(copy_a_to_b)
        mid.addSpacing(4)
        mid.addWidget(self._btn("Copy", None, width=8))
        mid.addSpacing(4)
        copy_b_to_a = self._btn("\u21d0", lambda: self._on_copy(ch_b_num, ch_a_num),
                                width=3, enabled=False)
        mid.addWidget(copy_b_to_a)
        mid.addStretch(1)
        body.addSpacing(8)
        body.addLayout(mid)
        body.addSpacing(8)

        self._copy_buttons[f"{ch_a_num}_to_{ch_b_num}"] = copy_a_to_b
        self._copy_buttons[f"{ch_b_num}_to_{ch_a_num}"] = copy_b_to_a

        body.addWidget(self._build_channel_box(ch_b_name, ch_b_num), 1)

        arrows = QVBoxLayout()
        arrows.setContentsMargins(0, 2, 0, 0)
        arrows.addWidget(self._btn("\u21d2", None, width=3), 0, Qt.AlignmentFlag.AlignHCenter)
        arrows.addWidget(self._btn("\u21d0", None, width=3, enabled=False), 0, Qt.AlignmentFlag.AlignHCenter)
        gl.addLayout(arrows)
        return group

    def _build_channel_box(self, name, channel_num):
        box = self._group(name)
        bl = QVBoxLayout(box)

        chk = QCheckBox("Active")
        chk.setFont(self._f("field", 9))
        chk.setChecked(True)
        bl.addWidget(chk)
        bl.addSpacing(8)

        options_btn = self._btn("Options", None, width=10)
        options_btn.clicked.connect(lambda _c=False: self._on_options(channel_num, chk))
        bl.addWidget(options_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        bl.addStretch(1)

        base_qss = box.styleSheet()

        def _apply_active_state(*_):
            """Grey out the whole channel box (title, checkbox label,
            Options button) when Active is unchecked."""
            active = chk.isChecked()
            color = C["text"] if active else C["btn_disabled_fg"]
            box.setStyleSheet(base_qss + f"QGroupBox::title {{ color:{color}; }}")
            chk.setStyleSheet(checkbox_qss(color))
            options_btn.setEnabled(active)
            options_btn.setCursor(Qt.CursorShape.PointingHandCursor if active
                                  else Qt.CursorShape.ArrowCursor)

        chk.toggled.connect(_apply_active_state)
        _apply_active_state()
        return box

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
        def on_channel_config_ok(configured_channel):
            self._configured_channels.add(configured_channel)
            self._update_copy_buttons()

        dialog = ChannelConfigurationDialog(
            self._dialog,
            channel_num,
            slot_num=self._slot_num,
            fonts=self._fonts,
            rack_type=self._rack_type,
            active=active_chk.isChecked() if active_chk is not None else True,
            on_ok=on_channel_config_ok,
        )
        dialog.show()

    def _update_copy_buttons(self):
        """Enable copy buttons whose source channel has been configured."""
        for button_key, button in self._copy_buttons.items():
            if button is None:
                continue
            source_channel = int(button_key.split("_")[0])
            if source_channel in self._configured_channels:
                button.setEnabled(True)
                button.setCursor(Qt.CursorShape.PointingHandCursor)

    def _on_copy(self, from_channel, to_channel):
        """Copy configuration from one channel to another."""
        print(f"Copying configuration from Channel {from_channel} to Channel {to_channel}")
        # TODO: Implement actual configuration data copying.
        # For now, just mark the destination as configured.
        self._configured_channels.add(to_channel)
        self._update_copy_buttons()

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
    ProximityMonitor3000ConfigDialog(None, 6).show()   # (parent, slot_num)
