"""WLKATA Python SDK - Control library for WLKATA robotic devices.

This package provides Python classes for communicating with WLKATA robotic
arms and controllers over UART/RS485, WiFi, or BLE using the G-code protocol.

Supported devices:

- ``Mirobot_UART`` -- WLKATA Mirobot 6-axis desktop robotic arm
- ``E4_UART`` -- WLKATA E4 4-axis SCARA robotic arm
- ``MT4_UART`` -- WLKATA MT4 4-axis robotic arm
- ``MS4220_UART`` -- WLKATA MS4220 stepper motor controller
- ``Harobot_UART`` -- WLKATA Harobot 7-axis (G07/G09/M67 protocol)
- ``Miromax_UART`` -- WLKATA Miromax (same protocol as Harobot; model constants)
- ``Mirobot_Serial_GUI`` -- Tkinter-based GUI for Mirobot control (optional)

All device classes inherit from ``WLKATA_UART``, which provides the core
protocol, status parsing, homing, movement commands, GPIO control, and
firmware version queries.

Connections may be:

- legacy ``serial.Serial`` via ``robot.init(ser, address)``
- ``UartTransport`` / ``WifiTransport`` / ``BleTransport`` via ``init(...)``
- convenience helpers ``init_uart`` / ``init_wifi`` / ``init_ble``

A hardware-free simulator is available as ``wlkatapython.simulator``.

Example (legacy serial)::

    from wlkatapython import Mirobot_UART
    import serial

    robot = Mirobot_UART()
    robot.init(serial.Serial('/dev/ttyUSB0', 115200), -1)
    robot.homing()
    robot.writeAngle(0, 45.0, 30.0, 15.0, 10.0, 5.0, 0.0)

Example (UART transport helper)::

    from wlkatapython import Mirobot_UART

    robot = Mirobot_UART()
    robot.init_uart('/dev/ttyUSB0', -1)
    robot.homing()
    robot.close()
"""
import warnings

from .robots import (
    WLKATA_UART,
    Mirobot_UART,
    E4_UART,
    MT4_UART,
    MS4220_UART,
    Harobot_UART,
    Miromax_UART,
)
from .transports import (
    BleTransport,
    Connection,
    SerialAdapter,
    Transport,
    UartTransport,
    WifiTransport,
)

try:
    from .robots.Mirobot_GUI import Mirobot_Serial_GUI
except ImportError:
    Mirobot_Serial_GUI = None

__all__ = [
    "WLKATA_UART",
    "Mirobot_UART",
    "E4_UART",
    "MT4_UART",
    "MS4220_UART",
    "Harobot_UART",
    "Miromax_UART",
    "Mirobot_Serial_GUI",
    "Connection",
    "Transport",
    "SerialAdapter",
    "UartTransport",
    "WifiTransport",
    "BleTransport",
]

_DEPRECATED_CLASSES = {
    "Wlkata_UART": ("WLKATA_UART", 1.2),
}


def __getattr__(name):
    entry = _DEPRECATED_CLASSES.get(name)
    if entry is not None:
        new_name, since_version = entry
        warnings.warn(
            f"{name} is deprecated and will be removed in v{since_version}, "
            f"use {new_name} instead",
            DeprecationWarning, stacklevel=2,
        )
        return globals()[new_name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
