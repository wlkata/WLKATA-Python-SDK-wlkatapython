"""WLKATA Python SDK - Serial control library for WLKATA robotic devices.

This package provides Python classes for communicating with WLKATA robotic
arms and controllers over UART and RS485 serial interfaces.

Supported devices:

- ``Mirobot_UART`` -- WLKATA Mirobot 6-axis desktop robotic arm
- ``E4_UART`` -- WLKATA E4 4-axis SCARA robotic arm
- ``MT4_UART`` -- WLKATA MT4 4-axis robotic arm
- ``MS4220_UART`` -- WLKATA MS4220 stepper motor controller
- ``Mirobot_Serial_GUI`` -- Tkinter-based GUI for Mirobot control (optional)

All device classes inherit from ``WLKATA_UART``, which provides the core
serial communication protocol, status parsing, homing, movement commands,
GPIO control, and firmware version queries.

Example usage::

    from wlkatapython import Mirobot_UART
    import serial

    robot = Mirobot_UART()
    robot.init(serial.Serial('/dev/ttyUSB0', 115200), -1)
    robot.homing()
    robot.writeAngle(0, 45.0, 30.0, 15.0, 10.0, 5.0, 0.0)
"""
import warnings

from .robots import WLKATA_UART, Mirobot_UART, E4_UART, MT4_UART, MS4220_UART

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
    "Mirobot_Serial_GUI",
]

_DEPRECATED_CLASSES = {
    "Wlkata_UART": ("WLKATA_UART", 1.2),
}


def __getattr__(name):
    new_name, since_version = _DEPRECATED_CLASSES.get(name)
    if new_name is not None:
        warnings.warn(
            f"{name} is deprecated and will be removed in v{since_version}, "
            f"use {new_name} instead",
            DeprecationWarning, stacklevel=2,
        )
        return globals()[new_name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
