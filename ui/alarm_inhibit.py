from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
                           QCheckBox, QLineEdit, QGridLayout, QFrame)
from PySide6.QtCore import Qt
from controls.xp_button import XPButton
from modules.modbus import ModbusClient
from modules.globals import *  # Assuming shared registers/constants

class AlarmInhibitWindow(QWidget):
    """
    Alarm Inhibit Configuration Window
    Converted from VB6 Alarm Inhibit Form
    Functionality: Enable/Disable alarms per channel, Read/Write to device via Modbus
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Alarm Inhibit")
        self.resize(1100, 680)
        self.modbus = ModbusClient()
        self.setup_ui()
        self.load_current_settings()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("ALARM INHIBIT CONFIGURATION")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        # Main Content Frame
        content = QFrame()
        content.setFrameShape(QFrame.Shape.StyledPanel)
        grid = QGridLayout(content)
        
        # Channel Headers
        headers = ["Channel", "Low Alarm", "High Alarm", "Rate Alarm", "Sensor Fail"]
        for col, header in enumerate(headers):
            lbl = QLabel(header)
            lbl.setStyleSheet("font-weight: bold; padding: 4px;")
            grid.addWidget(lbl, 0, col)

        self.checkboxes = {}  # Store references for read/write

        # Create rows for each channel (typically 4 channels in such systems)
        for row in range(1, 5):  # CH1 to CH4
            ch = f"CH{row}"
            
            # Channel Label
            grid.addWidget(QLabel(ch), row, 0)
            
            # Low Alarm Inhibit
            low_cb = QCheckBox()
            low_cb.setText("Inhibit")
            grid.addWidget(low_cb, row, 1)
            self.checkboxes[f"{ch}_Low"] = low_cb
            
            # High Alarm Inhibit
            high_cb = QCheckBox()
            high_cb.setText("Inhibit")
            grid.addWidget(high_cb, row, 2)
            self.checkboxes[f"{ch}_High"] = high_cb
            
            # Rate Alarm Inhibit
            rate_cb = QCheckBox()
            rate_cb.setText("Inhibit")
            grid.addWidget(rate_cb, row, 3)
            self.checkboxes[f"{ch}_Rate"] = rate_cb
            
            # Sensor Fail Inhibit
            sensor_cb = QCheckBox()
            sensor_cb.setText("Inhibit")
            grid.addWidget(sensor_cb, row, 4)
            self.checkboxes[f"{ch}_Sensor"] = sensor_cb

        main_layout.addWidget(content)

        # Status / Read Value Section
        status_group = QGroupBox("Current Status")
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("Status: Disconnected")
        status_layout.addWidget(self.status_label)
        
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)

        # Control Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_read = XPButton("&Read")
        self.btn_write = XPButton("&Write")
        self.btn_refresh = XPButton("Re&fresh")
        self.btn_exit = XPButton("E&xit")
        
        btn_layout.addWidget(self.btn_read)
        btn_layout.addWidget(self.btn_write)
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_exit)
        
        main_layout.addLayout(btn_layout)

        # Connect Signals
        self.btn_read.clicked.connect(self.read_alarm_inhibit)
        self.btn_write.clicked.connect(self.write_alarm_inhibit)
        self.btn_refresh.clicked.connect(self.load_current_settings)
        self.btn_exit.clicked.connect(self.close)

    def load_current_settings(self):
        """Load current alarm inhibit status from device"""
        try:
            # Example: Read holding registers for alarm inhibit bits
            response = self.modbus.read_holding_registers(ALARM_INHIBIT_REGISTER, 4, slave=15)
            if response.isError():
                self.status_label.setText("Status: Read Error")
                return
            
            values = response.registers
            for i, ch in enumerate(["CH1", "CH2", "CH3", "CH4"]):
                byte = values[i]
                self.checkboxes[f"{ch}_Low"].setChecked(bool(byte & 0x01))
                self.checkboxes[f"{ch}_High"].setChecked(bool(byte & 0x02))
                self.checkboxes[f"{ch}_Rate"].setChecked(bool(byte & 0x04))
                self.checkboxes[f"{ch}_Sensor"].setChecked(bool(byte & 0x08))
            
            self.status_label.setText("Status: Settings Loaded")
        except Exception as e:
            self.status_label.setText(f"Status: Error - {str(e)}")

    def read_alarm_inhibit(self):
        """Read alarm inhibit configuration from Modbus device"""
        self.load_current_settings()

    def write_alarm_inhibit(self):
        """Write alarm inhibit settings to Modbus device"""
        try:
            for i, ch in enumerate(["CH1", "CH2", "CH3", "CH4"]):
                value = 0
                if self.checkboxes[f"{ch}_Low"].isChecked():
                    value |= 0x01
                if self.checkboxes[f"{ch}_High"].isChecked():
                    value |= 0x02
                if self.checkboxes[f"{ch}_Rate"].isChecked():
                    value |= 0x04
                if self.checkboxes[f"{ch}_Sensor"].isChecked():
                    value |= 0x08
                
                # Write to Modbus register
                self.modbus.write_register(ALARM_INHIBIT_REGISTER + i, value, slave=15)
            
            self.status_label.setText("Status: Settings Written Successfully")
        except Exception as e:
            self.status_label.setText(f"Status: Write Failed - {str(e)}")

    def connect_device(self):
        """Helper to ensure connection before read/write"""
        if not self.modbus.is_connected():
            self.status_label.setText("Status: Please connect first")
            return False
        return True
       