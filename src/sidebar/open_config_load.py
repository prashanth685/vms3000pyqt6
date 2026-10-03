"""
open_config_load.py — VMS 3000  •  Load Configuration File Dialog
Opens a native file dialog to select .rcs configuration files.
"""

from PyQt6.QtWidgets import QFileDialog


class LoadConfigDialog:
    """Load Configuration File dialog — selects an .rcs configuration file."""

    def __init__(self, parent, fonts):
        self._fonts = fonts
        self._parent = parent
        self._dialog = None
        self._selected_file = None

    def show(self):
        """Open file dialog to select .rcs configuration file."""
        path, _ = QFileDialog.getOpenFileName(
            self._parent,
            "VM3000 SOFTWARE FILES",
            "C:/",
            "Rack Configuration Files (*.rcs);;All Files (*)",
        )
        self._selected_file = path or None

        if self._selected_file:
            print(f"Configuration file selected: {self._selected_file}")
            # TODO: Add logic to load and parse the selected .rcs file
            return self._selected_file
        return None

    def get_selected_file(self):
        """Return the path of the selected file."""
        return self._selected_file
