"""UART transport via pyserial.

Implements the same method names ``WLKATA_UART`` uses on ``pSerial``.
"""

from typing import Optional

import serial

from .base import Transport


class UartTransport(Transport):
    """Serial/UART transport wrapping a pyserial ``Serial`` instance.

    Args:
        port: Serial port name (e.g. ``"COM4"`` or ``"/dev/ttyUSB0"``).
        baudrate: Baud rate. Defaults to 115200.
        timeout: Read timeout in seconds. Defaults to 1. ``None`` waits forever.
    """

    def __init__(self, port: str, baudrate: int = 115200, timeout: Optional[float] = 1):
        self.port = port
        self.baudrate = baudrate
        self._timeout = timeout
        self._serial: Optional[serial.Serial] = None

    def connect(self):
        if self.is_connected:
            return
        self._serial = serial.Serial(self.port, self.baudrate, timeout=self._timeout)

    def disconnect(self):
        if self._serial is not None and self._serial.is_open:
            self._serial.close()
        self._serial = None

    @property
    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def _require_connected(self):
        if not self.is_connected:
            raise RuntimeError("UartTransport is not connected; call connect() first")

    def write(self, data: bytes):
        self._require_connected()
        self._serial.write(data)

    def readline(self) -> bytes:
        self._require_connected()
        return self._serial.readline()

    def flushInput(self):
        self._require_connected()
        self._serial.flushInput()

    def flushOutput(self):
        self._require_connected()
        self._serial.flushOutput()

    @property
    def in_waiting(self) -> int:
        self._require_connected()
        return self._serial.in_waiting

    @property
    def timeout(self) -> Optional[float]:
        if self._serial is not None:
            return self._serial.timeout
        return self._timeout

    @timeout.setter
    def timeout(self, value: Optional[float]):
        self._timeout = value
        if self._serial is not None:
            self._serial.timeout = value
