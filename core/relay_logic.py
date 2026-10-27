"""Relay module codec (214-word frame) and drive-logic expression compiler.

Per relay channel block (50 words at offsets 0/50/100/150 of the sequence area, which starts at word 14):
  [0]            = n_params*256 + n_steps
  [1..n]         = parameter words:  relay_ch<<12 | slot<<8 | channel<<4 | alert
  [n+1..n+steps] = step words:       operand1<<9 | operand2<<2 | op   (op: 1='*', 2='+')
  [end+1..]      = token nibbles:    '('=1 '+'=2 '*'=3 param=4 ')'=5, four per word (MSB first)

Expression syntax: S<slot>C<ch|##>A<alert> parameters joined by + (OR) and * (AND) with parentheses.
Example: "(S2C01A1 + S2C02A1) * S3C##A2".
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .model import MT_RLY_4C

RELAY_WORDS = 214
SEQ_BASE = 14
BLOCK = 50
MAX_BLOCK_WORDS = 49
_PARAM_RE = re.compile(r"S(\d{1,2})C(##|\d{1,2})A(\d)")
_TOKEN_RE = re.compile(r"\s*(S\d{1,2}C(?:##|\d{1,2})A\d|[()+*])")
_TOKVAL = {"(": 1, "+": 2, "*": 3, "P": 4, ")": 5}


class RelayLogicError(ValueError):
    pass


@dataclass
class RelayChannel:
    active: bool = False
    latching: bool = False
    logic: str = ""


@dataclass
class RelayConfig:
    channels: Dict[int, RelayChannel] = field(default_factory=lambda: {i: RelayChannel() for i in range(1, 5)})
    monitored_slots: List[int] = field(default_factory=lambda: [0] * 12)   # index 0 -> slot1 ... 11 -> slot12

    def to_dict(self):
        return {"channels": {str(k): {"active": v.active, "latching": v.latching, "logic": v.logic}
                             for k, v in self.channels.items()},
                "monitored_slots": list(self.monitored_slots)}

    @classmethod
    def from_dict(cls, d):
        r = cls()
        for k, v in (d or {}).get("channels", {}).items():
            r.channels[int(k)] = RelayChannel(bool(v.get("active")), bool(v.get("latching")), v.get("logic", ""))
        ms = (d or {}).get("monitored_slots")
        if ms:
            r.monitored_slots = list(ms)[:12] + [0] * (12 - len(ms))
        return r


def tokenize(expr: str) -> List[str]:
    expr = expr.strip()
    pos, out = 0, []
    while pos < len(expr):
        m = _TOKEN_RE.match(expr, pos)
        if not m:
            raise RelayLogicError(f"Unexpected text at position {pos + 1}: {expr[pos:pos + 6]!r}")
        out.append(m.group(1))
        pos = m.end()
        while pos < len(expr) and expr[pos].isspace():
            pos += 1
    return out


def validate(expr: str) -> None:
    toks = tokenize(expr)
    depth, prev = 0, None          # prev: 'op','(', 'val', ')' or None
    for t in toks:
        kind = "(" if t == "(" else ")" if t == ")" else "op" if t in "+*" else "val"
        if kind == "(":
            if prev in ("val", ")"):
                raise RelayLogicError("Operator expected before '('")
            depth += 1
        elif kind == ")":
            if prev in (None, "op", "("):
                raise RelayLogicError("Operand expected before ')'")
            depth -= 1
            if depth < 0:
                raise RelayLogicError("Unbalanced ')'")
        elif kind == "op":
            if prev in (None, "op", "("):
                raise RelayLogicError("Operand expected before operator")
        else:
            if prev in ("val", ")"):
                raise RelayLogicError("Operator expected between parameters")
        prev = kind
    if depth:
        raise RelayLogicError("Unbalanced '('")
    if toks and prev in ("op", "("):
        raise RelayLogicError("Expression ends with an operator")


def parse_param(tok: str) -> Tuple[int, int, int]:
    m = _PARAM_RE.fullmatch(tok)
    slot, ch, alert = int(m.group(1)), 0 if m.group(2) == "##" else int(m.group(2)), int(m.group(3))
    if not (1 <= slot <= 15 and 0 <= ch <= 4 and 0 <= alert <= 15):
        raise RelayLogicError(f"Parameter out of range: {tok}")
    return slot, ch, alert


def format_param(slot: int, ch: int, alert: int) -> str:
    return f"S{slot}C{'##' if ch == 0 else f'{ch:02d}'}A{alert}"


def compile_channel(expr: str, relay_channel: int) -> List[int]:
    """Return the 50-word block for one relay channel (zeros for an empty expression)."""
    block = [0] * BLOCK
    expr = expr.strip()
    if not expr:
        return block
    validate(expr)
    toks = tokenize(expr)
    params = [parse_param(t) for t in toks if t not in "()+*"]
    n = len(params)
    for i, (slot, ch, alert) in enumerate(params, 1):
        block[i] = (relay_channel << 12) | (slot << 8) | (ch << 4) | alert
    items: list = []
    pi = 0
    for t in toks:
        if t in "()+*":
            items.append(t)
        else:
            pi += 1
            items.append(pi)
    steps: List[int] = []

    def new_step(left: int, right: int, op: str) -> int:
        steps.append((right << 9) | (left << 2) | (1 if op == "*" else 2))
        return n + len(steps)

    def reduce_flat(seq: list) -> int:
        for op in ("*", "+"):
            while op in seq:
                i = seq.index(op)
                seq[i - 1:i + 2] = [new_step(seq[i - 1], seq[i + 1], op)]
        if len(seq) != 1:
            raise RelayLogicError("Invalid expression")
        return seq[0]

    while ")" in items:
        close = items.index(")")
        open_ = max(i for i in range(close) if items[i] == "(")
        items[open_:close + 1] = [reduce_flat(items[open_ + 1:close])]
    reduce_flat(items)
    end = n + len(steps)
    enc_tokens = [_TOKVAL["P" if t not in "()+*" else t] for t in toks]
    words = []
    for i in range(0, len(enc_tokens), 4):
        g = enc_tokens[i:i + 4] + [0] * (4 - len(enc_tokens[i:i + 4]))
        words.append((g[0] << 12) | (g[1] << 8) | (g[2] << 4) | g[3])
    if end + 1 + len(words) > MAX_BLOCK_WORDS + 1:
        raise RelayLogicError("Drive logic too long for one relay channel")
    block[0] = (n << 8) | len(steps)
    for i, s in enumerate(steps, n + 1):
        block[i] = s
    for j, w in enumerate(words):
        block[end + 1 + j] = w
    return block


def decompile_channel(block: List[int]) -> str:
    """Rebuild the expression text from a 50-word block."""
    hdr = block[0]
    if hdr == 0:
        return ""
    n, steps = hdr >> 8, hdr & 0xFF
    end = n + steps
    toks: List[int] = []
    for w in block[end + 1:]:
        if w == 0:
            break
        toks += [(w >> 12) & 15, (w >> 8) & 15, (w >> 4) & 15, w & 15]
    rev = {1: "(", 2: "+", 3: "*", 5: ")"}
    out, pi = [], 0
    for t in toks:
        if t == 0:
            continue
        if t == 4:
            pi += 1
            if pi > n:
                break
            w = block[pi]
            out.append(format_param((w >> 8) & 15, (w >> 4) & 15, w & 15))
        elif t in rev:
            out.append(rev[t])
    return " ".join(out).replace("( ", "(").replace(" )", ")")


def evaluate(expr: str, states: Dict[Tuple[int, int, int], bool]) -> bool:
    """Evaluate a drive-logic expression against alarm states (used by the simulator / preview)."""
    validate(expr)
    py = []
    for t in tokenize(expr):
        if t == "+":
            py.append(" or ")
        elif t == "*":
            py.append(" and ")
        elif t in "()":
            py.append(t)
        else:
            py.append("True" if states.get(parse_param(t), False) else "False")
    return bool(eval("".join(py), {"__builtins__": {}}, {}))


def encode_relay(cfg: RelayConfig, slot_id: int, monitored: Optional[List[int]] = None) -> List[int]:
    w = [0] * RELAY_WORDS
    w[0] = (slot_id << 8) | MT_RLY_4C
    w[1] = (7 << 8) | (RELAY_WORDS & 0xFF)   # input words=7, holding=214 (fits a byte)
    w[2] = 0
    mon = monitored if monitored is not None else cfg.monitored_slots
    for i in range(6):
        w[5 + i] = ((mon[2 * i] & 0xFF) << 8) | (mon[2 * i + 1] & 0xFF)
    act = lat = 0
    for i in range(1, 5):
        act |= int(cfg.channels[i].active) << (i - 1)
        lat |= int(cfg.channels[i].latching) << (i - 1)
    w[11], w[12] = act, lat
    for i in range(1, 5):
        blk = compile_channel(cfg.channels[i].logic, i)
        base = SEQ_BASE + (i - 1) * BLOCK
        for j, v in enumerate(blk):
            if base + j < RELAY_WORDS:
                w[base + j] = v
    return w


def decode_relay(words: List[int]) -> Tuple[RelayConfig, int]:
    if len(words) < RELAY_WORDS:
        words = list(words) + [0] * (RELAY_WORDS - len(words))
    cfg = RelayConfig()
    for i in range(6):
        cfg.monitored_slots[2 * i], cfg.monitored_slots[2 * i + 1] = words[5 + i] >> 8, words[5 + i] & 0xFF
    for i in range(1, 5):
        ch = cfg.channels[i]
        ch.active = bool((words[11] >> (i - 1)) & 1)
        ch.latching = bool((words[12] >> (i - 1)) & 1)
        base = SEQ_BASE + (i - 1) * BLOCK
        blk = words[base:base + BLOCK]
        blk += [0] * (BLOCK - len(blk))
        ch.logic = decompile_channel(blk)
    return cfg, words[0] >> 8
