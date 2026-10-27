"""Software VMS-3000 rack used for demo mode and tests. Speaks the same Modbus RTU frames as the hardware."""
from __future__ import annotations

import datetime
import struct
from typing import Dict, List, Optional

from . import modbus_rtu as m
from .calibration import Calibration, pack_read
from .events import EventRecord, make_record, CHUNK_BYTES
from .image import IMAGE_WORDS, addr as slot_addr, build_image
from .model import RackModel


class SimulatedRack:
    def __init__(self, rack: Optional[RackModel] = None, address: int = 1, wait_cycles: int = 1):
        self.address = address
        self.image: List[int] = build_image(rack or RackModel())
        self.actual_image_head = list(self.image[:34])          # what FC04 reports as plugged-in modules
        self.wait_cycles = wait_cycles
        self._read_state = 0
        self._wait = 0
        self.write_status = 0            # bit1 complete, bit2 fail, bit3 slot mismatch
        self.events: Dict[int, List[EventRecord]] = {}
        self._event_slot = 0
        self.calibration = Calibration()
        self.now = datetime.datetime.now()
        self.rtc_offset = datetime.timedelta(0)
        self.log: List[bytes] = []
        self.drop_next = 0               # test hook: ignore the next N requests

    # ---- helpers
    def _resp(self, body: bytes) -> bytes:
        return m.with_crc(bytes((self.address,)) + body)

    def _exc(self, fc: int, code: int) -> bytes:
        return self._resp(bytes((fc | 0x80, code)))

    def card_password(self, which: str) -> str:
        from .config_card import decode_card
        c, _t, _a = decode_card(self.image[:61])
        return c.config_password if which == "config" else c.connect_password

    def plugged_types(self) -> Dict[int, int]:
        from .config_card import decode_card
        return decode_card(self.actual_image_head + [0] * 30)[1]

    def set_plugged_from_image(self):
        self.actual_image_head = list(self.image[:34])

    # ---- main entry
    def handle(self, req: bytes) -> Optional[bytes]:
        self.log.append(req)
        if self.drop_next > 0:
            self.drop_next -= 1
            return None
        if len(req) < 4 or not m.check_crc(req):
            return None
        if req[0] not in (self.address, 0):
            return None
        fc = req[1]
        try:
            fn = getattr(self, f"_fc{fc}", None)
            if fn is None:
                return self._exc(fc, 1)
            return fn(req)
        except IndexError:
            return self._exc(fc, 2)

    def _fc3(self, req):
        a, n = (req[2] << 8) | req[3], (req[4] << 8) | req[5]
        if a + n > IMAGE_WORDS or n == 0 or n > 125 + 0:
            return self._exc(3, 3 if n > 125 else 2)
        data = b"".join(m.split_word(w) for w in self.image[a:a + n])
        return self._resp(bytes((3, len(data))) + data)

    def _fc4(self, req):
        a, n = (req[2] << 8) | req[3], (req[4] << 8) | req[5]
        words = (self.actual_image_head + [0] * 64)[a:a + n]
        data = b"".join(m.split_word(w) for w in words)
        return self._resp(bytes((4, len(data))) + data)

    def _fc16(self, req):
        a, n = (req[2] << 8) | req[3], (req[4] << 8) | req[5]
        if a + n > IMAGE_WORDS:
            return self._exc(16, 2)
        words = [(req[7 + 2 * i] << 8) | req[8 + 2 * i] for i in range(n)]
        slot, off = divmod(a, 1024)
        self.write_status = 2
        if 1 <= slot <= 11 and off == 0:
            plugged = self.plugged_types().get(slot, 0)
            if (words[0] >> 8) != slot or plugged != (words[0] & 0xFF):
                self.write_status = 8          # slot conflict
        if self.write_status != 8:
            self.image[a:a + n] = words
            if slot == 0:
                pass
        return self._resp(req[1:6])

    def _fc8(self, req):
        sub = (req[2] << 8) | req[3]
        if sub in (0, 5, 7, 10):
            if sub == 7:
                self._read_state, self._wait = 7, self.wait_cycles
            if sub == 5:
                self._read_state, self._wait = 5, self.wait_cycles
            return self._resp(req[1:6])
        if sub == 8:                                    # slot-read status: bit12 wait, bit13 complete
            if self._wait > 0:
                self._wait -= 1
                info = 1 << 12
            else:
                info = 1 << 13
        elif sub == 6:                                  # setpoint read status: 1 wait, 2 complete, 4 fail
            if self._wait > 0:
                self._wait -= 1
                info = 1
            else:
                info = 2
        elif sub == 2:                                  # write status
            if self._wait > 0:
                self._wait -= 1
                info = 1
            else:
                info = self.write_status or 2
        else:
            return self._exc(8, 1)
        return self._resp(bytes((8,)) + m.split_word(sub) + m.split_word(info))

    # ---- custom function codes
    def _fc69(self, req):
        cmd, slot = req[2], req[3]
        if cmd == 1:
            self._event_slot = slot
            return self._resp(bytes((69, 0, 0)))
        if cmd == 2:
            return self._resp(bytes((69, 0, 2)))
        ev = self.events.get(self._event_slot, [])
        ln = len(ev) * 10
        return self._resp(bytes((69,)) + struct.pack("<HHHH", 2, 2, ln, 0))

    def _fc67(self, req):
        cmd, slot = req[2], req[3]
        a = (req[4] << 8) | req[5]
        if cmd in (1,):
            self._event_slot = slot
            return self._resp(bytes((67, 0, 0, 0)))
        if cmd == 2:
            return self._resp(bytes((67, 0, 0, 2)))
        raw = b"".join(make_record(r) for r in self.events.get(self._event_slot or slot, []))
        chunk = raw[a:a + CHUNK_BYTES]
        return self._resp(bytes((67, 0, len(chunk))) + chunk)

    def _fc70(self, req):
        cmd, slot = req[2], req[3]
        self.events.pop(slot, None)
        return self._resp(req[1:4])

    def _dt_bytes(self):
        t = datetime.datetime.now() + self.rtc_offset
        return bytes((t.month, t.year % 100, t.hour, t.day, t.second, t.minute, 0, 0))

    def _fc71(self, req):
        if req[2] == 0:               # set
            month, year, hour, day, sec, minute = req[3:9]
            try:
                new = datetime.datetime(2000 + year, month, day, hour, minute, sec)
                self.rtc_offset = new - datetime.datetime.now()
            except ValueError:
                return self._exc(71, 3)
            return self._resp(req[1:3])
        return self._resp(bytes((71, 0)) + self._dt_bytes()[:6])

    def _fc72(self, req):
        return self._fc71(bytes((req[0], 71, 0)) + req[2:9])

    def _fc73(self, req):
        return self._resp(bytes((73, 0)) + self._dt_bytes()[:6])

    def _fc80(self, req):
        data = pack_read(self.calibration)
        return self._resp(bytes((80, len(data))) + data)

    def _fc81(self, req):
        f = struct.unpack("<12f", req[6:54])
        self.calibration.gain1, self.calibration.gain2, self.calibration.gap_gain = list(f[0:4]), list(f[4:8]), list(f[8:12])
        return self._resp(req[1:6])
