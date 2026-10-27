import pytest
from core import modbus_rtu as m
from core.model import RackModel, MT_VMM_12M, MT_VMM_6M, MT_RLY_4C, THRUST
from core.vmm_codec import encode_slot, decode_slot
from core.config_card import ConfigCard, encode_card, decode_card
from core import relay_logic as rl
from core.rcs_file import write_rcs, read_rcs
from core.app_state import AppState
from core import tasks


def test_crc_known_frame():
    assert m.with_crc(bytes([1, 3, 0, 0, 0, 10]))[-2:] == bytes([0xC5, 0xCD])
    assert m.check_crc(m.with_crc(b"\x01\x03\x00\x00\x00\x0a"))


def test_slot_codec_roundtrip():
    r = RackModel()
    s = r.slots[2]
    s.module = MT_VMM_12M
    s.channels[3].kind = s.channels[4].kind = THRUST
    s.channels[1].direct_alert = 4.5
    s.channels[1].delay_alert = 6.0
    frame = encode_slot(s, 2, 0)
    assert len(frame) == 156
    d = decode_slot(frame)
    assert d.channels[3].kind == THRUST
    assert d.channels[1].direct_alert == pytest.approx(4.5, abs=0.01)
    assert d.channels[1].delay_alert == pytest.approx(6.0, abs=0.3)


def test_config_card_roundtrip():
    r = RackModel()
    r.slots[1].module = MT_VMM_6M
    c = ConfigCard(device_name="RACK7", config_password="abc", ip="10.0.0.5")
    c.alarm_inhibit = True
    card, mods, _ = decode_card(encode_card(c, r))
    assert (card.device_name, card.config_password, card.ip) == ("RACK7", "abc", "10.0.0.5")
    assert card.alarm_inhibit and mods.get(1) == MT_VMM_6M
    assert ConfigCard(ip="999.1.1.1").validate()


def test_relay_compile_roundtrip_and_validate():
    expr = "(S2C1A1+S2C2A1)*S5C3A2"
    assert rl.decompile_channel(rl.compile_channel(expr, 1)).replace(" ", "") == "(S2C01A1+S2C02A1)*S5C03A2"
    for bad in ("S2C1A1+", "((S2C1A1)", "S2C1"):
        with pytest.raises(rl.RelayLogicError):
            rl.validate(bad)
    assert rl.evaluate("S1C1A1*S1C2A1+S1C3A1", {(1, 1, 1): True, (1, 2, 1): False, (1, 3, 1): True})


def test_rcs_roundtrip(tmp_path):
    r = RackModel()
    r.slots[3].module = MT_VMM_12M
    r.slots[3].channels[2].direct_danger = 8.0
    p = str(tmp_path / "a.rcs")
    write_rcs(p, r)
    r2 = read_rcs(p)
    assert r2.slots[3].module == MT_VMM_12M
    assert r2.slots[3].channels[2].direct_danger == pytest.approx(8.0, abs=0.01)


def test_simulator_upload_download_events_rtc():
    st = AppState()
    st.rack.slots[2].module = MT_VMM_12M
    st.rack.slots[5].module = MT_RLY_4C
    st.connect_demo()
    res = st.upload()
    assert st.rack.slots[2].module == MT_VMM_12M
    st.download("", [2, 5])
    tasks.set_rtc(st.link)
    assert tasks.read_rtc(st.link).year >= 2020
    assert isinstance(tasks.read_events(st.link, [2]), list)
    st.disconnect()
    with pytest.raises(tasks.TaskError):
        st.require_link()


def test_clipboard():
    st = AppState()
    st.rack.slots[2].module = MT_VMM_6M
    assert st.copy_slot(2) and st.paste_slot(4) and st.rack.slots[4].module == MT_VMM_6M
    assert st.cut_slot(2) and st.rack.slots[2].module == 0
