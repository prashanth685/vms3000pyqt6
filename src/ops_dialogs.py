"""Rack-operation dialogs: connect prompts, passwords, event log, RTC, calibration, comm settings, traffic."""
from __future__ import annotations

import datetime
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPlainTextEdit, QTableWidget, QTableWidgetItem, QWidget)

from core import events as ev
from core import tasks
from core.calibration import Calibration, calc_gain
from core.transport import available_ports
from qt_common import ThemedDialog, make_button, make_entry, show_error, show_info, show_warning
from workers import run_task


def ask_password(parent, fonts, title: str, prompt: str):
    """Returns the entered string or None when cancelled."""
    dlg = ThemedDialog(parent, title, fonts=fonts, size=(380, 190), badge=False)
    dlg.body_layout.addWidget(QLabel(prompt))
    e = make_entry("", password=True, chars=20)
    dlg.body_layout.addWidget(e)
    got = {}
    dlg.add_footer([dlg.footer_button("OK", lambda: (got.setdefault("v", e.text()), dlg.accept()), "primary"),
                    dlg.footer_button("Cancel", dlg.reject)])
    dlg.show_modal()
    return got.get("v")


def pick_slots(parent, fonts, title: str, slots: list):
    """Check-list of rack slots; returns the chosen list or None."""
    dlg = ThemedDialog(parent, title, fonts=fonts, size=(360, 130 + 28 * max(1, (len(slots) + 3) // 4)), badge=False)
    boxes = {}
    row = None
    for i, n in enumerate(slots):
        if i % 4 == 0:
            row = QHBoxLayout()
            dlg.body_layout.addLayout(row)
        cb = QCheckBox(f"Slot {n}")
        cb.setChecked(True)
        boxes[n] = cb
        row.addWidget(cb)
    got = {}
    dlg.add_footer([dlg.footer_button("OK", lambda: (got.setdefault("v", [n for n, c in boxes.items() if c.isChecked()]), dlg.accept()), "primary"),
                    dlg.footer_button("Cancel", dlg.reject)])
    dlg.show_modal()
    return got.get("v")


# ── Event log ───────────────────────────────────────────────────────────
class EventLogDialog:
    def __init__(self, parent, fonts, state, slots):
        self.parent, self.fonts, self.state, self.slots = parent, fonts, state, slots
        self.records = []

    def show(self):
        d = ThemedDialog(self.parent, "Event Log", fonts=self.fonts, size=(760, 520), badge=False)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["SL", "Date", "Time", "Slot", "Channel", "Alarm Type", "Direction", "Mode"])
        d.body_layout.addWidget(self.table)
        d.add_footer([d.footer_button("Read", self._read, "primary"), d.footer_button("Clear", self._clear),
                      d.footer_button("Export CSV", self._export), d.footer_button("Close", d.accept)])
        self._d = d
        d.show_modal()

    def _fill(self):
        self.table.setRowCount(len(self.records))
        for i, r in enumerate(self.records):
            for c, v in enumerate(r.as_row(i + 1)):
                self.table.setItem(i, c, QTableWidgetItem(str(v)))

    def _read(self):
        link = self.state.require_link()
        ok, res = run_task(self._d, self.fonts, "Reading event log",
                           lambda p, c: tasks.read_events(link, self.slots, p, c))
        if ok:
            self.records = res
            self._fill()
        else:
            show_error(self._d, "Event Log", str(res))

    def _clear(self):
        link = self.state.require_link()
        ok, res = run_task(self._d, self.fonts, "Clearing event log",
                           lambda p, c: tasks.clear_events(link, self.slots, False, p), cancellable=False)
        if ok:
            self.records = []
            self._fill()
        else:
            show_error(self._d, "Event Log", str(res))

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self._d, "Export events", "events.csv", "CSV (*.csv)")
        if path:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(ev.to_csv(self.records))


# ── Real-time clock ─────────────────────────────────────────────────────
def rtc_dialog(parent, fonts, state):
    link = state.require_link()
    d = ThemedDialog(parent, "Rack Date / Time", fonts=fonts, size=(420, 220), badge=False)
    lbl = QLabel("Rack time: (not read)")
    d.body_layout.addWidget(lbl)

    def read():
        try:
            lbl.setText("Rack time: " + tasks.read_rtc(link).strftime("%d-%m-%Y %H:%M:%S"))
        except Exception as e:                        # noqa: BLE001
            show_error(d, "Date/Time", str(e))

    def setnow():
        try:
            tasks.set_rtc(link)
            read()
        except Exception as e:                        # noqa: BLE001
            show_error(d, "Date/Time", str(e))

    d.add_footer([d.footer_button("Read", read), d.footer_button("Set to PC time", setnow, "primary"),
                  d.footer_button("Close", d.accept)])
    read()
    d.show_modal()


# ── Calibration ─────────────────────────────────────────────────────────
def calibration_dialog(parent, fonts, state):
    link = state.require_link()
    d = ThemedDialog(parent, "Calibration", fonts=fonts, size=(720, 470), badge=False)
    cal = Calibration()
    tbl = QTableWidget(4, 7)
    tbl.setHorizontalHeaderLabels(["Channel", "Gain1", "Gain2", "Gap gain", "Amp (live)", "Gap (live)", "Expected amp"])
    d.body_layout.addWidget(tbl)

    def fill():
        for i in range(4):
            vals = [f"CH{i + 1}", f"{cal.gain1[i]:.6f}", f"{cal.gain2[i]:.6f}", f"{cal.gap_gain[i]:.6f}",
                    f"{cal.amp[i]:.4f}", f"{cal.gap[i]:.4f}", tbl.item(i, 6).text() if tbl.item(i, 6) else "0"]
            for c, v in enumerate(vals):
                tbl.setItem(i, c, QTableWidgetItem(v))

    def read():
        nonlocal cal
        try:
            cal = tasks.read_calibration(link)
            fill()
        except Exception as e:                        # noqa: BLE001
            show_error(d, "Calibration", str(e))

    def calc():
        try:
            for i in range(4):
                exp = float(tbl.item(i, 6).text())
                if exp and cal.amp[i]:
                    cal.gain1[i] = calc_gain(cal.gain1[i], cal.amp[i], exp)
            fill()
        except ValueError as e:
            show_warning(d, "Calibration", str(e))

    def write():
        try:
            for i in range(4):
                cal.gain1[i] = float(tbl.item(i, 1).text())
                cal.gain2[i] = float(tbl.item(i, 2).text())
                cal.gap_gain[i] = float(tbl.item(i, 3).text())
            tasks.write_calibration(link, cal)
            show_info(d, "Calibration", "Gains written to the rack.")
        except Exception as e:                        # noqa: BLE001
            show_error(d, "Calibration", str(e))

    d.add_footer([d.footer_button("Read", read, "primary"), d.footer_button("Calculate", calc),
                  d.footer_button("Write", write), d.footer_button("Close", d.accept)])
    fill()
    d.show_modal()


# ── Communication settings ──────────────────────────────────────────────
def comm_settings_dialog(parent, fonts, state):
    s = state.settings
    d = ThemedDialog(parent, "Communication Settings", fonts=fonts, size=(420, 330), badge=False)
    form = QFormLayout()
    w = QWidget()
    w.setLayout(form)
    d.body_layout.addWidget(w)
    port = QComboBox(); port.setEditable(True)
    port.addItems(available_ports() or [s["com_port"]]); port.setCurrentText(str(s["com_port"]))
    baud = QComboBox(); baud.addItems(["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"])
    baud.setCurrentText(str(s["baud_rate"]))
    parity = QComboBox(); parity.addItems(["N", "E", "O"]); parity.setCurrentText(s["parity"])
    bits = QComboBox(); bits.addItems(["7", "8"]); bits.setCurrentText(str(s["data_bits"]))
    stop = QComboBox(); stop.addItems(["1", "2"]); stop.setCurrentText(str(s["stop_bits"]))
    tmo = QLineEdit(str(s["timeout"]))
    for lab, wd in (("COM port", port), ("Baud rate", baud), ("Parity", parity), ("Data bits", bits),
                    ("Stop bits", stop), ("Timeout (s)", tmo)):
        form.addRow(lab, wd)

    def ok():
        try:
            s.update(com_port=port.currentText(), baud_rate=int(baud.currentText()), parity=parity.currentText(),
                     data_bits=int(bits.currentText()), stop_bits=int(stop.currentText()), timeout=float(tmo.text()))
        except ValueError:
            show_warning(d, "Communication Settings", "Timeout must be a number.")
            return
        state.persist_settings()
        d.accept()

    d.add_footer([d.footer_button("OK", ok, "primary"), d.footer_button("Cancel", d.reject)])
    d.show_modal()


def rack_address_dialog(parent, fonts, state):
    d = ThemedDialog(parent, "Rack Address", fonts=fonts, size=(340, 170), badge=False)
    e = make_entry(str(state.settings.get("rack_address", 1)), chars=6)
    d.body_layout.addWidget(QLabel("Rack address (1-247):"))
    d.body_layout.addWidget(e)

    def ok():
        try:
            v = int(e.text())
            if not 1 <= v <= 247:
                raise ValueError
        except ValueError:
            show_warning(d, "Rack Address", "Enter a number from 1 to 247.")
            return
        state.settings["rack_address"] = v
        state.persist_settings()
        state.rack.rack_address = v
        state.notify("settings")
        d.accept()

    d.add_footer([d.footer_button("OK", ok, "primary"), d.footer_button("Cancel", d.reject)])
    d.show_modal()


def traffic_dialog(parent, fonts, state):
    d = ThemedDialog(parent, "Communication Traffic", fonts=fonts, size=(720, 440), badge=False)
    t = QPlainTextEdit()
    t.setReadOnly(True)
    t.setPlainText("\n".join(state.traffic_lines) or "(no traffic yet)")
    d.body_layout.addWidget(t)
    d.add_footer([d.footer_button("Close", d.accept)])
    d.show_modal()


def diagnostics_dialog(parent, fonts, state):
    link = state.require_link()
    ok, res = run_task(parent, fonts, "Diagnostics", lambda p, c: tasks.check_connection(link), cancellable=False)
    if ok and res:
        show_info(parent, "Diagnostics", "Rack responded to the diagnostic echo test — communication OK.")
    else:
        show_error(parent, "Diagnostics", "No valid response from the rack." if ok else str(res))
