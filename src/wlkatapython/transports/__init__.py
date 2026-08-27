"""Transport backends with a pyserial-compatible I/O surface.

All transports implement the same names the robot library uses on
``pSerial``: ``write``, ``readline``, ``in_waiting``, ``flushInput``,
``flushOutput``, and ``timeout``.

``Connection`` is the accepted input type for ``robot.init`` /
``WLKATA_UART``: a pyserial ``Serial`` or any ``Transport``.
"""

from typing import Union

from serial import Serial

from .base import Transport
from .ble import BleTransport
from .serial_adapter import SerialAdapter
from .uart import UartTransport
from .wifi import WifiTransport

# What callers may pass into robot.init() / __init__(p, ...)
Connection = Union[Serial, Transport]

__all__ = [
    "Connection",
    "Transport",
    "SerialAdapter",
    "UartTransport",
    "WifiTransport",
    "BleTransport",
]
