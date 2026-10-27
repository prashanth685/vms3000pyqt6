"""Central application state: rack model, connection, files, clipboard. UI-independent and unit-testable."""
from __future__ import annotations

import copy
import os
from typing import Callable, List, Optional

from . import settings as _settings
from . import tasks
from .config_card import ConfigCard
from .link import RackLink
from .model import MT_NONE, RackModel, SlotModel
from .rcs_file import read_any, write_rcs
from .simulator import SimulatedRack
from .transport import SerialTransport, SimTransport, TcpTransport

Progress = Callable[[int, str], None]


class AppState:
    def __init__(self):
        self.settings = _settings.load()
        self.rack = RackModel()
        self.rack.config = ConfigCard().to_dict()
        self.file_path: Optional[str] = None
        self.dirty = False
        self.link: Optional[RackLink] = None
        self.sim: Optional[SimulatedRack] = None
        self.connected = False
        self.mode = ""                       # "serial" | "network" | "demo"
        self.config_password = ""            # entered/verified during session
        self.connect_password = ""
        self.clipboard: Optional[SlotModel] = None
        self.traffic_lines: List[str] = []
        self.listeners: List[Callable[[str], None]] = []
        self.uploaded_card: Optional[ConfigCard] = None

    # ---- observers
    def notify(self, event: str):
        for cb in list(self.listeners):
            try:
                cb(event)
            except Exception:
                pass

    def mark_dirty(self):
        self.dirty = True
        self.notify("dirty")

    # ---- config card helpers
    @property
    def card(self) -> ConfigCard:
        return ConfigCard.from_dict(self.rack.config)

    def set_card(self, card: ConfigCard):
        self.rack.config = card.to_dict()
        self.rack.rack_slots = card.rack_slots
        self.rack.alarm_inhibit = card.alarm_inhibit
        self.mark_dirty()

    # ---- files
    def new(self):
        self.rack = RackModel()
        self.rack.config = ConfigCard().to_dict()
        self.file_path, self.dirty = None, False
        self.notify("model")

    def open_file(self, path: str):
        self.rack = read_any(path)
        if not self.rack.config:
            self.rack.config = ConfigCard().to_dict()
        self.file_path, self.dirty = path, False
        self._remember(path)
        self.notify("model")

    def save_file(self, path: Optional[str] = None):
        path = path or self.file_path
        if not path:
            raise ValueError("no file path")
        if not os.path.splitext(path)[1]:
            path += ".rcs"
        write_rcs(path, self.rack)
        self.file_path, self.dirty = path, False
        self._remember(path)
        self.notify("saved")
        return path

    def _remember(self, path: str):
        self.settings["last_file"] = path
        rec = [p for p in self.settings.get("recent_files", []) if p != path]
        self.settings["recent_files"] = ([path] + rec)[:8]
        _settings.save(self.settings)

    def persist_settings(self):
        _settings.save(self.settings)

    # ---- connection
    def _traffic(self, direction: str, data: bytes):
        self.traffic_lines.append(f"{direction}  " + " ".join(f"{b:02X}" for b in data))
        del self.traffic_lines[:-400]

    def _open(self, transport, rack_addr: int, timeout: float):
        self.disconnect(quiet=True)
        transport.open()
        self.link = RackLink(transport, rack_addr, timeout=timeout, on_traffic=self._traffic)

    def connect_serial(self, port: str, baud: int, rack_addr: int, password: str,
                       parity: str = None, data_bits: int = None, stop_bits: int = None,
                       progress: Progress = lambda p, t: None):
        s = self.settings
        # Use provided values or fall back to settings
        parity = parity if parity is not None else s["parity"]
        data_bits = data_bits if data_bits is not None else s["data_bits"]
        stop_bits = stop_bits if stop_bits is not None else s["stop_bits"]
        t = SerialTransport(port, int(baud), parity, data_bits, stop_bits)
        self._open(t, rack_addr, float(s["timeout"]))
        self.mode = "serial"
        self._finish_connect(password, progress, {"com_port": port, "baud_rate": int(baud), "rack_address": rack_addr})

    def connect_network(self, host: str, port: int, rack_addr: int, password: str, timeout: float = 1.0, progress: Progress = lambda p, t: None):
        self._open(TcpTransport(host, int(port)), rack_addr, float(timeout))
        self.mode = "network"
        self._finish_connect(password, progress, {"host": host, "tcp_port": int(port), "rack_address": rack_addr, "timeout": float(timeout)})

    def connect_demo(self, progress: Progress = lambda p, t: None):
        """Connect to the built-in simulated rack (seeded from the current configuration)."""
        from .model import RackModel as _R
        seed = copy.deepcopy(self.rack)
        addr = int(self.settings.get("rack_address", 1))
        self.sim = SimulatedRack(seed, address=addr, wait_cycles=1)
        self.sim.set_plugged_from_image()
        self._open(SimTransport(self.sim), addr, 1.0)
        self.mode = "demo"
        self._finish_connect(seed_pw(seed, "connect"), progress, {})

    def _finish_connect(self, password: str, progress: Progress, remember: dict):
        try:
            card = tasks.connect(self.link, password, progress)
        except Exception:
            self.disconnect(quiet=True)
            raise
        self.connect_password = password
        self.uploaded_card = card
        self.settings.update(remember)
        _settings.save(self.settings)
        self.connected = True
        self.notify("connection")

    def disconnect(self, quiet: bool = False):
        if self.link:
            try:
                self.link.t.close()
            except Exception:
                pass
        self.link, self.connected, self.mode, self.sim = None, False, "", None
        if not quiet:
            self.notify("connection")

    # ---- rack operations
    def require_link(self) -> RackLink:
        if not self.connected or not self.link:
            raise tasks.TaskError("Not connected to a rack")
        return self.link

    def upload(self, progress: Progress = lambda p, t: None, cancel=None) -> tasks.UploadResult:
        res = tasks.upload(self.require_link(), progress, cancel)
        self.rack = res.rack
        self.dirty = True
        self.notify("model")
        return res

    def download(self, config_password: str, slots=None, progress: Progress = lambda p, t: None, cancel=None):
        tasks.download(self.require_link(), self.rack, config_password, slots, progress, cancel)
        self.config_password = config_password

    # ---- clipboard (copy / cut / paste module)
    def copy_slot(self, n: int) -> bool:
        if self.rack.slots[n].module == MT_NONE:
            return False
        self.clipboard = copy.deepcopy(self.rack.slots[n])
        return True

    def cut_slot(self, n: int) -> bool:
        if not self.copy_slot(n):
            return False
        self.rack.slots[n] = SlotModel()
        self.mark_dirty()
        return True

    def paste_slot(self, n: int) -> bool:
        if self.clipboard is None:
            return False
        self.rack.slots[n] = copy.deepcopy(self.clipboard)
        self.mark_dirty()
        return True

    # ---- rack-wide flags
    def set_alarm_inhibit(self, on: bool):
        c = self.card
        c.alarm_inhibit = on
        self.set_card(c)

    def set_trip_multiply(self, on: bool):
        c = self.card
        c.trip_multiply = on
        self.set_card(c)


def seed_pw(rack: RackModel, which: str) -> str:
    c = ConfigCard.from_dict(rack.config)
    return c.connect_password if which == "connect" else c.config_password
