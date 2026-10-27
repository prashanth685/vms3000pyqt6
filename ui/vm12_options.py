from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QCheckBox
from controls.xp_button import XPButton

class VM12Options(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        gb = QGroupBox("VM12 Options")
        layout.addWidget(gb)
        layout.addWidget(XPButton("&Save Options"))