from PySide6.QtWidgets import QStatusBar, QLabel

class MenuStatus(QStatusBar):
    def __init__(self, parent):
        super().__init__(parent)
        self.status_label = QLabel("Disconnected")
        self.addWidget(self.status_label)
    
    def set_status(self, text):
        self.status_label.setText(text)