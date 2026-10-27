from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QLineEdit, QLabel
from controls.xp_button import XPButton

class VM12Setpoints(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        gb = QGroupBox("Setpoints")
        layout.addWidget(gb)
        layout.addWidget(XPButton("&Write Setpoints"))