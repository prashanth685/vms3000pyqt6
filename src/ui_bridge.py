"""Bridge between the PyQt6 screens (rack_area slot data + dialog stores) and core.model.RackModel.

UI raw slot = rack slot + 1 (raw slot 1 is the fixed configuration panel).
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.model import (  # noqa: E402
    MT_NONE, MT_RLY_4C, MT_VMM_12M, MT_VMM_6M, RADIAL, THRUST, RackModel, SlotModel, ChannelModel,
    UI_DIS, UI_6M, UI_RELAY, mt_from_ui, ui_module_name, SLOT_NUMBERS)
from core.relay_logic import RelayConfig  # noqa: E402
from points import relay_store, setpoint_store  # noqa: E402
from points.channel_configuration import ChannelConfigurationDialog as CCD  # noqa: E402

_REC = {"NONE": 0, "DIRECT AMPLITUDE": 1, "GAP": 2}
_REC_R = {v: k for k, v in _REC.items()}
_PAIRS = {"1_2": (1, 2), "3_4": (3, 4)}


def _model_key(mt: int) -> str:
    return "6M" if mt == MT_VMM_6M else "12M/DIS"


def _f(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        m = re.search(r"-?\d+(\.\d+)?", str(v or ""))
        return float(m.group()) if m else default


def _range_max(text: str, default=10.0) -> float:
    nums = re.findall(r"\d+(?:\.\d+)?", str(text or ""))
    return float(nums[-1]) if nums else default


def _clamp(v, hi):
    return max(-hi, min(hi, v)) if hi else v


def model_from_ui(app, rack_area) -> RackModel:
    """Build app.rack slots from the screens (config card is left untouched)."""
    rack = app.rack
    rack.clear()
    data = rack_area._slot_data
    for n in SLOT_NUMBERS:
        raw = n + 1
        mt = mt_from_ui(data.get(f"0_{raw}"))
        s = rack.slots[n]
        s.module = mt
        if mt == MT_RLY_4C:
            s.relay = relay_store.get(raw).to_dict()
            continue
        if mt not in (MT_VMM_12M, MT_VMM_6M):
            continue
        key = _model_key(mt)
        for pair, chs in _PAIRS.items():
            ptype = CCD.get_pair_type(key, raw, pair)
            kind = THRUST if ptype in ("Thrust Position", "Axial Vibration") else RADIAL
            for ch in chs:
                s.channels[ch].kind = kind
        for ch in range(1, 5):
            c = s.channels[ch]
            cfg = CCD.get_channel_config(ch, raw, key) or {}
            sp = setpoint_store.get(key, raw, ch) or {}
            c.active = CCD.get_active(key, raw, ch)
            c.thrust_dir = int(cfg.get("transducer_direction", 0) or 0) == 1
            c.alert_latch = bool(cfg.get("alert_latch", c.alert_latch))
            c.danger_latch = bool(cfg.get("danger_latch", c.danger_latch))
            c.direct_range = cfg.get("direct_scale", c.direct_range)
            c.gap_range = cfg.get("gap_scale", c.gap_range)
            c.direct_clamp = _f(cfg.get("direct_clamp"), 0.0)
            c.gap_clamp = _f(cfg.get("gap_clamp"), 0.0)
            c.zero_position = _f(cfg.get("zero_position"), c.zero_position)
            c.recorder = _REC.get(str(cfg.get("recorder_output", "DIRECT AMPLITUDE")).upper(), 1)
            c.delay_alert = _f(cfg.get("alert_delay"), c.delay_alert)
            c.delay_danger = _f(cfg.get("danger_delay"), c.delay_danger)
            c.trip_multiply = _f(cfg.get("trip_multiply"), c.trip_multiply) or 1.0
            hi = _range_max(c.direct_range)
            alert = _clamp(_f(sp.get("alert"), c.direct_alert), hi)
            danger = _clamp(_f(sp.get("danger"), c.direct_danger), hi)
            if c.kind == THRUST:
                c.direct_alert_upper, c.direct_alert_lower = abs(alert), -abs(alert)
                c.direct_danger_upper, c.direct_danger_lower = abs(danger), -abs(danger)
            else:
                c.direct_alert, c.direct_danger = alert, danger
            c.gap_alert_upper = c.gap_danger_upper = abs(_f(sp.get("gap_upper"), -c.gap_alert_upper))
            c.gap_alert_lower = c.gap_danger_lower = abs(_f(sp.get("gap_lower"), -c.gap_alert_lower))
            c.direct_alarm_en = bool(sp.get("direct_en", True))
            c.gap_alarm_en = bool(sp.get("gap_en", True))
            c.direct_danger_en = bool(sp.get("danger_en", True))
    return rack


def ui_from_model(app, rack_area):
    """Push app.rack into the screens (module cards, channel/setpoint/relay stores)."""
    rack = app.rack
    CCD.reset_all()
    setpoint_store.clear()
    relay_store.clear()
    data = rack_area._slot_data
    data.clear()
    for n in SLOT_NUMBERS:
        s = rack.slots[n]
        raw = n + 1
        name = ui_module_name(s.module)
        if not name:
            continue
        data[f"0_{raw}"] = name
        if s.module == MT_RLY_4C:
            relay_store.put(raw, RelayConfig.from_dict(s.relay))
            continue
        key = _model_key(s.module)
        for pair, (a, _b) in _PAIRS.items():
            CCD.set_pair_type(key, raw, pair,
                              "Thrust Position" if s.channels[a].kind == THRUST else "Radial Vibration")
        for ch in range(1, 5):
            c = s.channels[ch]
            CCD.set_active(key, raw, ch, c.active)
            CCD._channel_configs.setdefault(key, {}).setdefault(raw, {})[ch] = {
                "transducer_direction": 1 if c.thrust_dir else 0,
                "direct_scale": c.direct_range, "direct_clamp": c.direct_clamp,
                "gap_scale": c.gap_range, "gap_clamp": c.gap_clamp,
                "zero_position": c.zero_position,
                "alert_latch": c.alert_latch, "danger_latch": c.danger_latch,
                "alert_delay": c.delay_alert, "danger_delay": c.delay_danger,
                "trip_multiply": c.trip_multiply,
                "recorder_output": _REC_R.get(c.recorder, "DIRECT AMPLITUDE"),
            }
            alert = c.direct_alert_upper if c.kind == THRUST else c.direct_alert
            danger = c.direct_danger_upper if c.kind == THRUST else c.direct_danger
            setpoint_store.put(key, raw, ch, {
                "alert": alert, "danger": danger,
                "gap_upper": -abs(c.gap_alert_upper), "gap_lower": -abs(c.gap_alert_lower),
                "direct_en": c.direct_alarm_en, "gap_en": c.gap_alarm_en, "danger_en": c.direct_danger_en})
    rack_area._selected = None
    rack_area.draw()
