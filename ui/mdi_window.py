from PySide6.QtWidgets import QMainWindow, QMdiArea, QMdiSubWindow
from ui.menu import MainMenu

class MDIWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GUI-RCS-V.0.5 [TEXRON 6M MB TimeDelay]")
        self.resize(1450, 920)
        
        self.mdi = QMdiArea()
        self.mdi.setViewMode(QMdiArea.ViewMode.TabbedView)
        self.setCentralWidget(self.mdi)
        
        self.menu = MainMenu(self)
        self.setMenuBar(self.menu)
        
        self.show_welcome()
    
    def show_welcome(self):
        from ui.welcome_screen import WelcomeScreen
        self.add_subwin(WelcomeScreen(), "Welcome Screen")
    
    def add_subwin(self, widget, title=""):
        sub = QMdiSubWindow()
        sub.setWidget(widget)
        sub.setWindowTitle(title)
        self.mdi.addSubWindow(sub)
        sub.showMaximized()
    
    # Menu triggered methods
    def open_comport(self):
        from ui.comport_setting import ComPortSetting
        self.add_subwin(ComPortSetting(), "COM Port Setting")
    
    def open_rack_setup(self):
        from ui.rack_setup import RackSetupWindow
        self.add_subwin(RackSetupWindow(), "Rack Setup")
    
    def open_calibration(self):
        from ui.calibration import CalibrationWindow
        self.add_subwin(CalibrationWindow(), "Calibration")
    
    def open_relay(self):
        from ui.relay import RelayWindow
        self.add_subwin(RelayWindow(), "Relay")
    
    def open_rtc(self):
        from ui.rtc import RTCWindow
        self.add_subwin(RTCWindow(), "RTC")
    
    def open_eventlog(self):
        from ui.eventlog import EventLogWindow
        self.add_subwin(EventLogWindow(), "Event Log")
    
    # Add more as needed...