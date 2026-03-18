from .base import WLKATA_UART


class Mirobot_UART(WLKATA_UART):
    """Control class for WLKATA Mirobot 6-axis robotic arm.

    The Mirobot is a 6-axis robotic arm with X, Y, Z, A, B, and C axes.
    All motion, homing, status, and version methods are inherited from WLKATA_UART
    and configured via the class attributes below.
    """
    axis_count = 6
    _version_prefix = "Mirobot"
    _homing_fallback = "o105=8"
