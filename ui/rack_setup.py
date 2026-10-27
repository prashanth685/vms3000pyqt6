from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QLabel, QComboBox
from controls.xp_button import XPButton

class RackSetupWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rack Setup")
        layout = QVBoxLayout(self)
        
        gb = QGroupBox("Module Configuration")
        layout.addWidget(gb)
        # Add module address, type etc.
        btns = QHBoxLayout()
        btns.addWidget(XPButton("&Save"))
        btns.addWidget(XPButton("&Read"))
        layout.addLayout(btns)