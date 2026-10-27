from PySide6.QtWidgets import QApplication
from core.app_state import AppState
from rack_area import RackArea
from qt_common import make_fonts
from ui_bridge import model_from_ui, ui_from_model
from points import setpoint_store

_app = QApplication.instance() or QApplication([])


def test_bridge_roundtrip():
    st, ra = AppState(), RackArea(None, make_fonts())
    ra._slot_data.update({"0_2": "3000/12M/DIS", "0_5": "3000/6M", "0_8": "3000/RLY"})
    setpoint_store.put("12M/DIS", 2, 1, {"alert": 4, "danger": 7, "gap_upper": -14, "gap_lower": -9,
                                          "direct_en": True, "gap_en": True, "danger_en": True})
    d = model_from_ui(st, ra).to_dict()
    ui_from_model(st, ra)
    assert model_from_ui(st, ra).to_dict() == d
