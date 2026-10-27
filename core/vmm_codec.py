"""VMM slot frame codec: 78 holding words = 156 bytes, bit-exact with the VB6 Create_data_frame / read_setpoints."""
from __future__ import annotations

from typing import List

from .model import ChannelModel, RADIAL, THRUST, SlotModel, MT_VMM_12M, MT_VMM_6M
from .scaling import (MIL_PER_COUNT, VOLT_PER_COUNT, UM_PER_MIL, RADIAL_AMP_RANGES, GAP_RANGES,
                      amp_range_counts, bankers_round, counts_to_delay, counts_to_trip, delay_to_counts,
                      is_um, s16, trip_to_counts)

FRAME_LEN = 156
HOLDING_WORDS = 78
INPUT_WORDS = 14
_ADR = (1, 0, 3, 2)          # byte swap for delay bytes and recorder bytes
TRANSDUCER_SENS = 7874
THRUST_AMP_RANGES = RADIAL_AMP_RANGES
UNIT_MIL, UNIT_UM = 0, 1


def _w16(buf: bytearray, off: int, val: int):
    val &= 0xFFFF
    buf[off] = val >> 8
    buf[off + 1] = val & 0xFF


def _r16(buf, off: int) -> int:
    return (buf[off] << 8) | buf[off + 1]


def _div(rng: str) -> float:
    return UM_PER_MIL if is_um(rng) else 1.0


def _mil_counts(eng: float, rng: str) -> int:
    return bankers_round(eng / _div(rng) / MIL_PER_COUNT)


def _volt_counts(v: float) -> int:
    return bankers_round(v / VOLT_PER_COUNT)


def _counts_mil(c: int, rng: str) -> float:
    return round(c * MIL_PER_COUNT * _div(rng), 3)


def _bits(word: int) -> List[int]:
    return [(word >> i) & 1 for i in range(16)]


def _range_from_counts(counts: int, unit: int) -> str:
    """Reverse of the amplitude range map (full-scale counts -> label)."""
    mils = counts * MIL_PER_COUNT
    if unit == UNIT_UM:
        target = mils * UM_PER_MIL
        best = min((k for k in RADIAL_AMP_RANGES if "µm" in k), key=lambda k: abs(RADIAL_AMP_RANGES[k] - target))
    else:
        best = min((k for k in RADIAL_AMP_RANGES if "mil" in k), key=lambda k: abs(RADIAL_AMP_RANGES[k] - mils))
    return best


def encode_slot(slot: SlotModel, slot_id: int, rack_status: int = 0) -> bytes:
    """Build the 156-byte holding image for one VMM slot."""
    b = bytearray(FRAME_LEN)
    b[0] = slot_id
    b[1] = slot.module
    b[2], b[3], b[4], b[5] = INPUT_WORDS, HOLDING_WORDS, 0, 0
    # NOTE: VB writes length bytes as slot_info: input_register_length=14, holding=78
    _w16(b, 6, rack_status)
    ch = slot.channels
    p12 = 1 if ch[1].kind == RADIAL else 2
    p34 = 1 if ch[3].kind == RADIAL else 2
    b[11], b[10] = p12, p34
    active = en = 0
    for i in range(4):
        c = ch[i + 1]
        active |= (c.active << i) | (c.alert_latch << (8 + i)) | (c.danger_latch << (12 + i))
        if c.kind == THRUST:
            active |= c.thrust_dir << (4 + i)
        en |= (c.direct_alarm_en << i) | (c.gap_alarm_en << (4 + i)) | (c.direct_danger_en << (8 + i)) | (c.gap_danger_en << (12 + i))
    _w16(b, 12, active)
    _w16(b, 14, en)
    b[17], b[16], b[19], b[18] = (ch[1].recorder, ch[2].recorder, ch[3].recorder, ch[4].recorder)

    rows = [[0] * 4 for _ in range(18)]
    for i in range(4):
        c = ch[i + 1]
        rg = c.direct_range
        rows[0][i] = TRANSDUCER_SENS
        rows[1][i] = amp_range_counts(rg)
        rows[2][i] = -_volt_counts(24)
        if c.kind == RADIAL:
            rows[3][i] = _mil_counts(c.direct_alert, rg)
            rows[4][i] = 0
            rows[7][i] = _mil_counts(c.direct_danger, rg)
            rows[8][i] = 0
            rows[13][i] = 0
            rows[14][i] = trip_to_counts(c.trip_multiply)
        else:
            rows[3][i] = _mil_counts(c.direct_alert_upper, rg)
            rows[4][i] = _mil_counts(c.direct_alert_lower, rg)
            rows[7][i] = _mil_counts(c.direct_danger_upper, rg)
            rows[8][i] = _mil_counts(c.direct_danger_lower, rg)
            rows[13][i] = bankers_round(c.zero_position / VOLT_PER_COUNT)
            rows[14][i] = 0
        rows[5][i] = -_volt_counts(c.gap_alert_upper)
        rows[6][i] = -_volt_counts(c.gap_alert_lower)
        rows[9][i] = -_volt_counts(c.gap_danger_upper)
        rows[10][i] = -_volt_counts(c.gap_danger_lower)
        rows[11][i] = _mil_counts(c.direct_clamp, rg) if c.direct_clamp else 0
        rows[12][i] = _volt_counts(c.gap_clamp) if c.gap_clamp else 0
        b[140 + _ADR[i]] = delay_to_counts(c.delay_alert)
        b[144 + _ADR[i]] = delay_to_counts(c.delay_danger)
        units = UNIT_UM if is_um(rg) else UNIT_MIL
        b[148 + i * 2] = units
        b[149 + i * 2] = _parameter_code(c)
    for idx in range(15):
        for i in range(4):
            _w16(b, 20 + 8 * idx + i * 2, rows[idx][i])
    return bytes(b)


