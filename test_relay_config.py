"""
Test script for Relay Configuration Dialog with channel configuration slots
"""
import os
import sys

# Add src + project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

from points.relay_config import RelayConfigDialog


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    root = QWidget()
    root.setWindowTitle("Test Relay Configuration Dialog")
    root.resize(400, 300)

    # Simulate rack configuration with some modules
    rack_config = {
        "0_1": "No Modules",
        "0_2": "No Modules",
        "0_3": "No Modules",
        "0_4": "No Modules",
        "0_5": "VMM-6M",  # VMM module in slot 5
        "0_6": "No Modules",
        "0_7": "3000/12M/DIS",  # DIS module in slot 7
        "0_8": "No Modules",
        "0_9": "No Modules",
        "0_10": "No Modules",
        "0_11": "No Modules",
    }

    def open_relay_dialog():
        dlg = RelayConfigDialog(
            root,
            slot_num=5,  # Relay slot number
            rack_type="VMM/12T/DISP",
            config_id="CONFIG-001",
            selected_slot=5,  # Initially select slot 5 (which has VMM-6M)
            rack_config=rack_config,
        )
        dlg.show()

    lay = QVBoxLayout(root)
    btn = QPushButton("Open Relay Configuration Dialog")
    btn.clicked.connect(open_relay_dialog)
    lay.addSpacing(30)
    lay.addWidget(btn)
    info_label = QLabel("This will show channel configuration slots\n"
                        "for the selected module (e.g., VMM-6M in slot 5)")
    info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.addWidget(info_label)
    lay.addStretch(1)

    root.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
