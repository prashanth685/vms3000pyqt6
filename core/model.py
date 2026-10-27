"""Rack data model. Values are stored in engineering units; codecs convert to wire counts."""
from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field, fields
from typing import Dict, Optional

# module type codes on the wire
MT_NONE, MT_VMM_12M, MT_RLY_4C, MT_VMM_6M = 0, 1, 2, 3

# names used by the existing PyQt6 rack view  (`_slot_data["0_<rawslot>"]`)
UI_DIS, UI_6M, UI_RELAY = "3000/12M/DIS", "3000/6M", "3000/RLY"
SLOT_NUMBERS = range(1, 12)           # VB slots 1..11 (UI raw slot = VB slot + 1)

RADIAL, THRUST = "radial", "thrust"


@dataclass
class ChannelModel:
    kind: str = RADIAL
    active: bool = True
    alert_latch: bool = False
    danger_latch: bool = False
    thrust_dir: bool = False
    direct_alarm_en: bool = True
    gap_alarm_en: bool = True
    direct_danger_en: bool = True
    gap_danger_en: bool = False
    recorder: int = 1                       # 0 none, 1 direct, 2 gap
    direct_range: str = "0-10 mil pp"
    gap_range: str = "-24Vdc"
    # radial: direct_alert/direct_danger; thrust uses upper/lower pairs
    direct_alert: float = 3.0
    direct_danger: float = 6.0
    direct_alert_upper: float = 3.0
    direct_alert_lower: float = -3.0
    direct_danger_upper: float = 6.0
    direct_danger_lower: float = -6.0
    gap_alert_upper: float = 15.6           # volts (magnitude)
    gap_alert_lower: float = 8.4
    gap_danger_upper: float = 15.6
    gap_danger_lower: float = 8.4
    direct_clamp: float = 0.0
    gap_clamp: float = 0.0
    zero_position: float = -9.75            # volts (thrust)
    trip_multiply: float = 1.0
    delay_alert: float = 3.0                # seconds
    delay_danger: float = 1.0

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (d or {}).items() if k in names})


@dataclass
class SlotModel:
    module: int = MT_NONE
    channels: Dict[int, ChannelModel] = field(default_factory=lambda: {i: ChannelModel() for i in range(1, 5)})
    relay: Optional[dict] = None            # relay_logic.RelayConfig.to_dict()

    def pair_types(self):
        return (self.channels[1].kind, self.channels[3].kind)

    def set_pair_type(self, pair: int, kind: str):
        for ch in ((1, 2) if pair == 12 else (3, 4)):
            self.channels[ch].kind = kind

    def to_dict(self):
        return {"module": self.module,
                "channels": {str(k): v.to_dict() for k, v in self.channels.items()},
                "relay": self.relay}

    @classmethod
    def from_dict(cls, d):
        s = cls(module=int(d.get("module", 0)))
        s.channels = {int(k): ChannelModel.from_dict(v) for k, v in (d.get("channels") or {}).items()} or s.channels
        s.relay = d.get("relay")
        return s


@dataclass
class RackModel:
    slots: Dict[int, SlotModel] = field(default_factory=lambda: {i: SlotModel() for i in SLOT_NUMBERS})
    config: dict = field(default_factory=dict)      # config_card.ConfigCard.to_dict()
    rack_address: int = 1
    rack_slots: int = 12                              # 12 (full) or 6 (mini)
    rack_name: str = ""
    alarm_inhibit: bool = False

    def slot(self, n: int) -> SlotModel:
        return self.slots[n]

    def clear(self):
        self.slots = {i: SlotModel() for i in SLOT_NUMBERS}

    def copy_slot(self, n: int) -> SlotModel:
        return copy.deepcopy(self.slots[n])

    def to_dict(self):
        return {"slots": {str(k): v.to_dict() for k, v in self.slots.items()}, "config": self.config,
                "rack_address": self.rack_address, "rack_slots": self.rack_slots,
                "rack_name": self.rack_name, "alarm_inhibit": self.alarm_inhibit}

    @classmethod
    def from_dict(cls, d):
        r = cls()
        for k, v in (d.get("slots") or {}).items():
            r.slots[int(k)] = SlotModel.from_dict(v)
        r.config = d.get("config", {})
        r.rack_address = d.get("rack_address", 1)
        r.rack_slots = d.get("rack_slots", 12)
        r.rack_name = d.get("rack_name", "")
        r.alarm_inhibit = d.get("alarm_inhibit", False)
        return r


def ui_module_name(mt: int) -> Optional[str]:
    return {MT_VMM_12M: UI_DIS, MT_VMM_6M: UI_6M, MT_RLY_4C: UI_RELAY}.get(mt)


def mt_from_ui(name: Optional[str]) -> int:
    if not name:
        return MT_NONE
    if name == UI_DIS:
        return MT_VMM_12M
    if name == UI_6M or "6M" in name:
        return MT_VMM_6M
    if "RLY" in name or "elay" in name:
        return MT_RLY_4C
    return MT_NONE
