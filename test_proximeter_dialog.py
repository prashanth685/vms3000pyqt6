"""
Test script for Proximity Monitor 3000 Configuration Dialog
"""
import os
import sys

# Add src + project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget

from points.proximiter12m_ridial import ProximityMonitor3000ConfigDialog


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    root = QWidget()
    root.setWindowTitle("Test Proximity Monitor 3000 Dialog")
    root.resize(300, 200)

    def open_12m_dialog():
        ProximityMonitor3000ConfigDialog(root, slot_num=1, model="12M/DIS").show()

    def open_6m_dialog():
        ProximityMonitor3000ConfigDialog(root, slot_num=1, model="6M").show()

    lay = QVBoxLayout(root)
    btn_12m = QPushButton("Open 12M/DIS Dialog")
    btn_12m.clicked.connect(open_12m_dialog)
    lay.addWidget(btn_12m)
    btn_6m = QPushButton("Open 6M Dialog")
    btn_6m.clicked.connect(open_6m_dialog)
    lay.addWidget(btn_6m)
    lay.addStretch(1)

    root.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
