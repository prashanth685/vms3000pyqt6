from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QCheckBox, QHBoxLayout
from controls.xp_button import XPButton

class RelayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Relay Configuration")
        layout = QVBoxLayout(self)
        
        gb = QGroupBox("Relay Outputs")
        v = QVBoxLayout()
        for i in range(1, 9):
            v.addWidget(QCheckBox(f"Relay {i}"))
        gb.setLayout(v)
        layout.addWidget(gb)
        
        h = QHBoxLayout()
        h.addWidget(XPButton("&Write"))
        h.addWidget(XPButton("&Read"))
        layout.addLayout(h)