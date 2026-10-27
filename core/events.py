"""Event-log records: 10 bytes = Y M D h m s x x ev_lo ev_hi (ev = slot[0:4] ch[4:8] type[8:12] dir[12:14] mode[14:16])."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

ALARM_TYPES = {1: "Alert Amplitude", 2: "Danger Amplitude", 3: "Alert Gap", 4: "Danger Gap", 5: "Not OK", 6: "Relay Trip"}
DIRECTIONS = {1: "Enter", 0: "Left"}
RECORD_LEN = 10
CHUNK_BYTES = 254


@dataclass
class EventRecord:
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    slot: int
    channel: int
    alarm_type: int
    direction: int
    mode: int

    @property
    def date(self) -> str:
        return f"{self.day:02d}/{self.month:02d}/20{self.year:02d}"

    @property
    def time(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}:{self.second:02d}"

    @property
    def alarm_text(self) -> str:
        return ALARM_TYPES.get(self.alarm_type, f"Type {self.alarm_type}")

    @property
    def direction_text(self) -> str:
        return DIRECTIONS.get(self.direction, str(self.direction))

    def as_row(self, serial: int):
        return [f"{serial:03d}", self.date, self.time, self.slot, self.channel, self.alarm_text, self.direction_text, self.mode]


def decode_event_word(w: int):
    return (w & 15, (w >> 4) & 15, (w >> 8) & 15, (w >> 12) & 3, (w >> 14) & 3)


def encode_event_word(slot, channel, alarm_type, direction, mode) -> int:
    return (slot & 15) | ((channel & 15) << 4) | ((alarm_type & 15) << 8) | ((direction & 3) << 12) | ((mode & 3) << 14)


def parse_records(data: bytes) -> List[EventRecord]:
    out = []
    for i in range(0, len(data) - RECORD_LEN + 1, RECORD_LEN):
        r = data[i:i + RECORD_LEN]
        y, mo, d, h, mi, s = r[0:6]
        if mo > 12 or d > 31 or h > 24 or mi > 60 or s > 60 or mo == 0 or d == 0:
            continue           # VB skips corrupt records ("wrong_data")
        slot, ch, at, di, mode = decode_event_word((r[9] << 8) | r[8])
        out.append(EventRecord(y, mo, d, h, mi, s, slot, ch, at, di, mode))
    return out


def make_record(rec: EventRecord) -> bytes:
    w = encode_event_word(rec.slot, rec.channel, rec.alarm_type, rec.direction, rec.mode)
    return bytes((rec.year, rec.month, rec.day, rec.hour, rec.minute, rec.second, 0, 0, w & 0xFF, w >> 8))


def to_csv(records: List[EventRecord]) -> str:
    lines = ["SL.No,Date,Time,Slot,Channel,Alarm Type,Direction,Mode"]
    for i, r in enumerate(records, 1):
        lines.append(",".join(str(x) for x in r.as_row(i)))
    return "\n".join(lines) + "\n"
