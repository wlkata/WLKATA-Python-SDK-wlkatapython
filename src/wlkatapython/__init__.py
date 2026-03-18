"""WLKATA Python SDK — serial communication for WLKATA robotic arms.

WLKATA_UART is the abstract base class for all robots (UART / RS485).
Mirobot_UART  — 6-axis Mirobot arm (inherits WLKATA_UART).
E4_UART       — 4-axis E4 arm (inherits WLKATA_UART).
MT4_UART      — 4-axis MT4 arm (inherits WLKATA_UART).
MS4220_UART   — MS4220 stepper motor controller (inherits WLKATA_UART).
Mirobot_Serial_GUI — optional GUI for the Mirobot arm.
"""
from .robots import Mirobot_UART, E4_UART, MT4_UART, MS4220_UART
try:
    from .robots.Mirobot_GUI import Mirobot_Serial_GUI
except ImportError:
    # Mirobot_Serial_GUI not available
    Mirobot_Serial_GUI = object



# Backward-compatible alias
Wlkata_UART = Mirobot_UART

