import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLineEdit, QPushButton, QComboBox,
                             QSpinBox, QLabel, QMessageBox, QGroupBox,
                             QTextEdit, QCheckBox)
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QTextCursor
from pymodbus.client import ModbusTcpClient, ModbusSerialClient
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse
import serial.tools.list_ports
import pymodbus
from core.modbus_service import modbus_service, SERIAL_CONFIGS


DIAGNOSTIC_SUBFUNCTIONS = {
    "00: Return Query Data": ("ReturnQueryDataRequest", 0x0000),
    "01: Restart Communications Option": ("RestartCommunicationsOptionRequest", 0x0001),
    "02: Return Diagnostic Register": ("ReturnDiagnosticRegisterRequest", 0x0002),
    "03: Change ASCII Input Delimiter": ("ChangeAsciiInputDelimiterRequest", 0x0003),
    "04: Force Listen Only Mode": ("ForceListenOnlyModeRequest", 0x0004),
    "0A: Clear Counters and Diagnostic Register": ("ClearCountersRequest", 0x000A),
    "0B: Return Bus Message Count": ("ReturnBusMessageCountRequest", 0x000B),
    "0C: Return Bus Communication Error Count": ("ReturnBusCommunicationErrorCountRequest", 0x000C),
    "0D: Return Bus Exception Error Count": ("ReturnBusExceptionErrorCountRequest", 0x000D),
    "0E: Return Slave Message Count": ("ReturnSlaveMessageCountRequest", 0x000E),
    "0F: Return Slave No Response Count": ("ReturnSlaveNoResponseCountRequest", 0x000F),
    "10: Return Slave NAK Count": ("ReturnSlaveNAKCountRequest", 0x0010),
    "11: Return Slave Busy Count": ("ReturnSlaveBusyCountRequest", 0x0011),
    "12: Return Bus Character Overrun Count": ("ReturnBusCharacterOverrunCountRequest", 0x0012),
    "14: Clear Overrun Counter and Flag": ("ClearOverrunCountRequest", 0x0014),
}


def _get_diag_request_class(name):
    import pymodbus.pdu.diag_message as diag_msg
    return getattr(diag_msg, name)


