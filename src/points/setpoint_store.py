"""Persistent setpoint store shared by the 12M/DIS and 6M setpoint dialogs.

Structure: {model: {raw_slot: {channel: {alert, danger, gap_upper, gap_lower, direct_en, gap_en, danger_en}}}}
(raw_slot = UI slot number = VB slot + 1)
"""

_STORE = {"12M/DIS": {}, "6M": {}}


def get(model, slot, ch):
    return _STORE.get(model, {}).get(slot, {}).get(ch)


def put(model, slot, ch, data):
    _STORE.setdefault(model, {}).setdefault(slot, {})[ch] = dict(data)


def clear():
    for k in _STORE:
        _STORE[k] = {}


def all_data():
    return _STORE


class SetpointPersistence:
    """Mixin for SetpointsDialog / SetpointsDialog6M."""

    def _sp_load(self):
        d = get(self._model, self._slot_num, self._channel_num)
        if not d:
            return
        self.direct1_value = d.get("alert", self.direct1_value)
        self.direct2_value = d.get("danger", self.direct2_value)
        self.gap_value = d.get("gap_upper", self.gap_value)
        self.gap_secondary = d.get("gap_lower", self.gap_secondary)
        for attr, key in (("_en_direct1", "direct_en"), ("_en_gap", "gap_en"), ("_en_direct2", "danger_en")):
            w = getattr(self, attr, None)
            if w is not None and key in d:
                w.setChecked(bool(d[key]))

    def _sp_save(self):
        def _chk(attr):
            w = getattr(self, attr, None)
            return bool(w.isChecked()) if w is not None else True
        put(self._model, self._slot_num, self._channel_num, {
            "alert": self.direct1_value, "danger": self.direct2_value,
            "gap_upper": self.gap_value, "gap_lower": self.gap_secondary,
            "direct_en": _chk("_en_direct1"), "gap_en": _chk("_en_gap"), "danger_en": _chk("_en_direct2"),
        })
