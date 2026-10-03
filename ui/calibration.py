"""
calibration.py — VMS 3000  •  Calibration window (PyQt6)

Standalone tool:  python ui/calibration.py
"""

import os
import sys
from datetime import datetime

# project root on the path so qt_common can be imported when run directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import serial
import serial.tools.list_ports

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QPushButton, QVBoxLayout, QWidget,
)

from qt_common import show_error, show_info, show_warning

FONT = "MS Sans Serif"
BTN_BG = "#421F00"


def _font(size, bold=False):
    f = QFont(FONT)
    f.setPointSize(size)
    f.setBold(bold)
    return f


def _group(title, size=10, bold=True):
    g = QGroupBox(title)
    g.setFont(_font(size, bold))
    g.setStyleSheet(
        "QGroupBox { border:1px groove #8a8f98; margin-top:10px; padding-top:8px; }"
        "QGroupBox::title { subcontrol-origin: margin; left:8px; padding:0 3px; }"
    )
    return g


def _entry(value="0.0", readonly=False, chars=12):
    e = QLineEdit(value)
    e.setAlignment(Qt.AlignmentFlag.AlignCenter)
    e.setFont(_font(9, True))
    e.setReadOnly(readonly)
    e.setFixedWidth(chars * 9 + 10)
    return e


def _button(text, cb, width=None, enabled=True):
    b = QPushButton(text)
    b.setFont(_font(9, True))
    b.setStyleSheet(
        f"QPushButton {{ background:{BTN_BG}; color:white; padding:6px 10px; border:1px solid #2a1400; }}"
        "QPushButton:hover { background:#5a2b00; }"
        "QPushButton:disabled { background:#8b7a6b; color:#e0d8d0; }"
    )
    if width:
        b.setFixedWidth(width)
    b.setEnabled(enabled)
    b.clicked.connect(lambda _c=False: cb())
    return b


class CalibrationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calibration")
        self.setFixedSize(1320, 900)

        self.ser = None
        self.is_connected = False
        self.current_slave_id = 15
        self.current_baud = 115200

        # Per-gain-section widget lists, keyed by gain number (1, 2, 3)
        self.present_gains = {}
        self.calc_gains = {}
        self.check_boxes = {}
        self.read_values = {}
        self.actual_mills = {}
        self.actual_vrms = {}

        self.setup_ui()
        self.load_com_ports()

    # ------------------------------------------------------------------ #
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # ==================== GAIN SECTIONS ====================
        root.addWidget(self.create_gain_section(1, "Gain -1"))
        root.addWidget(self.create_gain_section(2, "Gain -2"))
        root.addWidget(self.create_gain_section(3, "Gain"))      # CH Gain

        # ==================== CONNECTION + DATE-TIME ====================
        bottom = QHBoxLayout()
        bottom.setSpacing(12)
        root.addLayout(bottom)
        bottom.addWidget(self._build_connection_group(), 1)
        bottom.addWidget(self._build_datetime_group())

    def _build_connection_group(self):
        g = _group("Connection")
        g.setMaximumHeight(90)
        row = QHBoxLayout(g)
        row.setSpacing(8)

        def lbl(t):
            l = QLabel(t)
            l.setFont(_font(8, True))
            return l

        row.addWidget(lbl("Slave Id"))
        self.module_Address_Cmbox = QComboBox()
        self.module_Address_Cmbox.setEditable(True)
        self.module_Address_Cmbox.addItems([str(i) for i in range(1, 32)])
        self.module_Address_Cmbox.setCurrentText("15")
        self.module_Address_Cmbox.setFixedWidth(80)
        row.addWidget(self.module_Address_Cmbox)

        row.addSpacing(10)
        row.addWidget(lbl("Com Port"))
        self.COM_Port_Cmbox = QComboBox()
        self.COM_Port_Cmbox.setEditable(True)
        self.COM_Port_Cmbox.setFixedWidth(110)
        row.addWidget(self.COM_Port_Cmbox)

        row.addSpacing(10)
        row.addWidget(lbl("Baud Rate"))
        self.Baud_Rate_Cmbox = QComboBox()
        self.Baud_Rate_Cmbox.setEditable(True)
        self.Baud_Rate_Cmbox.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.Baud_Rate_Cmbox.setCurrentText("115200")
        self.Baud_Rate_Cmbox.setFixedWidth(100)
        row.addWidget(self.Baud_Rate_Cmbox)

        row.addSpacing(10)
        self.connect_btn = _button("Connect", self.connect_device, 120)
        self.disconnect_btn = _button("Disconnect", self.disconnect_device, 120, enabled=False)
        row.addWidget(self.connect_btn)
        row.addWidget(self.disconnect_btn)
        row.addStretch(1)
        return g

    def _build_datetime_group(self):
        g = QWidget()
        row = QHBoxLayout(g)
        row.setContentsMargins(0, 14, 0, 0)
        row.addWidget(_button("SET DATE-TIME", self.set_date_time))
        row.addWidget(_button("Exit", self.close))
        return g

    # ------------------------------------------------------------------ #
    def create_gain_section(self, gain_num, title):
        frame = _group(title, size=13, bold=False)
        outer = QVBoxLayout(frame)
        outer.setSpacing(4)
        top = QHBoxLayout()
        top.setSpacing(16)
        outer.addLayout(top)

        small_bold = _font(8, True)

        # Present Gain
        present = _group("Present Gain")
        g = QGridLayout(present)
        self.present_gains[gain_num] = []
        for i in range(4):
            l = QLabel(f"CH{i + 1} GAIN{gain_num}")
            l.setFont(small_bold)
            g.addWidget(l, i, 0)
            e = _entry(readonly=True)
            g.addWidget(e, i, 1)
            self.present_gains[gain_num].append(e)
        top.addWidget(present)

        # Calculated Gain
        calc = _group("Calculated Gain")
        g = QGridLayout(calc)
        self.calc_gains[gain_num] = []
        self.check_boxes[gain_num] = []
        for i in range(4):
            l = QLabel(f"CH{i + 1} GAIN{gain_num}")
            l.setFont(small_bold)
            g.addWidget(l, i, 0)
            e = _entry()
            g.addWidget(e, i, 1)
            self.calc_gains[gain_num].append(e)
            chk = QCheckBox()
            g.addWidget(chk, i, 2)
            self.check_boxes[gain_num].append(chk)
        top.addWidget(calc)

        # Read Value
        read = _group("Read Value")
        g = QVBoxLayout(read)
        self.read_values[gain_num] = []
        for i in range(4):
            e = _entry(chars=10, readonly=True)
            g.addWidget(e, 0, Qt.AlignmentFlag.AlignHCenter)
            self.read_values[gain_num].append(e)
        mills = QLabel("Mills")
        mills.setFont(small_bold)
        g.addWidget(mills, 0, Qt.AlignmentFlag.AlignHCenter)
        top.addWidget(read)

        # Actual Values
        actual = _group("Actual Values")
        g = QGridLayout(actual)
        for col, text in ((0, "In Mills"), (1, "Vrms In Volts")):
            l = QLabel(text)
            l.setFont(small_bold)
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            g.addWidget(l, 0, col)
        self.actual_mills[gain_num] = []
        self.actual_vrms[gain_num] = []
        for i in range(4):
            em = _entry()
            ev = _entry()
            g.addWidget(em, i + 1, 0)
            g.addWidget(ev, i + 1, 1)
            self.actual_mills[gain_num].append(em)
            self.actual_vrms[gain_num].append(ev)
        top.addWidget(actual)
        top.addStretch(1)

        # Buttons
        btns = QHBoxLayout()
        btns.addSpacing(330)
        btns.addWidget(_button("Calculate", lambda g=gain_num: self.calculate_gain(g), 120))
        btns.addSpacing(10)
        btns.addWidget(_button("Write", lambda g=gain_num: self.write_gain(g), 120))
        btns.addStretch(1)
        outer.addLayout(btns)
        return frame

    # ------------------------------------------------------------------ #
    def load_com_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.COM_Port_Cmbox.clear()
        self.COM_Port_Cmbox.addItems(ports)
        if ports:
            self.COM_Port_Cmbox.setCurrentText(ports[0])

    def connect_device(self):
        if self.is_connected:
            return

        try:
            port = self.COM_Port_Cmbox.currentText()
            baud = int(self.Baud_Rate_Cmbox.currentText())
            slave = int(self.module_Address_Cmbox.currentText())

            self.ser = serial.Serial(port, baud, timeout=1)
            self.current_slave_id = slave
            self.current_baud = baud
            self.is_connected = True

            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            show_info(self, "Success", f"Connected to {port} at {baud} baud")

        except Exception as e:
            show_error(self, "Connection Error", str(e))

    def disconnect_device(self):
        if self.ser:
            self.ser.close()
        self.is_connected = False
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)

    def set_date_time(self):
        if not self.is_connected:
            show_warning(self, "Not Connected", "Please connect first")
            return
        # Send date time command (placeholder)
        dt = datetime.now()
        show_info(self, "Date Time", f"Set to: {dt.strftime('%Y-%m-%d %H:%M:%S')}")

    def calculate_gain(self, gain_num):
        if not self.is_connected:
            show_warning(self, "Not Connected", "Please connect device first")
            return

        try:
            for i in range(4):
                mills = float(self.actual_mills[gain_num][i].text() or 0)
                vrms = float(self.actual_vrms[gain_num][i].text() or 0)

                if vrms != 0:
                    gain = mills / vrms
                    self.calc_gains[gain_num][i].setText(f"{gain:.4f}")
        except Exception as e:
            show_error(self, "Calculate Error", str(e))

    def write_gain(self, gain_num):
        if not self.is_connected:
            show_warning(self, "Not Connected", "Please connect device first")
            return

        try:
            for i in range(4):
                if self.check_boxes[gain_num][i].isChecked():
                    gain_val = float(self.calc_gains[gain_num][i].text() or 0)
                    # TODO: Send Modbus/Protocol command to write gain
                    print(f"Writing CH{i + 1} Gain{gain_num}: {gain_val}")

            show_info(self, "Success", f"Gain {gain_num} values written successfully")
        except Exception as e:
            show_error(self, "Write Error", str(e))

    def closeEvent(self, event):
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
        super().closeEvent(event)

    def run(self):
        self.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = CalibrationApp()
    win.run()
    sys.exit(app.exec())
