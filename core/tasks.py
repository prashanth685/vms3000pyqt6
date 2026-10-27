"""High-level rack workflows: connect, upload, download, events, RTC, calibration. Run them from a worker thread."""
from __future__ import annotations

import datetime
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from . import modbus_rtu as m
from .calibration import Calibration, parse_read
from .config_card import ConfigCard, decode_card, encode_card, CARD_WORDS
from .events import CHUNK_BYTES, RECORD_LEN, EventRecord, parse_records
from .image import IMAGE_WORDS, addr, build_image, parse_image
from .link import LinkError, NoResponse, ProtocolError, RackLink
from .model import MT_RLY_4C, MT_VMM_12M, MT_VMM_6M, MT_NONE, RackModel

Progress = Callable[[int, str], None]


class TaskError(Exception):
    pass


class PasswordError(TaskError):
    pass


class Cancelled(TaskError):
    pass


def _noop(p, t): ...


@dataclass
class UploadResult:
    rack: RackModel
    mismatches: Dict[int, int] = field(default_factory=dict)       # slot -> actual slot id found in module


def _cancel_check(cancel):
    if cancel and cancel():
        raise Cancelled("Cancelled by user")


def _pass_ok(entered: str, stored: str) -> bool:
    return entered == stored


def connect(link: RackLink, connect_password: str = "", progress: Progress = _noop) -> ConfigCard:
    """FC08 loopback -> FC03(0,60) -> compare connect password (VB Connect_to_Rack)."""
    progress(20, "Testing communication link...")
    try:
        link.diag(0, 20)
    except NoResponse:
        raise TaskError("NO RACK FOUND, MAKE SURE THE RACK IS CONNECTED AND TURNED ON")
    progress(50, "Communication test passed...")
    progress(75, "Verifying connect password...")
    try:
        words = link.read_holding(0, CARD_WORDS - 1)
    except LinkError as e:
        raise TaskError(f"FAILED TO READ THE CONFIGURATION DATA FROM THE RACK ({e})")
    card, _t, _a = decode_card(words + [0])
    if not _pass_ok(connect_password, card.connect_password):
        raise PasswordError("Connect password incorrect, please enter the proper password and retry")
    progress(100, "Connected")
    return card


def check_connection(link: RackLink) -> bool:
    try:
        link.diag(0, 20)
        return True
    except LinkError:
        return False


def read_slot_info(link: RackLink, progress: Progress = _noop, cancel=None) -> Dict[int, int]:
    """FC08 7 -> poll FC08 8 (bit12 wait, bit13 done) -> FC04(0,33). Returns {slot: module_type}."""
    progress(10, "Initiating slot read...")
    link.diag(7, 0)
    for i in range(60):
        _cancel_check(cancel)
        info = link.diag(8, 0)
        progress(min(60, 20 + i * 2), "Reading from rack...")
        if info & (1 << 13):
            break
        if not info & (1 << 12):
            time.sleep(0.05)
    else:
        raise TaskError("Rack read failure (timed out waiting for slot scan)")
    progress(70, "Retrieving slot details...")
    words = link.read_input(0, 33)
    _card, types, _a = decode_card(words + [0] * 28)
    progress(100, "Done")
    return types


