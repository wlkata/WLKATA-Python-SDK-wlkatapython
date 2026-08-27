"""WiFi transport via TCP or UDP sockets.

Implements the same method names ``WLKATA_UART`` uses on ``pSerial``.
"""

import socket
import time
from typing import Optional

from .base import Transport


class WifiTransport(Transport):
    """TCP/UDP socket transport for WiFi-connected robots.

    Args:
        host: IP address or hostname of the robot.
        port: Port number.
        protocol: ``"tcp"`` (default) or ``"udp"``.
        timeout: Socket read timeout in seconds. Defaults to 1.
            ``None`` means wait forever (blocking).
    """

    def __init__(
        self,
        host: str,
        port: int,
        protocol: str = "tcp",
        timeout: Optional[float] = 1,
    ):
        self.host = host
        self.port = port
        self.protocol = protocol.lower()
        self._timeout = timeout
        self._socket: Optional[socket.socket] = None
        self._buffer = b""

    def connect(self):
        if self.is_connected:
            return
        if self.protocol == "tcp":
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self._timeout)
            self._socket.connect((self.host, self.port))
        else:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.settimeout(self._timeout)

    def disconnect(self):
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        self._buffer = b""

    @property
    def is_connected(self) -> bool:
        return self._socket is not None

    def _require_connected(self):
        if not self.is_connected:
            raise RuntimeError("WifiTransport is not connected; call connect() first")

    def write(self, data: bytes):
        self._require_connected()
        if self.protocol == "tcp":
            self._socket.sendall(data)
        else:
            self._socket.sendto(data, (self.host, self.port))

    def readline(self) -> bytes:
        """Read until ``\\n`` or until ``timeout`` elapses."""
        self._require_connected()
        if self._timeout is None:
            deadline = None
        else:
            deadline = time.monotonic() + self._timeout

        while b"\n" not in self._buffer:
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._socket.settimeout(remaining)
            else:
                self._socket.settimeout(None)

            try:
                chunk = self._socket.recv(1024)
                if not chunk:
                    break
                self._buffer += chunk
            except socket.timeout:
                break
            except BlockingIOError:
                break

        # Restore configured timeout after a bounded wait
        self._socket.settimeout(self._timeout)

        if b"\n" in self._buffer:
            line, _, self._buffer = self._buffer.partition(b"\n")
            return line + b"\n"
        line = self._buffer
        self._buffer = b""
        return line

    def flushInput(self):
        """Discard the local RX buffer and drain any pending socket data."""
        self._buffer = b""
        if self._socket is None:
            return
        self._socket.setblocking(False)
        try:
            while True:
                chunk = self._socket.recv(1024)
                if not chunk:
                    break
        except (BlockingIOError, socket.timeout, OSError):
            pass
        finally:
            self._socket.setblocking(True)
            self._socket.settimeout(self._timeout)

    def flushOutput(self):
        """No-op: TCP/UDP cannot cancel data already handed to the OS."""
        return

    @property
    def in_waiting(self) -> int:
        """Bytes already assembled in the local RX buffer."""
        return len(self._buffer)

    @property
    def timeout(self) -> Optional[float]:
        return self._timeout

    @timeout.setter
    def timeout(self, value: Optional[float]):
        self._timeout = value
        if self._socket is not None:
            self._socket.settimeout(value)