class ModScanReplica(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ModScan Replica (Python/PySide6) - Continuous Raw Traffic")
        self.setGeometry(100, 100, 1250, 900)

        # Use global modbus service
        self.client = modbus_service
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.read_registers)

        self.poll_count = 0
        self.valid_response_count = 0

        # Default to RTU mode (hidden from UI)
        self.is_rtu_mode = True

        self.init_ui()
        self.refresh_serial_ports()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Serial Settings (RTU only - no mode selection shown)
        serial_group = QGroupBox("Serial Settings (RTU)")
        serial_layout = QHBoxLayout()

        serial_layout.addWidget(QLabel("Port:"))
        self.serial_port_combo = QComboBox()
        self.serial_port_combo.setMinimumWidth(120)
        serial_layout.addWidget(self.serial_port_combo)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_serial_ports)
        serial_layout.addWidget(self.refresh_btn)

        serial_layout.addWidget(QLabel("Baud Rate:"))
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText("9600")
        serial_layout.addWidget(self.baud_combo)

        serial_layout.addWidget(QLabel("Serial Config:"))
        self.serial_config_combo = QComboBox()
        self.serial_config_combo.addItems(list(SERIAL_CONFIGS.keys()))
        self.serial_config_combo.setCurrentText("8N1")
        serial_layout.addWidget(self.serial_config_combo)

        serial_group.setLayout(serial_layout)
        main_layout.addWidget(serial_group)

        conn_bar = QHBoxLayout()
        conn_bar.addWidget(QLabel("Slave / Unit ID:"))
        self.unit_input = QSpinBox()
        self.unit_input.setRange(0, 247)
        self.unit_input.setValue(1)
        conn_bar.addWidget(self.unit_input)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        conn_bar.addWidget(self.connect_btn)

        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        conn_bar.addWidget(self.status_label)
        conn_bar.addStretch()
        main_layout.addLayout(conn_bar)

        config_group = QGroupBox("Read Configuration")
        config_layout = QHBoxLayout()

        config_layout.addWidget(QLabel("Address:"))
        self.start_addr = QSpinBox()
        self.start_addr.setRange(0, 65535)
        self.start_addr.setValue(0)  # Default address
        config_layout.addWidget(self.start_addr)

        config_layout.addWidget(QLabel("Length:"))
        self.quantity = QSpinBox()
        self.quantity.setRange(1, 2000)
        self.quantity.setValue(10)  # Default length
        config_layout.addWidget(self.quantity)

        config_layout.addWidget(QLabel("Function:"))
        self.func_combo = QComboBox()
        self.func_combo.addItems([
            "01: Coil Status",
            "02: Input Status",
            "03: Holding Register",
            "04: Input Register",
            "08: Diagnostics",
        ])
        self.func_combo.setCurrentIndex(3)  # Default to 04: Input Register
        self.func_combo.currentIndexChanged.connect(self.on_function_changed)
        config_layout.addWidget(self.func_combo)

        self.diag_sub_label = QLabel("Sub-Function:")
        config_layout.addWidget(self.diag_sub_label)
        self.diag_sub_combo = QComboBox()
        for name in DIAGNOSTIC_SUBFUNCTIONS.keys():
            self.diag_sub_combo.addItem(name)
        config_layout.addWidget(self.diag_sub_combo)
        self.diag_sub_label.setVisible(False)
        self.diag_sub_combo.setVisible(False)

        self.diag_data_label = QLabel("Data (hex):")
        config_layout.addWidget(self.diag_data_label)
        self.diag_data_input = QLineEdit("0000")
        self.diag_data_input.setMaximumWidth(80)
        config_layout.addWidget(self.diag_data_input)
        self.diag_data_label.setVisible(False)
        self.diag_data_input.setVisible(False)

        self.diag_sub_combo.currentIndexChanged.connect(self.on_diag_sub_changed)

        self.read_btn = QPushButton("Read Once")
        self.read_btn.clicked.connect(self.read_registers)
        self.read_btn.setEnabled(False)
        config_layout.addWidget(self.read_btn)

        self.poll_btn = QPushButton("Start Polling")
        self.poll_btn.setCheckable(True)
        self.poll_btn.clicked.connect(self.toggle_polling)
        self.poll_btn.setEnabled(False)
        config_layout.addWidget(self.poll_btn)

        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)

        stats_group = QGroupBox()
        stats_layout = QHBoxLayout()
        stats_layout.setContentsMargins(5, 5, 5, 5)

        self.polls_label = QLabel("Number of Polls: 0")
        self.responses_label = QLabel("Valid Slave Responses: 0")

        stats_layout.addWidget(self.polls_label)
        stats_layout.addWidget(self.responses_label)
        stats_layout.addStretch()

        self.raw_checkbox = QCheckBox("Show Raw Hex Traffic (TX/RX)")
        self.raw_checkbox.setChecked(True)
        stats_layout.addWidget(self.raw_checkbox)

        reset_btn = QPushButton("Clear & Reset")
        reset_btn.clicked.connect(self.reset_counters)
        stats_layout.addWidget(reset_btn)

        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)

        self.display = QTextEdit()
        self.display.setReadOnly(True)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.display.setFont(font)
        self.display.setStyleSheet("background-color: #FFFFFF; color: #000000; border: 1px solid #ccc;")
        main_layout.addWidget(self.display)

    def refresh_serial_ports(self):
        self.serial_port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for p in ports:
            self.serial_port_combo.addItem(p.device, p.device)
        if self.serial_port_combo.count() == 0:
            self.serial_port_combo.addItem("No serial port detected", None)

    def on_function_changed(self, index):
        is_diag = (index == 4)
        self.diag_sub_label.setVisible(is_diag)
        self.diag_sub_combo.setVisible(is_diag)
        if is_diag:
            self.on_diag_sub_changed(self.diag_sub_combo.currentIndex())
        else:
            self.diag_data_label.setVisible(False)
            self.diag_data_input.setVisible(False)

    def on_diag_sub_changed(self, index):
        if index < 0:
            return
        _, sub_code = list(DIAGNOSTIC_SUBFUNCTIONS.values())[index]
        no_data_subs = {0x0002, 0x0004, 0x000A, 0x000B, 0x000C, 0x000D,
                        0x000E, 0x000F, 0x0010, 0x0011, 0x0012, 0x0014}
        needs_data = sub_code not in no_data_subs
        self.diag_data_label.setVisible(needs_data)
        self.diag_data_input.setVisible(needs_data)
        if not needs_data:
            self.diag_data_input.setText("0000")

    def reset_counters(self):
        self.poll_count = 0
        self.valid_response_count = 0
        self.display.clear()
        self.update_stats_labels()

    def update_stats_labels(self):
        self.polls_label.setText(f"Number of Polls: {self.poll_count}")
        self.responses_label.setText(f"Valid Slave Responses: {self.valid_response_count}")

    def toggle_connection(self):
        if self.client and self.client.connected:
            self.disconnect()
        else:
            self.connect()

    def get_serial_config(self):
        """Parse serial config string (e.g., '8N1') to get bytesize, parity, stopbits"""
        config_name = self.serial_config_combo.currentText()
        return SERIAL_CONFIGS.get(config_name, SERIAL_CONFIGS["8N1"])

    def connect(self):
        try:
            # Always use RTU mode (hidden)
            port = self.serial_port_combo.currentData()
            if not port:
                QMessageBox.warning(self, "Warning", "Please select a valid serial port.")
                return

            config = self.get_serial_config()
            success, message = self.client.connect_rtu(
                port=port,
                baud_rate=int(self.baud_combo.currentText()),
                serial_config=self.serial_config_combo.currentText(),
                unit_id=self.unit_input.value()
            )

            if success:
                self.connect_btn.setText("Disconnect")
                self.status_label.setText("Connected")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
                self.read_btn.setEnabled(True)
                self.poll_btn.setEnabled(True)
            else:
                QMessageBox.critical(self, "Connection Failed", message)
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))

    def disconnect(self):
        self.poll_timer.stop()
        self.poll_btn.setChecked(False)
        self.poll_btn.setText("Start Polling")

        self.client.disconnect()

        self.connect_btn.setText("Connect")
        self.status_label.setText("Disconnected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        self.read_btn.setEnabled(False)
        self.poll_btn.setEnabled(False)

    def toggle_polling(self):
        if self.poll_btn.isChecked():
            self.poll_timer.start(1000)
            self.poll_btn.setText("Stop Polling")
        else:
            self.poll_timer.stop()
            self.poll_btn.setText("Start Polling")

    def format_hex_bytes(self, data):
        if not data:
            return "None"
        return "".join([f"[{b:03d}]" for b in data])

    def _execute_diagnostics(self, unit):
        sub_idx = self.diag_sub_combo.currentIndex()
        sub_name, sub_code = list(DIAGNOSTIC_SUBFUNCTIONS.values())[sub_idx]

        needs_data = self.diag_data_input.isVisible()
        if needs_data:
            data_str = self.diag_data_input.text().strip()
            try:
                data_value = int(data_str, 16) & 0xFFFF
            except ValueError:
                return (False, sub_code, 0, None, None,
                        f"Invalid hex data field: '{data_str}'. Expected 4 hex digits (e.g., 0000).")
        else:
            data_value = 0x0000

        raw_tx = bytes([
            unit, 0x08,
            (sub_code >> 8) & 0xFF, sub_code & 0xFF,
            (data_value >> 8) & 0xFF, data_value & 0xFF
        ])

        try:
            req_cls = _get_diag_request_class(sub_name)

            request = None
            try:
                request = req_cls(device_id=unit)
            except TypeError:
                pass
            if request is None:
                try:
                    request = req_cls(unit=unit)
                except TypeError:
                    pass
            if request is None:
                if sub_name in ("ReturnQueryDataRequest",
                                "ChangeAsciiInputDelimiterRequest",
                                "RestartCommunicationsOptionRequest"):
                    request = req_cls(message=data_value)
                else:
                    request = req_cls()

            for attr in ("dev_id", "device_id", "unit_id", "slave"):
                try:
                    setattr(request, attr, unit)
                except Exception:
                    pass

            response = self.client.execute(False, request)

            if response is None:
                return (False, sub_code, data_value, raw_tx, None,
                        "No response from slave (timeout).")

            if isinstance(response, ExceptionResponse):
                return (False, sub_code, data_value, raw_tx, None,
                        f"Modbus Exception {response.exception_code}")

            resp_data = getattr(response, 'message', None)
            if resp_data is None:
                resp_data = getattr(response, 'data', 0)
            if isinstance(resp_data, list):
                resp_data = resp_data[0] if resp_data else 0
            if not isinstance(resp_data, int):
                try:
                    resp_data = int(resp_data)
                except Exception:
                    resp_data = 0

            raw_rx = bytes([
                unit, 0x08,
                (sub_code >> 8) & 0xFF, sub_code & 0xFF,
                (resp_data >> 8) & 0xFF, resp_data & 0xFF
            ])

            return (True, sub_code, resp_data, raw_tx, raw_rx, None)

        except ModbusException as e:
            return (False, sub_code, data_value, raw_tx, None, f"Modbus Exception: {e}")
        except Exception as e:
            return (False, sub_code, data_value, raw_tx, None, f"Error: {e}")

    def _display_diagnostics_result(self, unit):
        sub_idx = self.diag_sub_combo.currentIndex()
        sub_name, sub_code = list(DIAGNOSTIC_SUBFUNCTIONS.values())[sub_idx]

        success, resp_sub, resp_data, raw_tx, raw_rx, err = self._execute_diagnostics(unit)

        html_content = ""

        if self.raw_checkbox.isChecked() and raw_tx:
            html_content += f"<span style='color: grey;'>TX:</span> {self.format_hex_bytes(raw_tx)}<br>"

        if not success:
            self.update_stats_labels()
            html_content += f"<span style='color: red; font-weight: bold;'>{err}</span><br>"
            html_content += "--------------------------------------------------<br>"
            cursor = self.display.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.display.setTextCursor(cursor)
            self.display.insertHtml(html_content)
            scrollbar = self.display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            return

        self.valid_response_count += 1
        self.update_stats_labels()

        if self.raw_checkbox.isChecked() and raw_rx:
            html_content += f"<span style='color: grey;'>RX:</span> <b>{self.format_hex_bytes(raw_rx)}</b><br>"

        html_content += (
            f"<span style='color: grey;'>DATA:</span> "
            f"Sub-Function=0x{resp_sub:04X} ({sub_name}), "
            f"Data=<b>0x{resp_data:04X}</b> ({resp_data})<br>"
        )
        html_content += "--------------------------------------------------<br>"

        cursor = self.display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.display.setTextCursor(cursor)
        self.display.insertHtml(html_content)
        scrollbar = self.display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def read_registers(self):
        if not self.client.is_connected:
            return

        func_idx = self.func_combo.currentIndex()
        start = self.start_addr.value()
        count = self.quantity.value()
        unit = self.unit_input.value()

        try:
            pymodbus_address = start - 1 if start > 0 else 0
            self.poll_count += 1

            if func_idx == 4:
                self._display_diagnostics_result(unit)
                return

            function_code = str(func_idx + 1).zfill(2)
            success, data, message = self.client.read_registers(
                address=pymodbus_address,
                length=count,
                function_code=function_code,
                unit_id=unit
            )

            html_content = ""

            if self.raw_checkbox.isChecked():
                tx_bytes = [unit, func_idx + 1, pymodbus_address >> 8, pymodbus_address & 0xFF, count >> 8, count & 0xFF]
                tx_str = self.format_hex_bytes(tx_bytes)
                html_content += f"<span style='color: grey;'>TX:</span> {tx_str}<br>"

            if not success:
                self.display.setHtml(f"<span style='color: red; font-weight: bold;'>{message}</span>")
                if self.poll_btn.isChecked():
                    self.poll_btn.setChecked(False)
                    self.toggle_polling()
                self.update_stats_labels()
                return

            self.valid_response_count += 1
            self.update_stats_labels()

            if self.raw_checkbox.isChecked():
                html_content += f"<span style='color: grey;'>RX:</span> <b>Data received</b><br>"

            html_content += "<span style='color: grey;'>DATA:</span> "

            is_bit = (func_idx == 0 or func_idx == 1)

            if is_bit:
                for i in range(count):
                    val = data[i] if i < len(data) else False
                    if val:
                        html_content += f"[<b>100</b>]"
                    else:
                        html_content += f"<span style='color: grey;'>[000]</span>"
            else:
                for i in range(count):
                    val = data[i] if i < len(data) else 0
                    html_content += f"<b>[{val % 100000:06d}]</b>"

            html_content += "<br>--------------------------------------------------<br>"

            cursor = self.display.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.display.setTextCursor(cursor)
            self.display.insertHtml(html_content)

            scrollbar = self.display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        except ModbusException as e:
            self.display.append(f"<span style='color: red;'>Modbus Exception: {str(e)}</span><br>")
        except Exception as e:
            self.display.append(f"<span style='color: red;'>Error: {str(e)}</span><br>")

    def closeEvent(self, event):
        self.disconnect()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModScanReplica()
    window.show()
    sys.exit(app.exec())
