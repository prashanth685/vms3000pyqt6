"""Persistent user settings (JSON in the user's home directory)."""
from __future__ import annotations

import json
import os

DEFAULTS = {
    "com_port": "COM1",
    "baud_rate": 9600,
    "parity": "N",
    "data_bits": 8,
    "stop_bits": 1,
    "rack_address": 1,
    "calibration_slave_id": 1,
    "host": "192.168.1.255",
    "tcp_port": 502,
    "timeout": 1.0,
    "last_file": "",
    "recent_files": [],
}


def settings_path() -> str:
    base = os.environ.get("VMS3000_HOME") or os.path.join(os.path.expanduser("~"), ".vms3000")
    return os.path.join(base, "settings.json")


def load() -> dict:
    s = dict(DEFAULTS)
    try:
        with open(settings_path(), encoding="utf-8") as f:
            s.update(json.load(f))
    except (OSError, ValueError):
        pass
    return s


def save(s: dict) -> None:
    p = settings_path()
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2)
    except OSError:
        pass
