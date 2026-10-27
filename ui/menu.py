from PySide6.QtWidgets import QMenuBar, QMenu
from PySide6.QtGui import QAction

class MainMenu(QMenuBar):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        # File
        file = QMenu("&File", self)
        self.addMenu(file)
        file.addAction(QAction("E&xit", self, triggered=parent.close))
        
        # Setup
        setup = QMenu("&Setup", self)
        self.addMenu(setup)
        setup.addAction(QAction("COM Port", self, triggered=parent.open_comport))
        setup.addAction(QAction("Rack Setup", self, triggered=parent.open_rack_setup))
        
        # Calibration
        cal = QMenu("&Calibration", self)
        self.addMenu(cal)
        cal.addAction(QAction("Gain Calibration", self, triggered=parent.open_calibration))
        
        # Tools
        tools = QMenu("&Tools", self)
        self.addMenu(tools)
        tools.addAction(QAction("Relay", self, triggered=parent.open_relay))
        tools.addAction(QAction("RTC", self, triggered=parent.open_rtc))
        tools.addAction(QAction("Event Log", self, triggered=parent.open_eventlog))
        
        # Help
        help_m = QMenu("&Help", self)
        self.addMenu(help_m)