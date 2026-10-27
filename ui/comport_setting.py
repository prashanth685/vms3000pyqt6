from PySide6.QtWidgets import QWidget, QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QComboBox
from controls.xp_button import XPButton

class ComPortSetting(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("COM Port Setting")
        layout = QVBoxLayout(self)
        
        gb = QGroupBox("Connection Parameters")
        h = QHBoxLayout()
        self.cmb_port = QComboBox(); self.cmb_port.addItems(["COM1","COM2","COM3"])
        self.cmb_baud = QComboBox(); self.cmb_baud.setCurrentText("115200")
        
        h.addWidget(QLabel("COM Port:")); h.addWidget(self.cmb_port)
        h.addWidget(QLabel("Baud Rate:")); h.addWidget(self.cmb_baud)
        gb.setLayout(h)
        layout.addWidget(gb)
        
        btns = QHBoxLayout()
        btns.addWidget(XPButton("&Connect"))
        btns.addWidget(XPButton("&Save"))
        layout.addLayout(btns)