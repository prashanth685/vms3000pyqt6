"""Configuration-card (slot 0) register image: 61 words. Layout from VB `download_configuration`/`upload_configuration`."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List

from .model import MT_NONE, MT_VMM_12M, MT_VMM_6M, MT_RLY_4C, RackModel

CARD_WORDS = 61
RACKSTATUS_ALARM_INHIBIT = 1 << 3
RACKSTATUS_TRIP_MULTIPLY = 1 << 4
# Word layout
W_AVAIL, W_SLOTS, W_CFG_PW, W_CONN_PW, W_CFG_ID, W_DEV_NAME = 0, 1, 34, 38, 42, 46
W_IP, W_SUBNET, W_GATEWAY, W_PORT, W_RACK_TYPE, W_RACK_STATUS, W_SECURITY = 50, 52, 54, 56, 58, 59, 60

# (type, holding_words, input_words) per module type
SLOT_INFO = {MT_VMM_12M: (78, 14), MT_VMM_6M: (78, 14), MT_RLY_4C: (214, 7)}

SECURITY_BITS = ["Upload password", "Download password", "Connect password", "Event log clear password",
                 "Calibration password", "Time set password"]   # bits 0-5 (labels are descriptive only)


def _pack_text(s: str, words: int = 4) -> List[int]:
    raw = s.encode("latin-1", "replace")[: words * 2].ljust(words * 2, b"\0")
    return [(raw[i] << 8) | raw[i + 1] for i in range(0, words * 2, 2)]


def _unpack_text(ws: List[int]) -> str:
    raw = b"".join(bytes((w >> 8, w & 0xFF)) for w in ws)
    return raw.rstrip(b"\0").decode("latin-1")


def _ip_to_words(ip: str) -> List[int]:
    o = [int(x) & 0xFF for x in ip.split(".")]
    return [(o[0] << 8) | o[1], (o[2] << 8) | o[3]]


def _words_to_ip(ws: List[int]) -> str:
    return ".".join(str(x) for x in (ws[0] >> 8, ws[0] & 255, ws[1] >> 8, ws[1] & 255))


@dataclass
class ConfigCard:
    config_password: str = ""
    connect_password: str = ""
    config_id: str = ""
    device_name: str = "RACK0001"
    ip: str = "192.168.1.255"
    subnet: str = "255.255.255.0"      # VB default 255.255.255.1 was a bug
    gateway: str = "192.168.1.1"
    service_port: int = 502
    rack_type_size: int = 785          # bits 8-9 system, 4-5 rack size, 0-1 interface
    rack_status: int = 0
    security: int = 1

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ConfigCard":
        c = cls()
        for k, v in (d or {}).items():
            if hasattr(c, k):
                setattr(c, k, v)
        return c

    # ── flags ───────────────────────────────────────────────────────────
    @property
    def alarm_inhibit(self) -> bool:
        return bool(self.rack_status & RACKSTATUS_ALARM_INHIBIT)

    @alarm_inhibit.setter
    def alarm_inhibit(self, v: bool):
        self.rack_status = (self.rack_status | RACKSTATUS_ALARM_INHIBIT) if v else (self.rack_status & ~RACKSTATUS_ALARM_INHIBIT)

    @property
    def trip_multiply(self) -> bool:
        return bool(self.rack_status & RACKSTATUS_TRIP_MULTIPLY)

    @trip_multiply.setter
    def trip_multiply(self, v: bool):
        self.rack_status = (self.rack_status | RACKSTATUS_TRIP_MULTIPLY) if v else (self.rack_status & ~RACKSTATUS_TRIP_MULTIPLY)

    @property
    def rack_slots(self) -> int:
        return {16: 12, 32: 6}.get(self.rack_type_size & 0x30, 12)

    def validate(self) -> List[str]:
        errs = []
        for name in ("ip", "subnet", "gateway"):
            try:
                parts = [int(x) for x in getattr(self, name).split(".")]
                if len(parts) != 4 or any(not 0 <= p <= 255 for p in parts):
                    raise ValueError
            except ValueError:
                errs.append(f"Invalid {name} address")
        if not 0 <= self.service_port <= 65535:
            errs.append("Service port must be 0-65535")
        for n in ("config_password", "connect_password", "device_name"):
            if len(getattr(self, n)) > 8:
                errs.append(f"{n} max 8 characters")
        return errs


def encode_card(card: ConfigCard, rack: RackModel) -> List[int]:
    w = [0] * CARD_WORDS
    avail = 0
    for n in range(1, 12):
        mt = rack.slots[n].module
        if mt != MT_NONE:
            avail |= 1 << (n - 1)
            hold, inp = SLOT_INFO[mt]
            b = (n, mt, inp, hold, 0, 0)
            base = W_SLOTS + (n - 1) * 3
            w[base], w[base + 1], w[base + 2] = (b[0] << 8) | b[1], (b[2] << 8) | b[3], (b[4] << 8) | b[5]
    # VB layout: word0 = avail mask, then bytes 2.. hold 6 bytes per slot -> words 1..33
    w[W_AVAIL] = avail
    w[W_CFG_PW:W_CFG_PW + 4] = _pack_text(card.config_password)
    w[W_CONN_PW:W_CONN_PW + 4] = _pack_text(card.connect_password)
    w[W_CFG_ID:W_CFG_ID + 4] = _pack_text(card.config_id)
    w[W_DEV_NAME:W_DEV_NAME + 4] = _pack_text(card.device_name)
    w[W_IP:W_IP + 2] = _ip_to_words(card.ip)
    w[W_SUBNET:W_SUBNET + 2] = _ip_to_words(card.subnet)
    w[W_GATEWAY:W_GATEWAY + 2] = _ip_to_words(card.gateway)
    w[W_PORT:W_PORT + 2] = [0, card.service_port & 0xFFFF]
    w[W_RACK_TYPE], w[W_RACK_STATUS], w[W_SECURITY] = card.rack_type_size & 0xFFFF, card.rack_status & 0xFFFF, card.security & 0xFFFF
    return w


def decode_card(words: List[int]):
    """Returns (ConfigCard, {slot: module_type}, avail_mask)."""
    if len(words) < CARD_WORDS:
        words = list(words) + [0] * (CARD_WORDS - len(words))
    c = ConfigCard()
    c.config_password = _unpack_text(words[W_CFG_PW:W_CFG_PW + 4])
    c.connect_password = _unpack_text(words[W_CONN_PW:W_CONN_PW + 4])
    c.config_id = _unpack_text(words[W_CFG_ID:W_CFG_ID + 4])
    c.device_name = _unpack_text(words[W_DEV_NAME:W_DEV_NAME + 4])
    c.ip = _words_to_ip(words[W_IP:W_IP + 2])
    c.subnet = _words_to_ip(words[W_SUBNET:W_SUBNET + 2])
    c.gateway = _words_to_ip(words[W_GATEWAY:W_GATEWAY + 2])
    c.service_port = words[W_PORT + 1]
    c.rack_type_size, c.rack_status, c.security = words[W_RACK_TYPE], words[W_RACK_STATUS], words[W_SECURITY]
    types: Dict[int, int] = {}
    for n in range(1, 12):
        base = W_SLOTS + (n - 1) * 3
        types[n] = words[base] & 0xFF if False else (words[base] & 0xFF)   # low byte of first word = module_type
    return c, types, words[W_AVAIL]
