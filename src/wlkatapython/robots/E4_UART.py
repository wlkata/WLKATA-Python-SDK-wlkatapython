from .base import WLKATA_UART
import serial

#E4串口控制类
#E4 serial port control class


class E4_UART(WLKATA_UART):
    """Control class for WLKATA E4 4-axis robotic arm.

    The E4 is a 4-axis SCARA-style robotic arm with X, Y, Z, and A (rotation) axes.
    All motion, homing, status, and version methods are inherited from WLKATA_UART
    and configured via the class attributes below.
    """
    axis_count = 4
    _version_prefix = "E4"
    _homing_fallback = "$h"


if __name__ == "__main__":
    e4 = E4_UART()
    e4.init(serial.Serial('COM13', 115200), 1)
    e4.homing()
