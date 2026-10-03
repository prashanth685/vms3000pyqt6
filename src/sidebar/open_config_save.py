"""
open_config_save.py — VMS 3000  •  Save Configuration File Dialog
Opens a native file dialog to save .rcs configuration files.
"""

from PyQt6.QtWidgets import QFileDialog


class SaveConfigDialog:
    """Save Configuration File dialog — chooses where to write an .rcs file."""

    def __init__(self, parent, fonts):
        self._fonts = fonts
        self._parent = parent
        self._dialog = None
        self._saved_file = None

    def show(self, default_filename="Configuration"):
        """Open file dialog to save .rcs configuration file."""
        path, _ = QFileDialog.getSaveFileName(
            self._parent,
            "VM3000 SOFTWARE FILES",
            f"C:/{default_filename}.rcs",
            "Rack Configuration Files (*.rcs);;All Files (*)",
        )
        if path and "." not in path.replace("\\", "/").split("/")[-1]:
            path += ".rcs"            # tkinter's defaultextension behaviour
        self._saved_file = path or None

        if self._saved_file:
            print(f"Configuration file saved to: {self._saved_file}")
            # TODO: Add logic to save the configuration data to the selected file
            return self._saved_file
        return None

    def get_saved_file(self):
        """Return the path of the saved file."""
        return self._saved_file
