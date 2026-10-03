"""
Test script for VMS 3000 Toolbar with Connection functionality
"""

import os
import sys

# Add src + project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget

from ui.toolbar import Toolbar


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    root = QMainWindow()
    root.setWindowTitle("VMS 3000 - Toolbar Test")
    root.resize(800, 600)

    central = QWidget()
    root.setCentralWidget(central)
    lay = QVBoxLayout(central)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)

    # Create toolbar
    toolbar = Toolbar(central, bg_color="#f4f6f9")

    # Set up callbacks
    toolbar.set_callback("new", lambda: print("New file created"))
    toolbar.set_callback("open", lambda: print("Open file dialog"))
    toolbar.set_callback("save", lambda: print("File saved"))
    toolbar.set_callback("print", lambda: print("Print document"))
    toolbar.set_callback("settings", lambda: print("Settings opened"))
    toolbar.set_callback("cut", lambda: print("Text cut"))
    toolbar.set_callback("copy", lambda: print("Text copied"))
    toolbar.set_callback("paste", lambda: print("Text pasted"))
    toolbar.set_callback("direct_connect", lambda result: print(f"Connected: {result}"))
    toolbar.set_callback("network_connect", lambda: print("Network connect initiated"))
    toolbar.set_callback("disconnect", lambda: print("Disconnected"))

    # Add some content to demonstrate the toolbar
    content_label = QLabel(
        "VMS 3000 Toolbar Demo\n\nClick the toolbar icons to test functionality:\n"
        "- File operations: New, Open, Save, Print, Settings\n"
        "- Clipboard: Cut, Copy, Paste\n"
        "- Connection: Click the connection icon for connection options"
    )
    content_label.setStyleSheet("background:white; color:black; font-size:12pt; padding:20px;")
    content_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.addWidget(content_label, 1)

    root.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
