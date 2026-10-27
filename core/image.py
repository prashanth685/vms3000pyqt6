"""Rack <-> holding-register image (13001 words; slot n at word n*1024, config card at slot 0)."""
from __future__ import annotations

from typing import List

from .config_card import CARD_WORDS, ConfigCard, decode_card, encode_card
from .model import MT_NONE, MT_RLY_4C, MT_VMM_12M, MT_VMM_6M, RackModel, SlotModel
from .relay_logic import RELAY_WORDS, RelayConfig, decode_relay, encode_relay
from .vmm_codec import FRAME_LEN, HOLDING_WORDS, decode_slot, encode_slot

IMAGE_WORDS = 13001
SLOT_STRIDE = 1024


def addr(slot: int) -> int:
    return slot * SLOT_STRIDE


def bytes_to_words(b: bytes) -> List[int]:
    return [(b[i] << 8) | b[i + 1] for i in range(0, len(b) - 1, 2)]


def words_to_bytes(ws: List[int]) -> bytes:
    return b"".join(bytes(((w >> 8) & 0xFF, w & 0xFF)) for w in ws)


def build_image(rack: RackModel) -> List[int]:
    img = [0] * IMAGE_WORDS
    card = ConfigCard.from_dict(rack.config)
    img[0:CARD_WORDS] = encode_card(card, rack)
    monitored = [1 if rack.slots.get(n) and rack.slots[n].module in (MT_VMM_12M, MT_VMM_6M) else 0
                 for n in range(1, 13)]
    for n in range(1, 12):
        s = rack.slots[n]
        if s.module in (MT_VMM_12M, MT_VMM_6M):
            ws = bytes_to_words(encode_slot(s, n, card.rack_status))
            img[addr(n):addr(n) + len(ws)] = ws
        elif s.module == MT_RLY_4C:
            cfg = RelayConfig.from_dict(s.relay)
            ws = encode_relay(cfg, n, monitored)
            img[addr(n):addr(n) + len(ws)] = ws
    return img


def parse_image(img: List[int]) -> RackModel:
    rack = RackModel()
    card, types, _avail = decode_card(img[0:CARD_WORDS])
    rack.config = card.to_dict()
    rack.rack_slots = card.rack_slots
    rack.alarm_inhibit = card.alarm_inhibit
    for n in range(1, 12):
        mt = types.get(n, 0)
        a = addr(n)
        if mt in (MT_VMM_12M, MT_VMM_6M):
            frame = words_to_bytes(img[a:a + HOLDING_WORDS])
            s = decode_slot(frame, n)
            s.module = mt
            rack.slots[n] = s
        elif mt == MT_RLY_4C:
            cfg, _sid = decode_relay(img[a:a + RELAY_WORDS])
            rack.slots[n] = SlotModel(module=MT_RLY_4C, relay=cfg.to_dict())
    return rack
