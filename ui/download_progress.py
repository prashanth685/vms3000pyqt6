from PySide6.QtWidgets import QWidget, QVBoxLayout, QProgressBar, QLabel
from controls.xp_button import XPButton

class DownloadProgress(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.label = QLabel("Downloading Configuration...")
        self.progress = QProgressBar()
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        layout.addWidget(XPButton("&Cancel"))