"""Run long rack tasks on a worker thread with a modal progress dialog (replaces the VB timer state machines)."""
from __future__ import annotations

import os
import sys
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import QLabel, QProgressBar

from qt_common import ThemedDialog


class _Worker(QThread):
    progress = Signal(int, str)
    finished_ok = Signal(object)
    failed = Signal(object)

    def __init__(self, fn, cancel_event):
        super().__init__()
        self._fn, self._cancel = fn, cancel_event

    def run(self):
        try:
            res = self._fn(lambda p, t="": self.progress.emit(int(p), str(t)), self._cancel)
            self.finished_ok.emit(res)
        except BaseException as e:           # noqa: BLE001 - report everything to the GUI thread
            self.failed.emit(e)


def run_task(parent, fonts, title: str, fn, *, cancellable: bool = True):
    """fn(progress, cancel_event) -> result.  Blocks (modal) until done.  Returns (ok, result_or_exception)."""
    cancel = threading.Event()
    dlg = ThemedDialog(parent, title, fonts=fonts, size=(460, 170), badge=False)
    label = QLabel("Starting...")
    bar = QProgressBar()
    bar.setRange(0, 100)
    dlg.body_layout.addWidget(label)
    dlg.body_layout.addWidget(bar)
    btns = [dlg.footer_button("Cancel", cancel.set)] if cancellable else []
    if btns:
        dlg.add_footer(btns)
    out = {"ok": False, "val": None}
    w = _Worker(fn, cancel)
    w.progress.connect(lambda p, t: (bar.setValue(p), label.setText(t or label.text())))

    def ok(r):
        out.update(ok=True, val=r)
        dlg.accept()

    def bad(e):
        out.update(ok=False, val=e)
        dlg.accept()

    w.finished_ok.connect(ok)
    w.failed.connect(bad)
    dlg.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
    w.start()
    dlg.show_modal()
    w.wait(5000)
    return out["ok"], out["val"]
