"""Engineering-unit <-> raw-count scaling used by the VMS-3000 wire format."""
from __future__ import annotations

MIL_PER_COUNT = 40 / 32767
VOLT_PER_COUNT = 24 / 32767
DELAY_PER_COUNT = 60 / 255
TRIP_PER_COUNT = 10 / 65535
UM_PER_MIL = 25.4

RADIAL_AMP_RANGES = {
    "0-3 mil pp": 3, "0-5 mil pp": 5, "0-10 mil pp": 10, "0-15 mil pp": 15, "0-20 mil pp": 20,
    "0-100 µm pp": 100, "0-150 µm pp": 150, "0-200 µm pp": 200, "0-400 µm pp": 400, "0-500 µm pp": 500,
}
GAP_RANGES = {"-24Vdc": 1, "15-0-15 mil": 1, "25-0-25 mil": 1, "300-0-300 µm": UM_PER_MIL, "600-0-600 µm": UM_PER_MIL}


def bankers_round(x: float) -> int:
    """VB Round(): half-to-even."""
    return int(round(x))


def s16(v: int) -> int:
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def is_um(range_name: str) -> bool:
    return "µm" in str(range_name)


def amp_range_counts(range_name: str) -> int:
    full = RADIAL_AMP_RANGES.get(range_name, 10)
    mils = full / UM_PER_MIL if is_um(range_name) else full
    return bankers_round(mils / MIL_PER_COUNT)


def gap_range_counts(range_name: str) -> int:
    return -bankers_round(24 / VOLT_PER_COUNT)


def amp_divisor(range_name: str) -> float:
    return UM_PER_MIL if is_um(range_name) else 1.0


def gap_divisor(range_name: str) -> float:
    return UM_PER_MIL if is_um(range_name) else 1.0


def eng_to_mils(value: float, range_name: str) -> float:
    return value / amp_divisor(range_name)


def mils_to_eng(value: float, range_name: str) -> float:
    return value * amp_divisor(range_name)


def delay_to_counts(seconds: float) -> int:
    return max(0, min(255, bankers_round(seconds / DELAY_PER_COUNT)))


def counts_to_delay(c: int) -> float:
    return round((c & 0xFF) * DELAY_PER_COUNT, 1)


def trip_to_counts(mult: float) -> int:
    return bankers_round(mult / TRIP_PER_COUNT) & 0xFFFF


def counts_to_trip(c: int) -> float:
    return round((c & 0xFFFF) * TRIP_PER_COUNT, 2)