def upload(link: RackLink, progress: Progress = _noop, cancel=None) -> UploadResult:
    types = read_slot_info(link, lambda p, t: progress(p // 4, t), cancel)
    progress(25, "Initiating rack upload...")
    link.diag(5, 0)
    for _ in range(60):
        _cancel_check(cancel)
        info = link.diag(6, 0)
        if info == 2:
            break
        if info == 4:
            raise TaskError("Rack read failure")
        time.sleep(0.05)
    else:
        raise TaskError("Rack did not finish preparing the upload")
    img = [0] * IMAGE_WORDS
    progress(35, "Uploading configuration data...")
    img[0:CARD_WORDS - 1] = link.read_holding(0, CARD_WORDS - 1)
    slots = [n for n in range(1, 12) if types.get(n)]
    for k, n in enumerate(slots):
        _cancel_check(cancel)
        pct = 35 + int(60 * (k + 1) / max(1, len(slots)))
        t = types[n]
        base = addr(n)
        if t in (MT_VMM_12M, MT_VMM_6M):
            progress(pct, f"Uploading slot {n}...")
            img[base:base + 78] = link.read_holding(base, 78)
        elif t == MT_RLY_4C:
            progress(pct, f"Uploading relay slot {n}...")
            img[base:base + 107] = link.read_holding(base, 107)
            img[base + 107:base + 214] = link.read_holding(base + 107, 107)
    # the config card in the image must describe the modules actually read
    live = link.read_input(0, 33)
    img[0:33] = live
    rack = parse_image(img)
    mism = {}
    for n in slots:
        hdr = img[addr(n)]
        if (hdr >> 8) != n and (hdr >> 8) != 0:
            mism[n] = hdr >> 8
    progress(100, "Upload complete")
    return UploadResult(rack, mism)


def verify_download_password(link: RackLink, config_password: str) -> None:
    words = link.read_holding(0, CARD_WORDS - 1)
    card, _t, _a = decode_card(words + [0])
    if not _pass_ok(config_password, card.config_password):
        raise PasswordError("Configuration password incorrect, please type the correct password and retry")


def _wait_write(link: RackLink, slot_label, cancel=None):
    """FC08 sub 2: bit0 wait, bit1 complete, bit2 fail, bit3 slot conflict (VB verify_diagnostic_register)."""
    for _ in range(80):
        _cancel_check(cancel)
        info = link.diag(2, 0)
        if info & 1:
            time.sleep(0.05)
            continue
        if info & 2:
            return
        if info & 4:
            raise TaskError(f"Download failed for slot {slot_label}. Download process aborted.")
        if info & 8:
            raise TaskError(f"Slot {slot_label} conflict. Download process aborted.")
    raise TaskError(f"Download failed for slot {slot_label} (timeout)")


def download(link: RackLink, rack: RackModel, config_password: str = "", slots: Optional[List[int]] = None,
             progress: Progress = _noop, cancel=None) -> None:
    progress(3, "Verifying password...")
    verify_download_password(link, config_password)
    img = build_image(rack)
    progress(5, "Downloading configuration data...")
    link.write_multi(0, img[0:CARD_WORDS - 1])
    _wait_write(link, 0, cancel)
    todo = [n for n in range(1, 12) if rack.slots[n].module != MT_NONE and (slots is None or n in slots)]
    for k, n in enumerate(todo):
        _cancel_check(cancel)
        pct = 10 + int(88 * (k + 1) / max(1, len(todo)))
        base = addr(n)
        mt = rack.slots[n].module
        if mt in (MT_VMM_12M, MT_VMM_6M):
            progress(pct, f"Downloading slot {n}...")
            link.write_multi(base, img[base:base + 78])
            _wait_write(link, n, cancel)
        elif mt == MT_RLY_4C:
            progress(pct, f"Downloading relay slot {n}...")
            link.write_multi(base, img[base:base + 114])
            _wait_write(link, n, cancel)
            link.write_multi(base + 114, img[base + 114:base + 214])
            _wait_write(link, n, cancel)
    progress(100, "Download complete")


# ── RTC ────────────────────────────────────────────────────────────────
def read_rtc(link: RackLink) -> datetime.datetime:
    r = link.request(m.build_fc71(link.addr, 1, datetime.datetime.now()))
    d = r.data                # [0, month, year, hour, day, second, minute]
    if len(d) < 7:
        raise TaskError("Malformed date/time response")
    month, year, hour, day, sec, minute = d[1:7]
    try:
        return datetime.datetime(2000 + year, month, day, hour, minute, sec)
    except ValueError as e:
        raise TaskError(f"Rack returned an invalid date/time: {e}")


def set_rtc(link: RackLink, when: Optional[datetime.datetime] = None) -> None:
    when = when or datetime.datetime.now()
    link.request(m.build_fc71(link.addr, 0, when))


# ── Calibration ────────────────────────────────────────────────────────
def read_calibration(link: RackLink) -> Calibration:
    r = link.request(m.build_fc80(link.addr, 0, 32))
    return parse_read(r.data[1:] if len(r.data) >= 81 else r.data)


def write_calibration(link: RackLink, cal: Calibration, slave: Optional[int] = None) -> None:
    slave = link.addr if slave is None else slave
    link.request(m.build_fc81_write(slave, cal.write_vector()), slave=slave)


# ── Events ─────────────────────────────────────────────────────────────
def read_events(link: RackLink, slots: List[int], progress: Progress = _noop, cancel=None) -> List[EventRecord]:
    out: List[EventRecord] = []
    for k, slot in enumerate(slots):
        _cancel_check(cancel)
        base = int(100 * k / max(1, len(slots)))
        progress(base, f"Reading event log length for slot {slot}...")
        r = link.request(m.build_fc69(link.addr, 1, slot))
        for _ in range(40):
            r = link.request(m.build_fc69(link.addr, 2, slot))
            st = (r.data[1] << 8) | r.data[2] if len(r.data) >= 3 else 0
            st = (r.data[0] << 8) | r.data[1] if len(r.data) == 2 else st
            if st & 1:
                time.sleep(0.05)
                continue
            if st & 2:
                break
            if st & 4:
                raise TaskError(f"Unable to get the event log length from slot {slot}")
        r = link.request(m.build_fc69(link.addr, 0, slot))
        d = r.data
        alarm_len = d[4] | (d[5] << 8) if len(d) >= 6 else 0
        if alarm_len == 0:
            continue
        link.request(m.build_fc67(link.addr, 1, slot, 0, 127))
        for _ in range(40):
            r = link.request(m.build_fc67(link.addr, 2, slot, 0, 127))
            st = (r.data[1] << 8) | r.data[2] if len(r.data) >= 3 else 0
            if st & 1:
                time.sleep(0.05)
                continue
            if st & 2:
                break
            if st & 4:
                raise TaskError(f"Unable to retrieve the event log from slot {slot}")
        raw = b""
        for q in range((alarm_len + CHUNK_BYTES - 1) // CHUNK_BYTES):
            _cancel_check(cancel)
            r = link.request(m.build_fc67(link.addr, 0, slot, q * CHUNK_BYTES, 127))
            ln = r.data[1]
            raw += r.data[2:2 + ln]
            progress(min(99, base + 5), f"Reading events from slot {slot}...")
        out += parse_records(raw)
    progress(100, "Event log read complete")
    return out


def clear_events(link: RackLink, slots: List[int], system: bool = False, progress: Progress = _noop) -> None:
    for k, slot in enumerate(slots):
        progress(int(100 * k / max(1, len(slots))), f"Clearing event log for slot {slot}...")
        link.request(m.build_fc70(link.addr, 1 if system else 0, slot))
    progress(100, "Event log cleared")
