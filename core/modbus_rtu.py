"""Modbus RTU framing for the VMS-3000 (standard FC03/04/08/16 + custom FC67-73,80,81)."""
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import List, Optional

FC_READ_HOLDING = 3
FC_READ_INPUT = 4
FC_DIAG = 8
FC_WRITE_MULTI = 16
FC_SLOT_CMD = 67        # cmd, slot, addr, len
FC_SYS_EVENTS = 68      # addr, len, rack, module_type
FC_EVENT_INFO = 69      # cmd, slot
FC_CLEAR_EVENTS = 70    # cmd, slot
FC_RTC = 71             # set/read time (rack addr)
FC_RTC_BROADCAST = 72   # set time (calibration slave id)
FC_RTC_READ = 73        # read time
FC_CAL_READ = 81        # read calibration gains

# Diagnostic sub-codes used as handshakes (FC08)
DIAG_CONNECT = 0
DIAG_SUBCODES = (0, 2, 5, 6, 7, 8, 10)

MAX_RETRIES = 3


def crc16(data: bytes) -> int:
    """Modbus CRC16 (poly 0xA001, init 0xFFFF)."""
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def with_crc(payload: bytes) -> bytes:
    """Append CRC low byte first (standard Modbus)."""
    c = crc16(payload)
    return payload + bytes((c & 0xFF, c >> 8))


def check_crc(frame: bytes) -> bool:
    return len(frame) >= 4 and crc16(frame[:-2]) == (frame[-2] | frame[-1] << 8)


def split_word(word: int) -> bytes:
    """VB `splitt`: big-endian 16-bit (two's complement masking)."""
    word &= 0xFFFF
    return bytes((word >> 8, word & 0xFF))


def join_word(hi: int, lo: int) -> int:
    return (hi << 8) | lo


def to_signed16(v: int) -> int:
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


# ── Request builders ───────────────────────────────────────────────────────
def build_fc03(addr: int, address: int, count: int) -> bytes:
    return with_crc(bytes((addr, FC_READ_HOLDING)) + split_word(address) + split_word(count))


def build_fc04(addr: int, address: int, count: int) -> bytes:
    return with_crc(bytes((addr, FC_READ_INPUT)) + split_word(address) + split_word(count))


def build_fc08(addr: int, sub: int, info: int = 0) -> bytes:
    return with_crc(bytes((addr, FC_DIAG)) + split_word(sub) + split_word(info))


def build_fc16(addr: int, address: int, words: List[int]) -> bytes:
    body = bytes((addr, FC_WRITE_MULTI)) + split_word(address) + split_word(len(words)) + bytes((len(words) * 2,))
    for w in words:
        body += split_word(w)
    return with_crc(body)


def build_fc67(addr: int, cmd: int, slot: int, address: int, length: int) -> bytes:
    return with_crc(bytes((addr, FC_SLOT_CMD, cmd & 0xFF, slot & 0xFF)) + split_word(address) + split_word(length))


def build_fc68(addr: int, address: int, length: int, module_type: int) -> bytes:
    # VB overrides slot byte with rack address
    return with_crc(bytes((addr, FC_SYS_EVENTS)) + split_word(address) + split_word(length)
                    + bytes((addr & 0xFF, module_type & 0xFF)))


def build_fc69(addr: int, cmd: int, slot: int) -> bytes:
    return with_crc(bytes((addr, FC_EVENT_INFO, cmd & 0xFF, slot & 0xFF)))


def build_fc70(addr: int, cmd: int, slot: int) -> bytes:
    return with_crc(bytes((addr, FC_CLEAR_EVENTS, cmd & 0xFF, slot & 0xFF)))


def _dt_bytes(dt) -> bytes:
    # order per VB: month, year(2-digit), hour, day, second, minute, 0, 0
    return bytes((dt.month, dt.year % 100, dt.hour, dt.day, dt.second, dt.minute, 0, 0))


def build_fc71(addr: int, set_read: int, dt) -> bytes:
    return with_crc(bytes((addr, FC_RTC, set_read)) + _dt_bytes(dt))


def build_fc72(slave: int, dt) -> bytes:
    return with_crc(bytes((slave, FC_RTC_BROADCAST)) + _dt_bytes(dt))


def build_fc73(slave: int) -> bytes:
    return with_crc(bytes((slave, FC_RTC_READ, 1)))


def build_fc81(slave: int, address: int, length: int) -> bytes:
    return with_crc(bytes((slave, FC_CAL_READ)) + split_word(address) + split_word(length))


# ── Response parsing ───────────────────────────────────────────────────────
@dataclass
class Response:
    ok: bool
    slave: int = 0
    fc: int = 0
    data: bytes = b""
    exception: Optional[int] = None
    error: str = ""

    def words(self) -> List[int]:
        d = self.data
        return [join_word(d[i], d[i + 1]) for i in range(0, len(d) - 1, 2)]


def parse_response(frame: bytes) -> Response:
    if len(frame) < 4:
        return Response(False, error="short frame")
    if not check_crc(frame):
        return Response(False, error="CRC error")
    slave, fc = frame[0], frame[1]
    if fc & 0x80:
        return Response(False, slave, fc & 0x7F, exception=frame[2] if len(frame) > 2 else None,
                        error="exception response")
    body = frame[2:-2]
    if fc in (FC_READ_HOLDING, FC_READ_INPUT):
        n = body[0] if body else 0
        return Response(len(body) - 1 == n, slave, fc, bytes(body[1:]))
    return Response(True, slave, fc, bytes(body))


def expected_length(request: bytes) -> int:
    """Expected full response length for a request (best effort; used by transport)."""
    fc = request[1]
    if fc in (3, 4):
        return 5 + 2 * ((request[4] << 8) | request[5])
    if fc == 8:
        return 8
    if fc == 16:
        return 8
    return 0  # variable, transport reads until idle gap


def f32_le(data: bytes) -> float:
    return struct.unpack("<f", data[:4])[0]


def f32_le_bytes(v: float) -> bytes:
    return struct.pack("<f", v)


def build_fc80(addr: int, address: int, length: int) -> bytes:
    return with_crc(bytes((addr, 80)) + split_word(address) + split_word(length))


CAL_FLOATS_WRITE = 12
CAL_FLOATS_READ = 20


def build_fc81_write(slave: int, gains: List[float], address: int = 0, length: int = 32) -> bytes:
    """gains: g1[4], g2[4], gap_gain[4] as little-endian float32."""
    if len(gains) != CAL_FLOATS_WRITE:
        raise ValueError("calibration write needs 12 float gains")
    body = bytes((slave, FC_CAL_READ)) + split_word(address) + split_word(length)
    for g in gains:
        body += f32_le_bytes(float(g))
    return with_crc(body)
