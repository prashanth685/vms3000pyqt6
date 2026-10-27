"""Persistent relay configuration store: {raw_slot: RelayConfig dict}. Used by RelayConfigDialog and the model bridge."""
import copy
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.relay_logic import RelayConfig   # noqa: E402

_STORE = {}


def get(raw_slot) -> RelayConfig:
    return RelayConfig.from_dict(copy.deepcopy(_STORE.get(raw_slot)))


def put(raw_slot, cfg: RelayConfig):
    _STORE[raw_slot] = cfg.to_dict()


def has(raw_slot) -> bool:
    return raw_slot in _STORE


def remove(raw_slot):
    _STORE.pop(raw_slot, None)


def clear():
    _STORE.clear()


def all_data():
    return _STORE
