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
    center_on_screen, checkbox_qss, classic_combo_qss, pick_font,
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
    "combo_white_fg":  "#000000",

    "combo_sel_bg":    "#ffffff",
    "combo_sel_fg":    "#000000",


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

        # Channel Pair Type references for copying
        self._pair_type_combos = {}

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

        # Store reference to pair type combo for this channel pair
        self._pair_type_combos[f"{ch_a_num}_{ch_b_num}"] = pair_type

        body = QHBoxLayout()
        gl.addLayout(body, 1)

        # Left arrow before Channel A (for pairs 3-4) - copies from pair 3-4 to pair 1-2
        if ch_a_num >= 3:
            left_arrow = self._btn("\u21d0", lambda: self._on_copy_pair_to_pair(3, 1),
                                   width=3, enabled=False)
            body.addWidget(left_arrow)
            # Store with suffix to track separately
            self._copy_buttons[f"{ch_b_num}_to_{ch_a_num}_left"] = left_arrow
            body.addSpacing(8)

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

        # Store copy buttons (only if not already stored)
        if f"{ch_a_num}_to_{ch_b_num}" not in self._copy_buttons:
            self._copy_buttons[f"{ch_a_num}_to_{ch_b_num}"] = copy_a_to_b
        if f"{ch_b_num}_to_{ch_a_num}" not in self._copy_buttons:
            self._copy_buttons[f"{ch_b_num}_to_{ch_a_num}"] = copy_b_to_a

        body.addWidget(self._build_channel_box(ch_b_name, ch_b_num), 1)

        # Right arrow after Channel B (only for pair 1-2) - copies to pair 3-4
        if ch_a_num < 3:
            right_arrow = self._btn("\u21d2", lambda: self._on_copy_pair_to_pair(1, 3),
                                    width=3, enabled=False)
            body.addSpacing(8)
            body.addWidget(right_arrow)
            # Store right arrow reference for updating
            if f"{ch_a_num}_to_{ch_b_num}_right" not in self._copy_buttons:
                self._copy_buttons[f"{ch_a_num}_to_{ch_b_num}_right"] = right_arrow

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

            # Save the Channel Pair Type for this channel's pair
            pair_key = self._get_pair_key(channel_num)
            if pair_key in self._pair_type_combos:
                pair_type = self._pair_type_combos[pair_key].currentText()
                # Store pair type in the channel config
                config = ChannelConfigurationDialog.get_channel_config(channel_num)
                if config:
                    config["pair_type"] = pair_type
                    ChannelConfigurationDialog._channel_configs[channel_num] = config

            self._update_copy_buttons()

        dialog = ChannelConfigurationDialog(
            self._dialog,
            channel_num,
            slot_num=self._slot_num,
            fonts=self._fonts,
            rack_type=self._rack_type,
            active=active_chk.isChecked() if active_chk is not None else True,
            on_ok=on_channel_config_ok,
            model=self._model,
            load_existing=True,  # Load existing configuration if available
        )
        dialog.show()

    def _update_copy_buttons(self):
        """Enable copy buttons whose source channel has been configured."""
        for button_key, button in self._copy_buttons.items():
            if button is None:
                continue
            # Extract the base key (remove _right or _left suffix)
            base_key = button_key.replace("_right", "").replace("_left", "")
            # Skip duplicate entries (we'll process the base key and update all variants)
            if button_key != base_key:
                continue
            source_channel = int(button_key.split("_")[0])
            if source_channel in self._configured_channels:
                # Enable the main button (middle button)
                button.setEnabled(True)
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                # Also enable the corresponding right arrow button
                right_key = f"{button_key}_right"
                if right_key in self._copy_buttons:
                    self._copy_buttons[right_key].setEnabled(True)
                    self._copy_buttons[right_key].setCursor(Qt.CursorShape.PointingHandCursor)
                # Also enable the corresponding left arrow button (if exists)
                left_key = f"{button_key}_left"
                if left_key in self._copy_buttons:
                    self._copy_buttons[left_key].setEnabled(True)
                    self._copy_buttons[left_key].setCursor(Qt.CursorShape.PointingHandCursor)

        # Enable cross-pair arrows when the entire source pair is configured
        # Enable right arrow for pair 1->3 (after Channel 2) when both channels 1 and 2 are configured
        if 1 in self._configured_channels and 2 in self._configured_channels:
            if "1_to_2_right" in self._copy_buttons:
                self._copy_buttons["1_to_2_right"].setEnabled(True)
                self._copy_buttons["1_to_2_right"].setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            # Disable if not fully configured
            if "1_to_2_right" in self._copy_buttons:
                self._copy_buttons["1_to_2_right"].setEnabled(False)
                self._copy_buttons["1_to_2_right"].setCursor(Qt.CursorShape.ArrowCursor)

        # Enable left arrow for pair 3->1 (before Channel 3) when both channels 3 and 4 are configured
        if 3 in self._configured_channels and 4 in self._configured_channels:
            if "4_to_3_left" in self._copy_buttons:
                self._copy_buttons["4_to_3_left"].setEnabled(True)
                self._copy_buttons["4_to_3_left"].setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            # Disable if not fully configured
            if "4_to_3_left" in self._copy_buttons:
                self._copy_buttons["4_to_3_left"].setEnabled(False)
                self._copy_buttons["4_to_3_left"].setCursor(Qt.CursorShape.ArrowCursor)

    def _on_copy(self, from_channel, to_channel):
        """Copy configuration from one channel to another."""
        print(f"Copying configuration from Channel {from_channel} to Channel {to_channel}")

        # Use the static copy method from ChannelConfigurationDialog
        success = ChannelConfigurationDialog.copy_configuration(from_channel, to_channel)

        if success:
            self._configured_channels.add(to_channel)
            self._update_copy_buttons()

            # Also copy Channel Pair Type (determine which pair the channels belong to)
            # Channel 1-2 are pair 1, Channel 3-4 are pair 2
            from_pair_key = self._get_pair_key(from_channel)
            to_pair_key = self._get_pair_key(to_channel)

            if from_pair_key in self._pair_type_combos and to_pair_key in self._pair_type_combos:
                from_type = self._pair_type_combos[from_pair_key].currentText()
                self._pair_type_combos[to_pair_key].setCurrentText(from_type)
                print(f"Also copied Channel Pair Type: {from_type}")

            print(f"Successfully copied configuration from Channel {from_channel} to Channel {to_channel}")
        else:
            print(f"Failed to copy: Channel {from_channel} has not been configured yet")

    def _on_copy_pair_to_pair(self, from_pair, to_pair):
        """Copy configuration from one entire pair to another."""
        print(f"Copying configuration from Pair {from_pair} to Pair {to_pair}")

        # Determine source and destination channels
        if from_pair == 1:
            source_channels = [1, 2]
        else:
            source_channels = [3, 4]

        if to_pair == 1:
            dest_channels = [1, 2]
        else:
            dest_channels = [3, 4]

        # Check if source channels are configured
        all_configured = all(ch in self._configured_channels for ch in source_channels)

        if not all_configured:
            print(f"Failed to copy: Not all channels in Pair {from_pair} have been configured")
            return

        # Copy each channel's configuration
        for src_ch, dst_ch in zip(source_channels, dest_channels):
            success = ChannelConfigurationDialog.copy_configuration(src_ch, dst_ch)
            if success:
                self._configured_channels.add(dst_ch)
                print(f"Copied Channel {src_ch} -> Channel {dst_ch}")

        # Copy Channel Pair Type
        from_pair_key = f"{source_channels[0]}_{source_channels[1]}"
        to_pair_key = f"{dest_channels[0]}_{dest_channels[1]}"

        if from_pair_key in self._pair_type_combos and to_pair_key in self._pair_type_combos:
            from_type = self._pair_type_combos[from_pair_key].currentText()
            self._pair_type_combos[to_pair_key].setCurrentText(from_type)
            print(f"Copied Channel Pair Type: {from_type}")

        self._update_copy_buttons()
        print(f"Successfully copied entire Pair {from_pair} to Pair {to_pair}")

    def _get_pair_key(self, channel_num):
        """Get the pair key for a channel (1-2 -> '1_2', 3-4 -> '3_4')."""
        if channel_num in [1, 2]:
            return "1_2"
        elif channel_num in [3, 4]:
            return "3_4"
        return None

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