def _parameter_code(c: ChannelModel) -> int:
    return 0


def decode_slot(frame: bytes, slot_id: int = 0) -> SlotModel:
    """Inverse of encode_slot. `frame` is the 156 data bytes (without addr/fc/bytecount/crc)."""
    if len(frame) < FRAME_LEN:
        raise ValueError(f"slot frame too short: {len(frame)}")
    b = frame
    s = SlotModel(module=b[1])
    p12, p34 = b[11], b[10]
    kinds = [RADIAL if p12 == 1 else THRUST] * 2 + [RADIAL if p34 == 1 else THRUST] * 2
    active = _bits(_r16(b, 12))
    en = _bits(_r16(b, 14))
    rec = {1: b[17], 2: b[16], 3: b[19], 4: b[18]}
    for i in range(4):
        c = ChannelModel(kind=kinds[i])
        c.active = bool(active[i])
        c.alert_latch = bool(active[8 + i])
        c.danger_latch = bool(active[12 + i])
        c.thrust_dir = bool(active[4 + i]) if c.kind == THRUST else False
        c.direct_alarm_en, c.gap_alarm_en = bool(en[i]), bool(en[4 + i])
        c.direct_danger_en, c.gap_danger_en = bool(en[8 + i]), bool(en[12 + i])
        c.recorder = rec[i + 1]
        units = b[148 + i * 2]
        full = _r16(b, 20 + 8 * 1 + i * 2)
        c.direct_range = _range_from_counts(full, units)
        c.gap_range = "-24Vdc"
        rg = c.direct_range

        def row(n):
            return _r16(b, 20 + 8 * n + i * 2)

        if c.kind == RADIAL:
            c.direct_alert = _counts_mil(s16(row(3)), rg)
            c.direct_danger = _counts_mil(s16(row(7)), rg)
            c.trip_multiply = counts_to_trip(row(14))
        else:
            c.direct_alert_upper = _counts_mil(s16(row(3)), rg)
            c.direct_alert_lower = _counts_mil(s16(row(4)), rg)
            c.direct_danger_upper = _counts_mil(s16(row(7)), rg)
            c.direct_danger_lower = _counts_mil(s16(row(8)), rg)
            c.zero_position = round(s16(row(13)) * VOLT_PER_COUNT, 2)
        c.gap_alert_upper = round(-s16(row(5)) * VOLT_PER_COUNT, 2)
        c.gap_alert_lower = round(-s16(row(6)) * VOLT_PER_COUNT, 2)
        c.gap_danger_upper = round(-s16(row(9)) * VOLT_PER_COUNT, 2)
        c.gap_danger_lower = round(-s16(row(10)) * VOLT_PER_COUNT, 2)
        c.direct_clamp = _counts_mil(s16(row(11)), rg)
        c.gap_clamp = round(s16(row(12)) * VOLT_PER_COUNT, 2)
        c.delay_alert = counts_to_delay(b[140 + _ADR[i]])
        c.delay_danger = counts_to_delay(b[144 + _ADR[i]])
        s.channels[i + 1] = c
    return s
