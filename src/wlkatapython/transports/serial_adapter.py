"""Adapter that wraps an already-open pyserial port as a Transport.

Used so ``robot.init(serial.Serial(...), adr)`` can store a Transport-shaped
object in ``pSerial`` without taking ownership of the user's port.
``disconnect()`` is intentionally a no-op and will not call ``close()`` on
the wrapped object.
"""

from typing import Optional

from serial import Serial

from .base import Transport


class SerialAdapter(Transport):
    """Wrap a user-owned ``serial.Serial`` instance.

    Args:
        serial_obj: An already-open ``serial.Serial`` port.
    """

    def __init__(self, serial_obj: Serial):
        if not isinstance(serial_obj, Serial):
            raise TypeError(
                f"serial_obj must be serial.Serial, got {type(serial_obj)!r}"
            )
        self.raw: Serial = serial_obj
        self.serial: Serial = serial_obj  # alias

    def connect(self):
        """No-op: the wrapped port is assumed already open by the user."""
        return

    def disconnect(self):
        """No-op: does not close the user-owned port."""
        return

    @property
    def is_connected(self) -> bool:
        return bool(self.raw.is_open)

    def write(self, data: bytes):
        self.raw.write(data)

    def readline(self) -> bytes:
        return self.raw.readline()

    def flushInput(self):
        self.raw.flushInput()

    def flushOutput(self):
        self.raw.flushOutput()

    @property
    def in_waiting(self) -> int:
        return self.raw.in_waiting

    @property
    def timeout(self) -> Optional[float]:
        return self.raw.timeout

    @timeout.setter
    def timeout(self, value: Optional[float]):
        self.raw.timeout = value
