"""WLKATA robot control classes.

Provides UART/RS485 control classes for WLKATA robotic devices:
Mirobot (6-axis), E4 (4-axis), MT4 (4-axis), and MS4220 (stepper motor).
The optional Mirobot_Serial_GUI is available when tkinter is installed.
"""

from .E4_UART import E4_UART
from .MS4220_UART import MS4220_UART
from .MT4_UART import MT4_UART
from .Mirobot_UART import Mirobot_UART
from .base import WLKATA_UART

try:
    from .Mirobot_GUI import Mirobot_Serial_GUI

    __all__ = [
        "WLKATA_UART",
        "Mirobot_UART",
        "E4_UART",
        "MT4_UART",
        "MS4220_UART",
        "Mirobot_Serial_GUI",
    ]
except ImportError:
    __all__ = [
        "WLKATA_UART",
        "Mirobot_UART",
        "E4_UART",
        "MT4_UART",
        "MS4220_UART",
    ]
