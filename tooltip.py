"""
tooltip.py — Simple tooltip helper for PyQt6

Qt has native tooltips, so this is now a thin compatibility shim that keeps the
old ``ToolTip(widget, text)`` call sites working.
"""

from PyQt6.QtWidgets import QWidget


class ToolTip:
    def __init__(self, widget: QWidget, text: str):
        self.w = widget
        self.t = text
        self()

    def __call__(self, event=None):
        """Enable tooltip on hover."""
        self.w.setToolTip(self.t or "")
