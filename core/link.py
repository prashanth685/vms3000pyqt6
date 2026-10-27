"""RackLink: request/response with retries, CRC/slave checks and a traffic log (replaces the VB timer state machines)."""
from __future__ import annotations

import time
from typing import Callable, List, Optional

from . import modbus_rtu as m
from .transport import Transport, TransportError


class LinkError(Exception):
    pass


class NoResponse(LinkError):
    pass


class ProtocolError(LinkError):
    def __init__(self, msg, exception_code: Optional[int] = None):
        super().__init__(msg)
        self.exception_code = exception_code


EXC_TEXT = {1: "Illegal function", 2: "Illegal address", 3: "Illegal length"}


class RackLink:
    def __init__(self, transport: Transport, rack_address: int = 1, timeout: float = 1.0, retries: int = m.MAX_RETRIES,
                 on_traffic: Optional[Callable[[str, bytes], None]] = None):
        self.t = transport
        self.addr = rack_address
        self.timeout = timeout
        self.retries = retries
        self.on_traffic = on_traffic
        self.traffic: List[tuple] = []

    # ---- low level
    def _log(self, direction: str, data: bytes):
        self.traffic.append((time.time(), direction, data))
        del self.traffic[:-500]
        if self.on_traffic:
            try:
                self.on_traffic(direction, data)
            except Exception:
                pass

    def request(self, req: bytes, slave: Optional[int] = None) -> m.Response:
        slave = self.addr if slave is None else slave
        last_err = "no response"
        for _attempt in range(max(1, self.retries)):
            self._log("TX", req)
            try:
                raw = self.t.transact(req, self.timeout)
            except TransportError as e:
                raise LinkError(str(e)) from e
            if not raw:
                continue
            self._log("RX", raw)
            resp = m.parse_response(raw)
            if resp.error == "exception response":
                raise ProtocolError(f"Rack reports: {EXC_TEXT.get(resp.exception, 'exception')}", resp.exception)
            if not resp.ok:
                last_err = resp.error
                continue
            if resp.slave != slave:
                last_err = "wrong slave address"
                continue
            return resp
        if last_err == "no response":
            raise NoResponse("No response from the rack")
        raise ProtocolError(f"Bad response: {last_err}")

    # ---- typed helpers
    def diag(self, sub: int, info: int = 0) -> int:
        """FC08. Echo sub-codes (0,5,7,10) are verified; others return the info word."""
        req = m.build_fc08(self.addr, sub, info)
        r = self.request(req)
        if r.fc != m.FC_DIAG or len(r.data) < 4:
            raise ProtocolError("Malformed diagnostic response")
        if sub in (0, 5, 7, 10) and r.data != req[2:6]:
            raise ProtocolError("Loopback diagnostic failure")
        return (r.data[2] << 8) | r.data[3]

    def read_holding(self, address: int, count: int) -> List[int]:
        r = self.request(m.build_fc03(self.addr, address, count))
        if len(r.data) != count * 2:
            raise ProtocolError("Unexpected register count in response")
        return r.words()

    def read_input(self, address: int, count: int) -> List[int]:
        r = self.request(m.build_fc04(self.addr, address, count))
        if len(r.data) != count * 2:
            raise ProtocolError("Unexpected register count in response")
        return r.words()

    def write_multi(self, address: int, words: List[int]) -> None:
        req = m.build_fc16(self.addr, address, words)
        r = self.request(req)
        if r.data[:4] != req[2:6]:
            raise ProtocolError("Write echo mismatch")
