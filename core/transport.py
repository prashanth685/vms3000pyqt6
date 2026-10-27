"""Byte transports: pyserial (RS-232/485), RTU-over-TCP, and the in-process simulator."""
from __future__ import annotations

import socket
import time
from typing import Optional

try:
    import serial
    from serial.tools import list_ports
except Exception:      # pragma: no cover
    serial = None
    list_ports = None


class TransportError(Exception):
    pass


class Transport:
    def open(self): ...
    def close(self): ...
    def is_open(self) -> bool: return False
    def transact(self, request: bytes, timeout: float = 1.0) -> Optional[bytes]:
        raise NotImplementedError


def available_ports():
    if list_ports is None:
        return []
    return [p.device for p in list_ports.comports()]


class SerialTransport(Transport):
    """Framing: Modbus RTU silence gap. Reads until `gap` seconds pass with no new bytes."""

    def __init__(self, port: str, baud: int = 9600, parity: str = "N", data_bits: int = 8, stop_bits: int = 1, gap: float = 0.05):
        self.port, self.baud, self.parity, self.data_bits, self.stop_bits, self.gap = port, baud, parity, data_bits, stop_bits, gap
        self._ser = None

    def open(self):
        if serial is None:
            raise TransportError("pyserial is not installed")
        par = {"N": serial.PARITY_NONE, "E": serial.PARITY_EVEN, "O": serial.PARITY_ODD}.get(self.parity.upper()[:1], serial.PARITY_NONE)
        sb = {1: serial.STOPBITS_ONE, 2: serial.STOPBITS_TWO}.get(int(self.stop_bits), serial.STOPBITS_ONE)
        try:
            self._ser = serial.Serial(self.port, self.baud, bytesize=int(self.data_bits), parity=par, stopbits=sb, timeout=0.02, write_timeout=1)
        except Exception as e:
            raise TransportError(f"Cannot open {self.port}: {e}") from e

    def close(self):
        if self._ser:
            try:
                self._ser.close()
            finally:
                self._ser = None

    def is_open(self):
        return bool(self._ser and self._ser.is_open)

    def transact(self, request, timeout=1.0):
        if not self.is_open():
            raise TransportError("Port is not open")
        self._ser.reset_input_buffer()
        self._ser.write(request)
        self._ser.flush()
        buf, deadline, last = b"", time.monotonic() + timeout, None
        while time.monotonic() < deadline:
            chunk = self._ser.read(256)
            if chunk:
                buf += chunk
                last = time.monotonic()
            elif last is not None and time.monotonic() - last >= self.gap:
                break
        return buf or None


class TcpTransport(Transport):
    """Modbus RTU framing carried over a TCP socket (experimental network connect)."""

    def __init__(self, host: str, port: int = 502, gap: float = 0.05):
        self.host, self.port, self.gap = host, port, gap
        self._s = None

    def open(self):
        try:
            self._s = socket.create_connection((self.host, self.port), timeout=3)
        except OSError as e:
            raise TransportError(f"Cannot connect to {self.host}:{self.port}: {e}") from e

    def close(self):
        if self._s:
            try:
                self._s.close()
            finally:
                self._s = None

    def is_open(self):
        return self._s is not None

    def transact(self, request, timeout=1.0):
        if not self._s:
            raise TransportError("Socket is not open")
        self._s.settimeout(self.gap)
        try:
            while self._s.recv(4096):
                pass
        except OSError:
            pass
        self._s.sendall(request)
        buf, deadline, last = b"", time.monotonic() + timeout, None
        while time.monotonic() < deadline:
            try:
                chunk = self._s.recv(4096)
                if not chunk:
                    break
                buf += chunk
                last = time.monotonic()
            except socket.timeout:
                if last is not None:
                    break
            except OSError:
                break
        return buf or None


class SimTransport(Transport):
    def __init__(self, sim):
        self.sim = sim
        self._open = False

    def open(self):
        self._open = True

    def close(self):
        self._open = False

    def is_open(self):
        return self._open

    def transact(self, request, timeout=1.0):
        return self.sim.handle(request)
