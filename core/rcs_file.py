"""`.rcs` configuration file: 13001 decimal words, one per line, each byte XOR 128, written twice."""
from __future__ import annotations

import json
from typing import List

from .image import IMAGE_WORDS, build_image, parse_image
from .model import RackModel

KEY = 0x80


class RcsError(Exception):
    pass


def _enc(text: str) -> bytes:
    return bytes(b ^ KEY for b in text.encode("ascii"))


def _dec(raw: bytes) -> str:
    return bytes(b ^ KEY for b in raw).decode("latin-1")


def write_rcs(path: str, rack: RackModel) -> None:
    img = build_image(rack)
    lines = [_enc(str(v)) for v in img]
    with open(path, "wb") as f:
        for _ in range(2):
            for ln in lines:
                f.write(ln + b"\r\n")


def read_rcs(path: str) -> RackModel:
    with open(path, "rb") as f:
        raw = f.read()
    lines = [ln for ln in raw.replace(b"\r\n", b"\n").split(b"\n")]
    if lines and lines[-1] == b"":
        lines.pop()
    if len(lines) < 2 * IMAGE_WORDS:
        raise RcsError("Configuration file is incomplete or not a VMS-3000 .rcs file")
    try:
        vals = [int(_dec(ln).strip() or 0) for ln in lines[: 2 * IMAGE_WORDS]]
    except ValueError as e:
        raise RcsError("Configuration file is corrupt") from e
    if vals[:IMAGE_WORDS] != vals[IMAGE_WORDS:2 * IMAGE_WORDS]:
        raise RcsError("Configuration file failed the duplicate-copy verification")
    return parse_image([v & 0xFFFF for v in vals[:IMAGE_WORDS]])


def write_json(path: str, rack: RackModel) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rack.to_dict(), f, indent=2)


def read_json(path: str) -> RackModel:
    with open(path, encoding="utf-8") as f:
        return RackModel.from_dict(json.load(f))


def read_any(path: str) -> RackModel:
    """Open a binary VB-compatible .rcs, or the JSON format of the earlier PyQt build."""
    with open(path, "rb") as f:
        head = f.read(1)
    if head in (b"{",):
        d = json.load(open(path, encoding="utf-8"))
        if "slots" in d:
            return RackModel.from_dict(d)
        raise RcsError("Legacy JSON layout is not supported; re-save from the VB or new build")
    return read_rcs(path)
