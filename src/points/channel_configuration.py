"""
channel_configuration.py — VMS 3000  •  Channel-N Configuration dialog
(Transducer setup / Variables + Alarms)
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QRadioButton, QButtonGroup,
    QStackedWidget, QTabBar, QVBoxLayout, QWidget,
)

from qt_common import (
    center_on_screen, checkbox_qss, field_palette, char_width,
    classic_combo_qss, pick_font, plain_label, raised_button,
    sunken_label,
)


# ══════════════════════════════════════════════════════════════════════════
#  PALETTE
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

    "tab_sel_bg":      "#f0f0f0",
    "tab_unsel_bg":    "#d7dbe0",
    "tab_border":      "#8a8f98",

    "text":            "#000000",
    "text_dim":        "#4a5568",

    "vms_logo":        "#17408a",
}

FONT_NAME = "Segoe UI"


def classic_group(title: str, font) -> QGroupBox:
    """Etched group box with a plain black bold title."""
    g = QGroupBox(f" {title} ")
    g.setFont(font)
    g.setStyleSheet(f"""
        QGroupBox {{
            background:{C['group_bg']};
            border:1px groove {C['group_border']};
            margin-top:9px;
            padding:10px 10px 8px 10px;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left:8px;
            padding:0 2px;
            color:{C['group_label']};
        }}
    """)
    return g


class ChannelConfigurationDialog:
    """Channel-N Configuration dialog."""

    # Static storage for channel configurations
    _channel_configs = {}  # {channel_num: config_dict}

    # ------------------------------------------------------------------ #
    #  Init
    # ------------------------------------------------------------------ #

    def __init__(
        self,
        parent,
        channel_num,
        slot_num=6,
        fonts=None,
        rack_type="",
        active=True,
        on_ok=None,
        model="12M/DIS",
        load_existing=False,
    ):
        self._parent = parent
        self._channel_num = channel_num
        self._slot_num = slot_num
        self._fonts = fonts if isinstance(fonts, dict) else {}
        self._rack_type = rack_type
        self._active = active
        self._dialog = None
        self._on_ok_callback = on_ok
        self._model = model
        self._load_existing = load_existing

        # Widget references used by Set Defaults
        self._direct_row = None
        self._gap_row = None

        self._zero_spin = None

        self._alert_latch = None
        self._danger_latch = None

        self._alert_delay = None
        self._danger_delay = None

        self._trip_multiply = None

        self._recorder_output = None

        self._direction_group = None

        # Transducer setup widgets
        self._transducer_type_combo = None

    def _f(
        self,
        key,
        size=9,
        bold=False,
        italic=False,
        family=FONT_NAME,
    ):
        return pick_font(
            self._fonts,
            key,
            family,
            size,
            bold,
            italic,
        )

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def show(self):
        d = QDialog(self._parent)
        self._dialog = d

        d.setObjectName("chanDlg")
        d.setWindowTitle(
            f"Channel-{self._channel_num} Configuration"
        )
        d.setModal(True)

        d.setStyleSheet(
            f"QDialog#chanDlg {{ background:{C['win_bg']}; }}"
            f"QLabel {{ background:transparent; }}"
            + checkbox_qss(C["text"])
        )

        root = QVBoxLayout(d)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        body = QVBoxLayout()
        body.setContentsMargins(14, 10, 14, 10)

        root.addLayout(body, 1)

        self._create_identity_row(body)
        self._create_tabs(body)
        self._create_buttons(body)

        # Load existing configuration if available
        if self._load_existing:
            existing_config = self.get_channel_config(self._channel_num)
            if existing_config:
                self._load_configuration(existing_config)

        # Start on Variables + Alarms
        self._tabbar.setCurrentIndex(1)

        d.adjustSize()
        d.setFixedSize(d.sizeHint())

        center_on_screen(d)
        d.exec()

    # ------------------------------------------------------------------ #
    #  Small widget helpers
    # ------------------------------------------------------------------ #

    def _lbl(
        self,
        text,
        bold=False,
        size=9,
        italic=False,
        fg=None,
        wrap=False,
    ):
        l = plain_label(
            text,
            self._f(
                "label_b" if bold else "field",
                size,
                bold,
                italic,
            ),
            fg or C["text"],
        )

        l.setWordWrap(wrap)
        return l

    def _group(self, title):
        return classic_group(
            title,
            self._f("group", 9, bold=True),
        )

    def _btn(
        self,
        text,
        cmd,
        width=None,
        enabled=True,
    ):
        return raised_button(
            text,
            cmd,
            width_chars=width,
            enabled=enabled,
            font=self._f("field", 9),
            colors=C,
        )

    def _combo(
        self,
        values,
        default,
        chars=20,
    ):
        cb = QComboBox()

        f = self._f("field", 9)
        cb.setFont(f)

        cb.addItems(values)
        cb.setCurrentText(default)

        cb.setStyleSheet(
            classic_combo_qss(
                C["combo_white_bg"],
                C["combo_white_fg"],
                C["field_border"],
                C["btn_face"],
                C["titlebar"],
                "#ffffff",
            )
        )

        cb.setMinimumWidth(
            char_width(f, chars) + 28
        )

        return cb

    def _spinbox(
        self,
        value,
        chars=5,
        frm=-999,
        to=999,
    ):
        """Small numeric field."""

        sb = QDoubleSpinBox()

        text = str(value)

        if "." in text:
            decimals = len(text.split(".")[1])
        else:
            decimals = 0

        sb.setDecimals(decimals)
        sb.setRange(frm, to)
        sb.setSingleStep(1)
        sb.setValue(float(text))

        f = self._f("field", 9)

        sb.setFont(f)

        field_palette(
            sb,
            C["field_bg"],
            C["text"],
        )

        sb.setFixedWidth(
            char_width(f, chars) + 34
        )

        return sb

    # ------------------------------------------------------------------ #
    #  Identity row
    # ------------------------------------------------------------------ #

    def _create_identity_row(self, parent):
        row = QHBoxLayout()
        row.setSpacing(0)

        row.addWidget(
            self._lbl("CHANNEL", bold=True)
        )

        row.addSpacing(6)

        row.addWidget(
            sunken_label(
                str(self._channel_num),
                self._f("field", 9, True),
                bg=C["field_bg"],
                border=C["field_border"],
                chars=3,
                align=Qt.AlignmentFlag.AlignCenter,
            )
        )

        row.addSpacing(10)

        status = (
            "'ACTIVE'"
            if self._active
            else "'INACTIVE'"
        )

        row.addWidget(
            sunken_label(
                status,
                self._f("field", 9, True),
                bg=C["field_bg"],
                border=C["field_border"],
                chars=10,
                align=Qt.AlignmentFlag.AlignCenter,
            )
        )

        row.addSpacing(30)

        row.addWidget(
            self._lbl("SLOT", bold=True)
        )

        row.addSpacing(6)

        row.addWidget(
            sunken_label(
                str(self._slot_num),
                self._f("field", 9),
                bg=C["field_bg"],
                border=C["field_border"],
                chars=6,
                align=Qt.AlignmentFlag.AlignCenter,
            )
        )

        row.addSpacing(30)

        row.addWidget(
            self._lbl("RACK TYPE", bold=True)
        )

        row.addSpacing(6)

        row.addWidget(
            sunken_label(
                self._rack_type,
                self._f("field", 9),
                bg=C["field_bg"],
                border=C["field_border"],
                chars=16,
            )
        )

        row.addStretch(1)

        parent.addLayout(row)
        parent.addSpacing(8)

    # ------------------------------------------------------------------ #
    #  Tabs
    # ------------------------------------------------------------------ #

    def _create_tabs(self, parent):
        self._tabbar = QTabBar()

        self._tabbar.setDrawBase(False)
        self._tabbar.setFont(
            self._f("tab", 9)
        )

        self._tabbar.addTab(
            "Transducer setup"
        )

        self._tabbar.addTab(
            "Variables + Alarms"
        )

        self._tabbar.setStyleSheet(f"""
            QTabBar::tab {{
                background:{C['tab_unsel_bg']};
                color:{C['text']};
                border:1px outset {C['tab_border']};
                padding:4px 10px;
                margin-right:2px;
            }}

            QTabBar::tab:selected {{
                background:{C['tab_sel_bg']};
                font-weight:bold;
                border:1px solid {C['tab_border']};
                border-bottom-color:{C['tab_sel_bg']};
            }}
        """)

        parent.addWidget(
            self._tabbar
        )

        stack = QStackedWidget()

        transducer_page = QWidget()
        self._build_transducer_setup_tab(
            transducer_page
        )

        variables_page = QWidget()
        self._build_variables_alarms_tab(
            variables_page
        )

        stack.addWidget(
            transducer_page
        )

        stack.addWidget(
            variables_page
        )

        stack.setSizePolicy(
            stack.sizePolicy().horizontalPolicy(),
            stack.sizePolicy().verticalPolicy(),
        )

        parent.addWidget(
            stack,
            1,
        )

        self._tabbar.currentChanged.connect(
            stack.setCurrentIndex
        )

        self._stack = stack

    # ------------------------------------------------------------------ #
    #  Variables + Alarms
    # ------------------------------------------------------------------ #

    def _build_variables_alarms_tab(self, page):
        lay = QVBoxLayout(page)

        lay.setContentsMargins(
            0,
            0,
            0,
            8,
        )

        panel = self._group(
            "Variables + Alarm"
        )

        lay.addWidget(panel)

        pl = QVBoxLayout(panel)
        pl.setSpacing(4)

        # -------------------------------------------------------------- #
        # Enable
        # -------------------------------------------------------------- #

        top = QHBoxLayout()

        pl.addLayout(top)

        enable = self._group("Enable")

        top.addWidget(
            enable,
            1,
        )

        grid = QGridLayout(enable)

        grid.setHorizontalSpacing(12)

        grid.addWidget(
            self._lbl(
                "Full Scale Range",
                bold=True,
            ),
            0,
            1,
        )

        grid.addWidget(
            self._lbl(
                "Clamp Value",
                bold=True,
            ),
            0,
            2,
        )

        direct_scale_values = [
            "0-10 mil pp",
            "0-15 mil pp",
            "0-20 mil pp",
            "0-100 mil pp",
            "0-150 µm pp",
            "0-200 µm pp",
            "0-400 µm pp",
            "0-500 µm pp",
        ]

        gap_scale_values = [
            "-24Vdc",
            "-20Vdc",
            "-18Vdc",
            "-16Vdc",
            "-12Vdc",
            "-10Vdc",
            "-8Vdc",
        ]

        self._direct_row = self._build_enable_row(
            grid,
            1,
            "Direct",
            direct_scale_values,
            "0-10 mil pp",
            "0",
        )

        self._gap_row = self._build_enable_row(
            grid,
            2,
            "Gap",
            gap_scale_values,
            "-24Vdc",
            "0",
        )

        # -------------------------------------------------------------- #
        # Zero Position
        # -------------------------------------------------------------- #

        zero = self._group(
            "Zero Position"
        )

        top.addWidget(zero)

        zl = QVBoxLayout(zero)

        zrow = QHBoxLayout()

        zrow.addWidget(
            self._lbl(
                "Zero Position\n(Gap)"
            )
        )

        zrow.addSpacing(8)

        self._zero_spin = self._spinbox(
            "-9.75",
            chars=6,
        )

        zrow.addWidget(
            self._zero_spin
        )

        zrow.addSpacing(4)

        zrow.addWidget(
            self._lbl("Volts")
        )

        zl.addLayout(zrow)

        zl.addWidget(
            self._btn(
                "Adjust",
                None,
                width=12,
                enabled=False,
            ),
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )

        # -------------------------------------------------------------- #
        # Latching
        # -------------------------------------------------------------- #

        latch = QHBoxLayout()

        latch.setContentsMargins(
            0,
            8,
            0,
            4,
        )

        self._alert_latch = QCheckBox(
            "Alert Latching"
        )

        self._alert_latch.setFont(
            self._f("field", 9)
        )

        self._danger_latch = QCheckBox(
            "Danger Latching"
        )

        self._danger_latch.setFont(
            self._f("field", 9)
        )

        latch.addWidget(
            self._alert_latch
        )

        latch.addSpacing(30)

        latch.addWidget(
            self._danger_latch
        )

        latch.addStretch(1)

        pl.addLayout(latch)

        # -------------------------------------------------------------- #
        # Delay / Trip Multiply
        # -------------------------------------------------------------- #

        mid = QHBoxLayout()

        pl.addLayout(mid)

        # Delay
        delay = self._group("Delay")

        mid.addWidget(
            delay,
            1,
        )

        dl = QVBoxLayout(delay)

        # Alert delay
        r = QHBoxLayout()

        l = self._lbl("Alert")

        l.setFixedWidth(
            char_width(
                self._f("field", 9),
                7,
            )
        )

        r.addWidget(l)

        self._alert_delay = self._spinbox(
            "3",
            chars=4,
        )

        r.addWidget(
            self._alert_delay
        )

        r.addSpacing(6)

        r.addWidget(
            self._lbl("1 - 60 s")
        )

        r.addStretch(1)

        dl.addLayout(r)

        # Danger delay
        r = QHBoxLayout()

        l = self._lbl("Danger")

        l.setFixedWidth(
            char_width(
                self._f("field", 9),
                7,
            )
        )

        r.addWidget(l)

        self._danger_delay = self._spinbox(
            "1",
            chars=4,
        )

        r.addWidget(
            self._danger_delay
        )

        r.addSpacing(6)

        r.addWidget(
            self._lbl("1.0 - 60.0")
        )

        r.addStretch(1)

        dl.addLayout(r)

        # Trip Multiply
        trip = self._group(
            "Trip Multiply"
        )

        mid.addWidget(trip)

        tl = QHBoxLayout(trip)

        self._trip_multiply = self._spinbox(
            "1",
            chars=4,
        )

        tl.addWidget(
            self._trip_multiply
        )

        tl.addSpacing(6)

        tl.addWidget(
            self._lbl(
                "1 to 3 (Step of\n0.25)"
            )
        )

        # -------------------------------------------------------------- #
        # Recorder Output
        # -------------------------------------------------------------- #

        rec = self._group(
            "Recorder Output"
        )

        pl.addWidget(rec)

        rl = QHBoxLayout(rec)

        self._recorder_output = self._combo(
            [
                "NONE",
                "DIRECT AMPLITUDE",
                "GAP",
            ],
            "DIRECT AMPLITUDE",
            20,
        )

        rl.addWidget(
            self._recorder_output
        )

        rl.addStretch(1)

    # ------------------------------------------------------------------ #
    #  Enable row
    # ------------------------------------------------------------------ #

    def _build_enable_row(
        self,
        grid,
        row,
        label,
        scale_values,
        scale_default,
        clamp_default,
    ):
        l = self._lbl(label)

        l.setFixedWidth(
            char_width(
                self._f("field", 9),
                7,
            )
        )

        grid.addWidget(
            l,
            row,
            0,
        )

        scale_combo = self._combo(
            scale_values,
            scale_default,
            14,
        )

        grid.addWidget(
            scale_combo,
            row,
            1,
        )

        clamp_spin = self._spinbox(
            clamp_default,
            chars=5,
        )

        grid.addWidget(
            clamp_spin,
            row,
            2,
        )

        return (
            scale_combo,
            clamp_spin,
        )

    # ------------------------------------------------------------------ #
    #  Transducer setup
    # ------------------------------------------------------------------ #

    def _build_transducer_setup_tab(
        self,
        page,
    ):
        lay = QVBoxLayout(page)

        lay.setContentsMargins(
            0,
            0,
            0,
            8,
        )

        panel = self._group(
            "Transducer Setup"
        )

        lay.addWidget(panel)

        pl = QVBoxLayout(panel)

        grid = QGridLayout()

        pl.addLayout(grid)

        pl.addStretch(1)

        # -------------------------------------------------------------- #
        # Different transducer options based on model
        # -------------------------------------------------------------- #

        if self._model == "12M/DIS":
            rows = [
                (
                    "Type",
                    [
                        "3000- 8mm Proximiter",
                        "3000- 11mm Proximiter",
                        "3000- 5mm Proximiter",
                        "Extended Range",
                    ],
                    "3000- 8mm Proximiter",
                ),
            ]

        else:
            rows = [
                (
                    "Type",
                    [
                        "3000- 8mm Proximiter",
                        "3000- 11mm Proximiter",
                        "3000- 5mm Proximiter",
                    ],
                    "3000- 8mm Proximiter",
                ),
            ]

        for r, (
            label,
            values,
            default,
        ) in enumerate(rows):

            l = self._lbl(label)

            l.setFixedWidth(
                char_width(
                    self._f("field", 9),
                    20,
                )
            )

            grid.addWidget(
                l,
                r,
                0,
            )

            combo = self._combo(
                values,
                default,
                20,
            )

            grid.addWidget(
                combo,
                r,
                1,
            )

            # Store reference to transducer type combo
            if label == "Type":
                self._transducer_type_combo = combo

        grid.setColumnStretch(
            2,
            1,
        )

        # -------------------------------------------------------------- #
        # Transducer Direction
        # -------------------------------------------------------------- #

        pl.addSpacing(10)

        direction_group = self._group(
            "Transducer Direction"
        )

        pl.addWidget(
            direction_group
        )

        dl = QHBoxLayout(
            direction_group
        )

        self._direction_group = QButtonGroup()

        towards = QRadioButton(
            "Towards Probe"
        )

        away = QRadioButton(
            "Away From Probe"
        )

        towards.setFont(
            self._f("field", 9)
        )

        away.setFont(
            self._f("field", 9)
        )

        towards.setChecked(True)

        self._direction_group.addButton(
            towards,
            0,
        )

        self._direction_group.addButton(
            away,
            1,
        )

        dl.addWidget(
            towards
        )

        dl.addSpacing(30)

        dl.addWidget(
            away
        )

        dl.addStretch(1)

    # ------------------------------------------------------------------ #
    #  Bottom button bar
    # ------------------------------------------------------------------ #

    def _create_buttons(self, parent):
        bar = QHBoxLayout()

        bar.setContentsMargins(
            0,
            4,
            0,
            0,
        )

        bar.addWidget(
            self._btn(
                "Ok",
                self._on_ok,
                width=10,
            )
        )

        bar.addSpacing(8)

        bar.addWidget(
            self._btn(
                "Set defaults",
                self._on_set_defaults,
                width=12,
            )
        )

        bar.addSpacing(8)

        bar.addWidget(
            self._btn(
                "Cancel",
                self._on_cancel,
                width=10,
            )
        )

        bar.addSpacing(40)

        bar.addWidget(
            self._btn(
                "Print",
                self._on_print,
                width=10,
            )
        )

        bar.addSpacing(8)

        bar.addWidget(
            self._btn(
                "Help",
                self._on_help,
                width=10,
            )
        )

        bar.addStretch(1)

        logo = QLabel(
            "VMS 3000"
        )

        logo.setFont(
            self._f(
                "logo",
                15,
                bold=True,
                italic=True,
            )
        )

        logo.setStyleSheet(
            f"color:{C['vms_logo']}; "
            f"background:transparent;"
        )

        bar.addWidget(
            logo
        )

        parent.addLayout(bar)

    # ------------------------------------------------------------------ #
    #  Handlers
    # ------------------------------------------------------------------ #

    def _on_ok(self):
        print("OK pressed")

        # Save the current configuration
        config = self._get_configuration()
        ChannelConfigurationDialog._channel_configs[self._channel_num] = config

        if self._on_ok_callback:
            self._on_ok_callback(
                self._channel_num
            )

        self._dialog.accept()

    def _get_configuration(self):
        """Extract current configuration from all widgets."""
        config = {
            "transducer_type": self._transducer_type_combo.currentText() if self._transducer_type_combo else "",
            "transducer_direction": self._direction_group.checkedId() if self._direction_group else 0,
            "direct_scale": self._direct_row[0].currentText() if self._direct_row else "0-10 mil pp",
            "direct_clamp": self._direct_row[1].value() if self._direct_row else 0,
            "gap_scale": self._gap_row[0].currentText() if self._gap_row else "-24Vdc",
            "gap_clamp": self._gap_row[1].value() if self._gap_row else 0,
            "zero_position": self._zero_spin.value() if self._zero_spin else -9.75,
            "alert_latch": self._alert_latch.isChecked() if self._alert_latch else False,
            "danger_latch": self._danger_latch.isChecked() if self._danger_latch else False,
            "alert_delay": self._alert_delay.value() if self._alert_delay else 3,
            "danger_delay": self._danger_delay.value() if self._danger_delay else 1,
            "trip_multiply": self._trip_multiply.value() if self._trip_multiply else 1,
            "recorder_output": self._recorder_output.currentText() if self._recorder_output else "DIRECT AMPLITUDE",
            "pair_type": "",  # Will be set by the parent dialog
        }
        return config

    def _load_configuration(self, config):
        """Load configuration into widgets."""
        if not config:
            return

        # Transducer setup
        if self._transducer_type_combo and "transducer_type" in config:
            self._transducer_type_combo.setCurrentText(config["transducer_type"])

        if self._direction_group and "transducer_direction" in config:
            button = self._direction_group.button(config["transducer_direction"])
            if button:
                button.setChecked(True)

        # Variables + Alarms
        if self._direct_row and "direct_scale" in config:
            self._direct_row[0].setCurrentText(config["direct_scale"])
        if self._direct_row and "direct_clamp" in config:
            self._direct_row[1].setValue(config["direct_clamp"])

        if self._gap_row and "gap_scale" in config:
            self._gap_row[0].setCurrentText(config["gap_scale"])
        if self._gap_row and "gap_clamp" in config:
            self._gap_row[1].setValue(config["gap_clamp"])

        if self._zero_spin and "zero_position" in config:
            self._zero_spin.setValue(config["zero_position"])

        if self._alert_latch and "alert_latch" in config:
            self._alert_latch.setChecked(config["alert_latch"])
        if self._danger_latch and "danger_latch" in config:
            self._danger_latch.setChecked(config["danger_latch"])

        if self._alert_delay and "alert_delay" in config:
            self._alert_delay.setValue(config["alert_delay"])
        if self._danger_delay and "danger_delay" in config:
            self._danger_delay.setValue(config["danger_delay"])

        if self._trip_multiply and "trip_multiply" in config:
            self._trip_multiply.setValue(config["trip_multiply"])

        if self._recorder_output and "recorder_output" in config:
            self._recorder_output.setCurrentText(config["recorder_output"])

        # Note: pair_type is handled by the parent dialog, not this one

    @classmethod
    def copy_configuration(cls, from_channel, to_channel):
        """Copy configuration from one channel to another."""
        if from_channel in cls._channel_configs:
            cls._channel_configs[to_channel] = dict(cls._channel_configs[from_channel])
            return True
        return False

    @classmethod
    def get_channel_config(cls, channel_num):
        """Get configuration for a specific channel."""
        return cls._channel_configs.get(channel_num)

    @classmethod
    def has_configuration(cls, channel_num):
        """Check if a channel has been configured."""
        return channel_num in cls._channel_configs

    def _on_set_defaults(self):
        """
        Reset all editable fields to their default values.

        Important:
        Recorder Output defaults to DIRECT AMPLITUDE.
        """

        print("Set defaults pressed")

        # --------------------------------------------------------------
        # Direct
        # --------------------------------------------------------------

        if self._direct_row:
            direct_scale = self._direct_row[0]
            direct_clamp = self._direct_row[1]

            direct_scale.setCurrentText(
                "0-10 mil pp"
            )

            direct_clamp.setValue(0)

        # --------------------------------------------------------------
        # Gap
        # --------------------------------------------------------------

        if self._gap_row:
            gap_scale = self._gap_row[0]
            gap_clamp = self._gap_row[1]

            gap_scale.setCurrentText(
                "-24Vdc"
            )

            gap_clamp.setValue(0)

        # --------------------------------------------------------------
        # Zero Position
        # --------------------------------------------------------------

        if self._zero_spin:
            self._zero_spin.setValue(
                -9.75
            )

        # --------------------------------------------------------------
        # Alert / Danger Latching
        # --------------------------------------------------------------

        if self._alert_latch:
            self._alert_latch.setChecked(
                False
            )

        if self._danger_latch:
            self._danger_latch.setChecked(
                False
            )

        # --------------------------------------------------------------
        # Delay
        # --------------------------------------------------------------

        if self._alert_delay:
            self._alert_delay.setValue(3)

        if self._danger_delay:
            self._danger_delay.setValue(1)

        # --------------------------------------------------------------
        # Trip Multiply
        # --------------------------------------------------------------

        if self._trip_multiply:
            self._trip_multiply.setValue(1)

        # --------------------------------------------------------------
        # Recorder Output
        #
        # Required default:
        # DIRECT AMPLITUDE
        # --------------------------------------------------------------

        if self._recorder_output:
            self._recorder_output.setCurrentText(
                "DIRECT AMPLITUDE"
            )

        # --------------------------------------------------------------
        # Transducer Direction
        # --------------------------------------------------------------

        if self._direction_group:
            button = self._direction_group.button(0)

            if button:
                button.setChecked(True)

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

    ChannelConfigurationDialog(
        None,
        1,
        slot_num=10,
        rack_type="",
        active=True,
    ).show()
