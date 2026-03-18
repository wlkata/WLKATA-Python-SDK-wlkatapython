from .base import WLKATA_UART
import serial

#MT4串口控制类
#MT4 serial port control class


class MT4_UART(WLKATA_UART):
    """Control class for WLKATA MT4 4-axis robotic arm.

    The MT4 is a 4-axis robotic arm with X, Y, Z, and A (rotation) axes.
    All motion, homing, status, and version methods are inherited from WLKATA_UART
    and configured via the class attributes below.
    """
    axis_count = 4
    _version_prefix = "E4"
    _homing_fallback = "$h"


if __name__ == "__main__":
    mt4 = MT4_UART()
    mt4.init(serial.Serial('COM13', 115200), -1)
    mt4.homing()

