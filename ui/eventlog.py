from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QHBoxLayout
from controls.xp_button import XPButton

class EventLogWindow(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)
        
        h = QHBoxLayout()
        h.addWidget(XPButton("&Refresh"))
        h.addWidget(XPButton("&Clear"))
        layout.addLayout(h)