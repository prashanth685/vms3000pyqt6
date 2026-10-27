from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QLineEdit, QLabel, QHBoxLayout
from controls.xp_button import XPButton
from PySide6.QtCore import QDateTime

class RTCWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RTC - Real Time Clock")
        layout = QVBoxLayout(self)
        
        gb = QGroupBox("Date & Time")
        h = QHBoxLayout()
        self.dt_edit = QLineEdit(QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss"))
        h.addWidget(QLabel("Set Time:")); h.addWidget(self.dt_edit)
        gb.setLayout(h)
        layout.addWidget(gb)
        
        layout.addWidget(XPButton("&SET DATE-TIME"))