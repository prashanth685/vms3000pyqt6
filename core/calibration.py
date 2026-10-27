"""Calibration: gains (12 floats written) and live readings (20 floats read), little-endian float32."""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import List


@dataclass
class Calibration:
    gain1: List[float] = field(default_factory=lambda: [1.0] * 4)
    gain2: List[float] = field(default_factory=lambda: [1.0] * 4)
    gap_gain: List[float] = field(default_factory=lambda: [1.0] * 4)
    amp: List[float] = field(default_factory=lambda: [0.0] * 4)      # live readings per channel
    gap: List[float] = field(default_factory=lambda: [0.0] * 4)

    def write_vector(self) -> List[float]:
        return list(self.gain1) + list(self.gain2) + list(self.gap_gain)


def parse_read(data: bytes) -> Calibration:
    """data = float bytes after the byte-count (>= 80 bytes)."""
    if len(data) < 80:
        raise ValueError("calibration response too short")
    f = struct.unpack("<20f", data[:80])
    c = Calibration(list(f[0:4]), list(f[4:8]), list(f[8:12]))
    c.amp = [f[12], f[14], f[16], f[18]]
    c.gap = [f[13], f[15], f[17], f[19]]
    return c


def pack_read(c: Calibration) -> bytes:
    vals = c.gain1 + c.gain2 + c.gap_gain
    for i in range(4):
        vals += [c.amp[i], c.gap[i]]
    return struct.pack("<20f", *vals)


def calc_gain(old_gain: float, measured: float, expected: float) -> float:
    """New gain so that measured*new/old == expected (VB 'Calculate' button semantics)."""
    if measured == 0:
        raise ZeroDivisionError("measured value is zero")
    return round(old_gain * expected / measured, 6)
