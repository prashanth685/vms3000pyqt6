"""
relay_config.py — VMS 3000 Relay Configuration Dialog
Classic-style relay configuration dialog, matching the legacy VMS 3000
"Relay Configuration" screen:
  - Rack Type / Config ID / Relay Slot header
  - Available Slots rack graphic (11 module slots, selected slot highlighted)
  - Available Monitor channels / Alarms list
  - Logic keypad: And(*), Or(+), (, ), Enter, <-, CLR, Copy  + percent readout
  - Standard Relay Association: channel dropdown, Active / Latching Relay,
    And Voting Setup
  - Alarm Drive Logic text box
  - Relay NE/NDE Switch Status line
  - Bottom bar: Ok, Point Names, Cancel, Print, Help, VMS 3000 badge
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "..")))

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen, QTextCursor
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QListWidget, QPlainTextEdit, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget,
)

from qt_common import center_on_parent, checkbox_qss, raised_button, scaled_pixmap

# ── Classic "Windows Classic" gray theme, matching the reference screenshot ──
# Falls back to this if the project theme.py isn't available / doesn't define
# these classic-look keys (the modern teal/card theme doesn't apply to this
# legacy-style dialog).
try:
    from theme import T as _PROJECT_T
except Exception:
    _PROJECT_T = {}

CLASSIC = {
    "win_bg":       "#dbe4f0",   # light blue-gray dialog face
    "group_bg":     "#dbe4f0",
    "field_bg":     "#ffffff",
    "text":         "#000000",
    "text_dim":     "#000000",
    "border_dark":  "#7f8a9a",
    "border_light": "#ffffff",
    "border_black": "#000000",
    "btn_face":     "#dbe4f0",
    "btn_hover":    "#eaf0f8",
    "accent":       "#0d3fa0",   # VMS 3000 badge blue
    "slot_dark":    "#0a2a52",
    "slot_mid":     "#1c4d82",
    "slot_light":   "#3f7ab5",
    "slot_selected": "#79b8e8",
    "led_green":    "#3fdc5a",
    "led_yellow":   "#e8d23f",
    "lcd_bg":       "#0b0f14",
}
T = {**CLASSIC, **{k: v for k, v in _PROJECT_T.items() if k not in CLASSIC}}

FONT_NAME = "MS Sans Serif"


def _font(size=8, bold=False, italic=False) -> QFont:
    f = QFont(FONT_NAME)
    f.setPointSize(size)
    f.setBold(bold)
    f.setItalic(italic)
    return f


# ══════════════════════════════════════════════════════════════════════════
#  Classic bevel helpers
# ══════════════════════════════════════════════════════════════════════════

def sunken_frame() -> QFrame:
    """A frame with a classic sunken (etched-in) border."""
    f = QFrame()
    f.setObjectName("sunkenFrame")
    f.setStyleSheet(f"QFrame#sunkenFrame {{ background:{T['field_bg']};"
                    f" border:2px inset {T['border_dark']}; }}")
    return f


def group_box(title, font) -> tuple:
    """
    Classic Windows GroupBox: an etched border with a title cut into the
    top-left. Returns (group_widget, content_layout).
    """
    g = QGroupBox(title)
    g.setFont(font)
    g.setStyleSheet(f"""
        QGroupBox {{
            background:{T['win_bg']};
            border:1px solid {T['border_dark']};
            margin-top:8px; padding:12px 8px 8px 8px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin; subcontrol-position: top left;
            left:8px; padding:0 4px; color:{T['text']}; background:{T['win_bg']};
        }}
    """)
    lay = QVBoxLayout(g)
    lay.setContentsMargins(8, 10, 8, 8)
    return g, lay


def classic_button(text, command, font, width=None, enabled=True) -> QPushButton:
    """A raised classic beveled button."""
    return raised_button(
        text, command, width_chars=width, enabled=enabled, font=font,
        colors={"btn_face": T["btn_face"], "btn_hover": T["btn_hover"],
                "btn_press": "#c3cfdf", "btn_border": T["border_dark"],
                "text": T["text"]},
    )


# ══════════════════════════════════════════════════════════════════════════
#  Available Slots rack graphic
# ══════════════════════════════════════════════════════════════════════════

class SlotsRackWidget(QWidget):
    """Painted rack of module slots; click a slot to select it."""

    PAD = 4
    HEIGHT = 168
    NUM_Y = 12                  # slot-number row, fully inside the top edge
    TOP_Y = 26                  # module image top
    NAME_OFFSET = 10            # module short-name row, from bottom

    def __init__(self, dialog_ref, n_slots, f_bold, f_small, parent=None):
        super().__init__(parent)
        self._dlg = dialog_ref
        self._n = n_slots
        self._f_bold = f_bold
        self._f_small = f_small
        self.setFixedHeight(self.HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _slot_w(self):
        return (self.width() - 2 * self.PAD) / self._n

    def mousePressEvent(self, e):
        if self.width() < 10:
            return
        i = int((e.position().x() - self.PAD) // self._slot_w()) + 1
        i = max(1, min(self._n, i))
        self._dlg._on_slot_selected(i)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(T["field_bg"]))
        p.setPen(QPen(QColor(T["border_dark"]), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(0, 0, self.width() - 1, self.height() - 1)

        width = self.width() if self.width() >= 10 else 480
        n, pad = self._n, self.PAD
        slot_w = (width - 2 * pad) / n
        bot_y = self.HEIGHT - 22
        name_y = self.HEIGHT - self.NAME_OFFSET
        selected = self._dlg.config_data["selected_slot"]

        # Every slot is drawn at the SAME size — no enlarge/zoom for the
        # selected slot. Selection is shown only via a highlight border.
        for i in range(1, n + 1):
            x0 = pad + (i - 1) * slot_w
            x1 = x0 + slot_w - 2
            cx = (x0 + x1) / 2
            is_selected = (i == selected)

            # real module image, scaled to FIT the slot (aspect kept)
            module = self._dlg._rack_config.get(f"0_{i}")
            filename = self._dlg._resolve_module_image(module)
            box_w = max(1, (x1 - x0) - 4)
            box_h = max(1, (bot_y - self.TOP_Y) - 4)
            pm = scaled_pixmap(filename, box_w, box_h, keep_aspect=True)
            if pm is not None:
                cy = (self.TOP_Y + bot_y) / 2
                p.drawPixmap(int(cx - pm.width() / 2), int(cy - pm.height() / 2), pm)

            if is_selected:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(QColor("#ffffff"), 2))
                p.drawRect(QRectF(x0, self.TOP_Y, x1 - x0, bot_y - self.TOP_Y))
                p.setPen(QPen(QColor(T["accent"]), 1))
                p.drawRect(QRectF(x0 - 1, self.TOP_Y - 1, x1 - x0 + 2, bot_y - self.TOP_Y + 2))

            # Slot number: drawn LAST with a high-contrast chip behind it
            num_text = str(i)
            fm = QFontMetrics(self._f_bold)
            chip_w = max(14, fm.horizontalAdvance(num_text) + 8)
            chip_h = fm.height() + 2
            p.setPen(QPen(QColor(T["border_dark"]), 1))
            p.setBrush(QColor("#fdf6c9"))
            p.drawRect(QRectF(cx - chip_w / 2, self.NUM_Y - chip_h / 2, chip_w, chip_h))
            p.setFont(self._f_bold)
            p.setPen(QColor("#000000"))
            p.drawText(QRectF(cx - chip_w / 2, self.NUM_Y - chip_h / 2, chip_w, chip_h),
                       Qt.AlignmentFlag.AlignCenter, num_text)

            # Module short-name, shown under the image
            p.setFont(self._f_small)
            p.setPen(QColor(T["text_dim"]))
            fm2 = QFontMetrics(self._f_small)
            p.drawText(QRectF(cx - slot_w / 2, name_y - fm2.height() / 2, slot_w, fm2.height()),
                       Qt.AlignmentFlag.AlignCenter,
                       self._dlg._short_module_label(module))
        p.end()


# ══════════════════════════════════════════════════════════════════════════
#  Relay Configuration Dialog
# ══════════════════════════════════════════════════════════════════════════

class RelayConfigDialog:
    """Relay Configuration dialog — classic VMS 3000 layout."""

    NUM_SLOTS = 11

    def __init__(self, parent, slot_num, rack_type, config_id, selected_slot=4, rack_config=None):
        self._parent = parent
        self._slot_num = slot_num
        self._rack_type = rack_type
        self._config_id = config_id
        self._selected_slot = selected_slot
        self._rack_config = rack_config or {}  # Saved rack configuration data
        self._dialog = None

        # ── Full data model — every field visible in the reference dialog ──
        self.config_data = {
            "rack_type": rack_type,
            "config_id": config_id,
            "relay_slot": slot_num,
            "selected_slot": selected_slot,
            "monitor_channels": [],          # "Available Monitor channels/ Alarms" list
            "logic_expression": "",          # built via And/Or/(/)/Enter keypad
            "logic_percent": 0,              # "0%" readout under keypad
            "channel_association": "Channel 1",
            "active": False,
            "latching_relay": False,
            "alarm_drive_logic": "",
            "ne_nde_switch_status": "",
        }

    # ──────────────────────────────────────────────────────────────────
    def show(self):
        d = QDialog(self._parent)
        self._dialog = d
        d.setObjectName("relayDlg")
        d.setWindowTitle("Relay Configuration")
        d.setMinimumSize(680, 520)
        d.resize(700, 600)
        d.setModal(True)
        d.setStyleSheet(f"QDialog#relayDlg {{ background:{T['win_bg']}; }}"
                        f"QLabel {{ background:transparent; color:{T['text']}; }}"
                        + checkbox_qss(T['text']))

        self._f_norm = _font(8)
        self._f_bold = _font(8, bold=True)
        self._f_small = _font(7)
        self._f_group = _font(8, bold=True)
        self._f_vms = _font(13, bold=True, italic=True)

        self._build_ui()

        # Every widget now exists, so selecting the initial slot can fill the
        # monitor list, the channel dropdown and the Alarm Drive Logic box.
        self._on_slot_selected(self.config_data["selected_slot"])

        center_on_parent(d, self._parent)
        d.exec()

    # ──────────────────────────────────────────────────────────────────
    def _label(self, text, bold=False):
        l = QLabel(text)
        l.setFont(self._f_bold if bold else self._f_norm)
        return l

    def _build_ui(self):
        main = QVBoxLayout(self._dialog)
        main.setContentsMargins(8, 8, 8, 8)

        # ═══════════════════ Header: Rack Type / Config ID / Relay Slot ════
        header = QHBoxLayout()
        header.addWidget(self._label("Rack Type:", True))
        header.addSpacing(4)
        header.addWidget(self._label(self._rack_type))
        header.addSpacing(24)
        header.addWidget(self._label("Config ID:", True))
        header.addSpacing(4)
        header.addWidget(self._label(self._config_id or ""))
        header.addSpacing(24)
        header.addWidget(self._label("Relay Slot:", True))
        header.addSpacing(4)
        header.addWidget(self._label(str(self._slot_num)))
        header.addStretch(1)
        main.addLayout(header)
        main.addSpacing(8)

        # ═══════════════════ Top split: Slots | Monitor channels ═══════════
        top_split = QHBoxLayout()
        top_split.setSpacing(12)
        main.addLayout(top_split, 1)

        slots_group, slots_lay = group_box("Available Slots", self._f_group)
        top_split.addWidget(slots_group, 58)
        self._build_slots_rack(slots_lay)
        slots_lay.addStretch(1)

        mon_group, mon_lay = group_box("Available Monitor channels/ Alarms", self._f_group)
        top_split.addWidget(mon_group, 42)
        self._build_monitor_list(mon_lay)
        mon_lay.addSpacing(8)
        self._build_keypad(mon_lay)

        # ═══════════════════ Bottom split: Association | Alarm Logic ═══════
        bottom_split = QHBoxLayout()
        bottom_split.setSpacing(12)
        main.addSpacing(8)
        main.addLayout(bottom_split, 1)

        assoc_group, assoc_lay = group_box("Standard Relay Association", self._f_group)
        bottom_split.addWidget(assoc_group, 1)
        self._build_relay_association(assoc_lay)

        logic_group, logic_lay = group_box("Alarm Drive Logic", self._f_group)
        bottom_split.addWidget(logic_group, 1)
        self._build_alarm_drive_logic(logic_lay)

        # ═══════════════════ NE/NDE Switch Status ═══════════════════════
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 8, 0, 6)
        status_row.addWidget(self._label("Relay NE/NDE Switch Status:", True))
        status_row.addSpacing(6)
        self._status_value = self._label("")
        status_row.addWidget(self._status_value)
        status_row.addStretch(1)
        main.addLayout(status_row)

        # ═══════════════════ Bottom button bar ═══════════════════════
        self._build_bottom_bar(main)

    # ──────────────────────────────────────────────────────────────────
    #  Available Slots rack graphic
    # ──────────────────────────────────────────────────────────────────
    def _build_slots_rack(self, parent_layout):
        self._slots_widget = SlotsRackWidget(
            self, self.NUM_SLOTS, self._f_bold, self._f_small)
        parent_layout.addWidget(self._slots_widget)

    def _redraw_slots_rack(self):
        if hasattr(self, "_slots_widget"):
            self._slots_widget.update()

    def _on_slot_selected(self, slot_num):
        """Select a slot in the rack graphic and populate the Available
        Monitor channels/Alarms list for the module installed there."""
        self.config_data["selected_slot"] = slot_num
        self._redraw_slots_rack()

        module = self._rack_config.get(f"0_{slot_num}")
        entries = self._monitor_entries_for_slot(slot_num, module)
        self.config_data["monitor_channels"] = entries

        if hasattr(self, "_monitor_listbox"):
            self._monitor_listbox.blockSignals(True)
            self._monitor_listbox.clear()
            self._monitor_listbox.addItems(entries)
            self._monitor_listbox.blockSignals(False)

        # Update channel association dropdown based on available channels
        self._update_channel_association_dropdown(module)

        # Auto-populate Alarm Drive Logic when a module with channels is selected
        if module and self._channel_count_for_module(module) > 0:
            self._auto_populate_alarm_logic(slot_num, module)

    @staticmethod
    def _channel_count_for_module(module):
        """Number of monitored channels for a given module type — drives how
        many Alert/Danger rows appear in Available Monitor channels/Alarms."""
        if not module or module == "No Modules":
            return 0
        if module == "3000/12M/DIS":
            return 4
        if module in ("VMM-6M", "3000/6M"):
            return 2
        upper = module.upper()
        if "TAC" in upper:
            return 2
        return 0

    def _monitor_entries_for_slot(self, slot_num, module):
        """Build the Available Monitor channels/Alarms entries for a slot:
          S{slot}C##A1 (Slot {slot} Any Active Alert)
          S{slot}C##A2 (Slot {slot} Any Active Danger)
          S{slot}C{ch:02d}A1 (Slot {slot} Channel {ch} Alert)
          S{slot}C{ch:02d}A2 (Slot {slot} Channel {ch} Danger)
        Returns an empty list for slots with no monitored channels."""
        n_channels = self._channel_count_for_module(module)
        if n_channels <= 0:
            return []

        entries = [
            f"S{slot_num}C##A1 (Slot {slot_num} Any Active Alert)",
            f"S{slot_num}C##A2 (Slot {slot_num} Any Active Danger)",
        ]
        for ch in range(1, n_channels + 1):
            entries.append(f"S{slot_num}C{ch:02d}A1 (Slot {slot_num} Channel {ch} Alert)")
            entries.append(f"S{slot_num}C{ch:02d}A2 (Slot {slot_num} Channel {ch} Danger)")
        return entries

    @staticmethod
    def _short_module_label(module):
        """Short label under each slot's image ('DIS', '6M', 'RLY', '—' ...)."""
        if not module or module == "No Modules":
            return "\u2014"
        if module == "3000/12M/DIS":
            return "DIS"
        if module in ("VMM-6M", "3000/6M"):
            return "6M"
        upper = module.upper()
        if "RLY" in upper or "RELAY" in upper:
            return "RLY"
        if "TAC" in upper:
            return "TAC"
        return module[:6]

    @staticmethod
    def _resolve_module_image(module):
        """Map an assigned module name to its rack image filename."""
        if not module or module == "No Modules":
            return "NO_Module.jpg"
        if module == "3000/12M/DIS":
            return "Measurement_Module.jpg"
        if module in ("VMM-6M", "3000/6M"):
            return "VMM-6M.jpg"
        upper = module.upper()
        if "RLY" in upper or "RELAY" in upper:
            return "Relay_Module.jpg"
        return "NO_Module.jpg"

    # ──────────────────────────────────────────────────────────────────
    #  Logic keypad: And(*) Or(+) ( ) Enter <- CLR Copy  + % readout
    # ──────────────────────────────────────────────────────────────────
    def _build_keypad(self, parent_layout):
        def add(txt):
            # Insert directly into the Alarm Drive Logic box at the cursor
            self._insert_logic_text(txt)

        btn_font = self._f_norm
        box = QVBoxLayout()
        box.setSpacing(4)
        parent_layout.addLayout(box)

        # Top row: And [*] Or [+]
        r1 = QHBoxLayout()
        r1.addWidget(classic_button("And [*]", lambda: add("*"), btn_font, width=10))
        r1.addWidget(classic_button("Or [+]", lambda: add("+"), btn_font, width=10))
        r1.addStretch(1)
        box.addLayout(r1)

        # Second row: ( ) Enter
        r2 = QHBoxLayout()
        r2.addWidget(classic_button("(", lambda: add("("), btn_font, width=6))
        r2.addWidget(classic_button(")", lambda: add(")"), btn_font, width=6))
        r2.addWidget(classic_button("Enter", self._on_logic_enter, self._f_bold, width=8))
        r2.addStretch(1)
        box.addLayout(r2)

        # Third row: <- CLR Copy
        r3 = QHBoxLayout()
        r3.addWidget(classic_button("<-", self._on_logic_backspace, btn_font, width=6))
        r3.addWidget(classic_button("CLR", self._on_logic_clear, btn_font, width=6))
        r3.addWidget(classic_button("Copy", self._on_copy, btn_font, width=6))
        r3.addStretch(1)
        box.addLayout(r3)

        # Percentage readout at bottom
        pct = QHBoxLayout()
        pct.setContentsMargins(0, 6, 0, 0)
        track = QFrame()
        track.setFixedHeight(12)
        track.setStyleSheet(f"background:{T['field_bg']}; border:2px inset {T['border_dark']};")
        pct.addWidget(track, 1)
        pct.addSpacing(6)
        self._pct_label = QLabel(f'{self.config_data["logic_percent"]}%')
        self._pct_label.setFont(self._f_small)
        pct.addWidget(self._pct_label)
        box.addLayout(pct)

    # ── Alarm Drive Logic text helpers — the logic box is the single
    #    visible source of truth; the keypad, the monitor-channel list,
    #    and Enter/backspace/CLR all read from and write to it directly. ──
    def _logic_text(self):
        return self._alarm_logic_text.toPlainText()

    def _insert_logic_text(self, text):
        """Insert text into the Alarm Drive Logic box at the cursor, then
        sync config_data."""
        widget = getattr(self, "_alarm_logic_text", None)
        if widget is None:
            self.config_data["logic_expression"] += text
            return
        widget.insertPlainText(text)
        widget.ensureCursorVisible()
        widget.setFocus()
        self.config_data["logic_expression"] = self._logic_text()

    def _on_logic_enter(self):
        widget = getattr(self, "_alarm_logic_text", None)
        if widget is not None:
            self.config_data["logic_expression"] = self._logic_text()
        print(f"Enter logic expression: {self.config_data['logic_expression']}")

    def _on_logic_backspace(self):
        widget = getattr(self, "_alarm_logic_text", None)
        if widget is not None:
            widget.textCursor().deletePreviousChar()
            widget.setFocus()
            self.config_data["logic_expression"] = self._logic_text()
        else:
            self.config_data["logic_expression"] = self.config_data["logic_expression"][:-1]

    def _on_logic_clear(self):
        widget = getattr(self, "_alarm_logic_text", None)
        if widget is not None:
            widget.clear()
            widget.setFocus()
        self.config_data["logic_expression"] = ""
        self.config_data["logic_percent"] = 0
        self._pct_label.setText("0%")

    # ──────────────────────────────────────────────────────────────────
    #  Available Monitor channels/ Alarms
    # ──────────────────────────────────────────────────────────────────
    def _build_monitor_list(self, parent_layout):
        lb = QListWidget()
        lb.setFont(self._f_norm)
        lb.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        lb.setStyleSheet(
            f"QListWidget {{ background:{T['field_bg']}; color:{T['text']};"
            f" border:2px inset {T['border_dark']}; }}"
            "QListWidget::item:selected { background:#0a246a; color:#ffffff; }"
        )
        lb.addItems(self.config_data["monitor_channels"])
        lb.itemSelectionChanged.connect(self._on_monitor_channel_select)
        self._monitor_listbox = lb
        parent_layout.addWidget(lb, 1)

    def _on_monitor_channel_select(self):
        """Selecting a channel/alarm entry (e.g. 'S5C01A1 (Slot 5 Channel 1
        Alert)') inserts just its point code into the Alarm Drive Logic box
        at the cursor."""
        items = self._monitor_listbox.selectedItems()
        if not items:
            return
        code = items[0].text().split(" ", 1)[0]
        self._insert_logic_text(code)

    # ──────────────────────────────────────────────────────────────────
    #  Standard Relay Association
    # ──────────────────────────────────────────────────────────────────
    def _build_relay_association(self, parent_layout):
        parent_layout.addWidget(self._label("Channel Association"))

        self._channel_combo = QComboBox()
        self._channel_combo.setFont(self._f_norm)
        self._channel_combo.addItems([f"Channel {i}" for i in range(1, 9)])
        self._channel_combo.setCurrentText(self.config_data["channel_association"])
        self._channel_combo.setStyleSheet("QComboBox { background:#ffffff; color:#000; padding:2px 4px; }")
        self._channel_combo.activated.connect(lambda _i: self._on_channel_selected())
        parent_layout.addWidget(self._channel_combo)
        parent_layout.addSpacing(6)

        self._active_chk = QCheckBox("Active")
        self._active_chk.setFont(self._f_norm)
        self._active_chk.setChecked(self.config_data["active"])
        parent_layout.addWidget(self._active_chk)

        self._latching_chk = QCheckBox("Latching Relay")
        self._latching_chk.setFont(self._f_norm)
        self._latching_chk.setChecked(self.config_data["latching_relay"])
        parent_layout.addWidget(self._latching_chk)

        parent_layout.addSpacing(8)
        parent_layout.addWidget(classic_button("And Voting Setup", self._on_voting_setup, self._f_norm))
        parent_layout.addStretch(1)

    def _on_voting_setup(self):
        print(f"And Voting Setup for slot {self._slot_num}")

    def _logic_for_channel(self, slot_num, channel_num):
        entries = [
            f"S{slot_num}C{channel_num:02d}A1 (Slot {slot_num} Channel {channel_num} Alert)",
            f"S{slot_num}C{channel_num:02d}A2 (Slot {slot_num} Channel {channel_num} Danger)",
        ]
        return " + ".join(e.split()[0] for e in entries)

    def _on_channel_selected(self):
        """When a channel is chosen in the Channel Association dropdown,
        populate the Alarm Drive Logic text with that channel's points."""
        selected_channel = self._channel_combo.currentText()
        if not selected_channel:
            return

        # Extract channel number from "Channel X" format
        try:
            channel_num = int(selected_channel.split()[-1])
        except (IndexError, ValueError):
            return

        selected_slot = self.config_data["selected_slot"]
        module = self._rack_config.get(f"0_{selected_slot}")

        # Only populate if there's a module with channels in the selected slot
        n_channels = self._channel_count_for_module(module)
        if n_channels <= 0 or channel_num > n_channels:
            return

        logic_expression = self._logic_for_channel(selected_slot, channel_num)
        self._alarm_logic_text.setPlainText(logic_expression)
        self.config_data["alarm_drive_logic"] = logic_expression
        print(f"Populated Alarm Drive Logic for Channel {channel_num}: {logic_expression}")

    def _auto_populate_alarm_logic(self, slot_num, module):
        """Auto-populate the Alarm Drive Logic text when a module with
        channels is selected in the rack."""
        n_channels = self._channel_count_for_module(module)
        if n_channels <= 0:
            return

        selected_channel = self._channel_combo.currentText()
        if not selected_channel:
            return

        try:
            channel_num = int(selected_channel.split()[-1])
        except (IndexError, ValueError):
            channel_num = 1  # Default to channel 1 if parsing fails

        # Validate channel number against available channels
        if channel_num > n_channels:
            channel_num = 1

        logic_expression = self._logic_for_channel(slot_num, channel_num)
        self._alarm_logic_text.setPlainText(logic_expression)
        self.config_data["alarm_drive_logic"] = logic_expression
        print(f"Auto-populated Alarm Drive Logic for Slot {slot_num}, "
              f"Channel {channel_num}: {logic_expression}")

    def _update_channel_association_dropdown(self, module):
        """Update the Channel Association dropdown based on the number of
        available channels in the selected module."""
        if not hasattr(self, "_channel_combo"):
            return
        n_channels = self._channel_count_for_module(module)
        combo = self._channel_combo

        if n_channels <= 0:
            combo.clear()
            combo.addItem("No Channels")
            combo.setCurrentIndex(0)
            combo.setEnabled(False)
        else:
            channel_values = [f"Channel {i}" for i in range(1, n_channels + 1)]
            current = combo.currentText()
            combo.setEnabled(True)
            combo.clear()
            combo.addItems(channel_values)
            # keep the current selection if still valid, else the first channel
            combo.setCurrentText(current if current in channel_values else channel_values[0])

    # ──────────────────────────────────────────────────────────────────
    #  Alarm Drive Logic
    # ──────────────────────────────────────────────────────────────────
    def _build_alarm_drive_logic(self, parent_layout):
        te = QPlainTextEdit()
        te.setFont(self._f_norm)
        te.setStyleSheet(
            f"QPlainTextEdit {{ background:{T['field_bg']}; color:{T['text']};"
            f" border:2px inset {T['border_dark']}; }}"
        )
        te.setPlainText(self.config_data["alarm_drive_logic"])
        self._alarm_logic_text = te
        parent_layout.addWidget(te, 1)

    # ──────────────────────────────────────────────────────────────────
    #  Bottom button bar
    # ──────────────────────────────────────────────────────────────────
    def _build_bottom_bar(self, main):
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{T['border_dark']};")
        main.addWidget(line)
        main.addSpacing(6)

        bottom = QHBoxLayout()
        for text, cb in (("Ok", self._on_ok), ("Point Names", self._on_point_names),
                         ("Cancel", self._on_cancel), ("Print", self._on_print),
                         ("Help", self._on_help)):
            bottom.addWidget(classic_button(text, cb, self._f_norm, width=10))
        bottom.addStretch(1)

        vms = QLabel("VMS 3000")
        vms.setFont(self._f_vms)
        vms.setStyleSheet(f"color:{T['accent']}; background:transparent;")
        bottom.addWidget(vms)
        main.addLayout(bottom)

    # ──────────────────────────────────────────────────────────────────
    #  Button handlers
    # ──────────────────────────────────────────────────────────────────
    def _on_ok(self):
        self.config_data["channel_association"] = self._channel_combo.currentText()
        self.config_data["active"] = self._active_chk.isChecked()
        self.config_data["latching_relay"] = self._latching_chk.isChecked()
        self.config_data["alarm_drive_logic"] = self._logic_text()
        self.config_data["monitor_channels"] = [
            self._monitor_listbox.item(i).text() for i in range(self._monitor_listbox.count())
        ]
        print(f"Ok — relay configuration applied for slot {self._slot_num}: {self.config_data}")
        self._dialog.accept()

    def _on_point_names(self):
        print(f"Point Names for slot {self._slot_num}")

    def _on_cancel(self):
        self._dialog.reject()

    def _on_print(self):
        print(f"Print relay configuration for slot {self._slot_num}")

    def _on_help(self):
        print("Help — Relay Configuration")

    def _on_copy(self):
        print(f"Copy relay configuration for slot {self._slot_num}")


# ══════════════════════════════════════════════════════════════════════════
#  Standalone demo
# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    host = QPushButton("Open Relay Configuration...")
    host.resize(300, 120)
    host.clicked.connect(lambda: RelayConfigDialog(
        host, slot_num=1, rack_type="Standard Relay", config_id="", selected_slot=4).show())
    host.show()
    sys.exit(app.exec())
