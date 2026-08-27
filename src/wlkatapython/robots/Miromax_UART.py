"""WLKATA Miromax UART/RS485 control class.

Uses the same G-code protocol as ``Harobot_UART`` (G07/G01 Cartesian, G09
angles, M67 end effector, Cartesian-first status). Override class constants
below when Miromax firmware differs in feed rate, EE presets, version string,
or zero command — without changing command shape.
"""

from typing import Optional

from ..transports import Connection
from .Harobot_UART import Harobot_UART


class Miromax_UART(Harobot_UART):
    """Control class for the WLKATA Miromax robotic arm.

    Command format matches ``Harobot_UART``. Model-specific values live on
    class attributes so they can diverge without forking protocol methods.
    """

    _VERSION_PREFIX = "Miromax"
    _ZERO_CMD = "G9 G90 X0 Y0 Z0 A0 B0 C0 F4000"
    _HOMING_FALLBACK = "o105=8"
    _VALID_HOMING_MODES = set(range(11))

    # End-effector Q presets (override if Miromax uses different values)
    _GRIPPER_Q = {0: 0, 1: 4, 2: 7.5}
    _PUMP_Q = {0: 0, 1: 100, 2: 50}

    _FEED_RATE = 4000
    _MOTION_FAST = "G07"
    _MOTION_LINEAR = "G01"
    _MOTION_ANGLE = "G09"

    # Same Cartesian-first status layout as Harobot; override if firmware differs
    _STATUS_KEYS = (
        "state",
        "coordinate_X", "coordinate_Y", "coordinate_Z",
        "coordinate_RX", "coordinate_RY", "coordinate_RZ",
        None,
        "angle_X", "angle_Y", "angle_Z",
        "angle_A", "angle_B", "angle_C", "angle_D",
        None,
    )

    def __init__(
        self,
        p: Optional[Connection] = None,
        adr: Optional[int] = None,
        message_flag: bool = False,
    ):
        super().__init__(p, adr, message_flag=message_flag)


if __name__ == "__main__":
    import serial
    import time

    robot = Miromax_UART(message_flag=True)
    robot.init(serial.Serial("COM4", 115200, timeout=1), -1)
    robot.restart()
    robot.homing()
    robot.writeAngle(0, axle1=70)
    robot.writeCoordinate(0, 0, 220)
    robot.zero()
