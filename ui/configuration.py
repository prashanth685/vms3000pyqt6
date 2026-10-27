from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QPushButton

class ConfigurationWindow(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        gb = QGroupBox("System Configuration")
        layout.addWidget(gb)