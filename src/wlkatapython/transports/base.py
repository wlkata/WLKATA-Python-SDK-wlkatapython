"""Abstract base class for WLKATA robot transport layers.

The I/O method names match the pyserial ``Serial`` surface used by
``WLKATA_UART`` (``pSerial``), so each protocol must implement the same
calls the robot library already makes:

- ``write(data)``
- ``readline()``
- ``in_waiting``
- ``flushInput()``
- ``flushOutput()``
- ``timeout`` (get and set)

Lifecycle helpers:

- ``connect()`` / ``disconnect()``
- ``is_connected``
"""

from abc import ABC, abstractmethod
from typing import Optional


class Transport(ABC):
    """Serial-compatible communication interface for all transports.

    Concrete implementations handle UART, WiFi, and BLE specifics while
    exposing the same method names the robot layer uses on ``pSerial``.
    """

    @abstractmethod
    def connect(self):
        """Open the connection to the robot."""

    @abstractmethod
    def disconnect(self):
        """Close the connection to the robot.

        For user-owned serial wrappers (``SerialAdapter``), this may be a
        no-op so the caller's port is not closed unexpectedly.
        """

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Whether the transport currently has an open link."""

    @abstractmethod
    def write(self, data: bytes):
        """Write raw bytes to the robot.

        Args:
            data: Raw bytes to transmit (typically a G-code line ending in ``\\r\\n``).
        """

    @abstractmethod
    def readline(self) -> bytes:
        """Read one line of bytes from the robot (up to and including ``\\n``).

        Blocking behavior is controlled by ``timeout`` (same idea as pyserial):
        wait up to ``timeout`` seconds; ``None`` means wait forever.

        Returns:
            Raw bytes of the received line, including the trailing ``\\n`` when
            a full line is available. May return a partial or empty result on
            timeout, depending on the backend.
        """

    @abstractmethod
    def flushInput(self):
        """Discard any buffered incoming (RX) data."""

    @abstractmethod
    def flushOutput(self):
        """Discard any buffered outgoing (TX) data.

        On network/BLE backends this may be a no-op when the OS or stack
        does not support cancelling in-flight transmit data.
        """

    @property
    @abstractmethod
    def in_waiting(self) -> int:
        """Number of bytes currently available to read without blocking.

        Returns:
            Byte count waiting in the receive buffer.
        """

    @property
    @abstractmethod
    def timeout(self) -> Optional[float]:
        """Read timeout in seconds, or ``None`` to wait forever."""

    @timeout.setter
    @abstractmethod
    def timeout(self, value: Optional[float]):
        """Set read timeout in seconds, or ``None`` to wait forever."""
