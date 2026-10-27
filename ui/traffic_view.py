from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class TrafficView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Traffic / Communication View"))
        # Can add QTextEdit for logs later