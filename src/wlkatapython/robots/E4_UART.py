import serial

from .base import WLKATA_UART
from .utils import (
    _MOTION_CODES, _POSITION_CODES,
    _4AXIS_ANGLE_MAP, _4AXIS_COORDINATE_MAP,
    deprecated_alias,
)


class E4_UART(WLKATA_UART):
    """Control class for the WLKATA E4 4-axis robotic arm.

    Inherits from WLKATA_UART and overrides config for the E4's
    4-axis configuration (X, Y, Z, A).
    """

    _VALID_HOMING_MODES = {0, 1, 2, 3, 4, 7, 8, 9, 10}
    _HOMING_FALLBACK = "$h"
    _ZERO_CMD = "M21 G90 G00 X0 Y0 Z0 A0 "
    _VERSION_PREFIX = "E4"
    _ANGLE_MAP = _4AXIS_ANGLE_MAP
    _COORDINATE_MAP = _4AXIS_COORDINATE_MAP

    def writeCoordinate(self, motion, position, x, y, z, a):
        """Move the E4 to specified Cartesian coordinates.

        Args:
            motion (int): Movement type (0=Fast G00, 1=Linear G01, 2=Joint G05).
            position (int): Coordinate mode (0=Absolute G90, 1=Incremental G91).
            x (float): X coordinate.
            y (float): Y coordinate.
            z (float): Z coordinate.
            a (float): A rotation.
        """
        motion_code = _MOTION_CODES.get(motion, "G00")
        position_code = _POSITION_CODES.get(position, "G90")
        self.sendMsg(f"M20{position_code}{motion_code}X{x}Y{y}Z{z}A{a}")

    def writeAngle(self, position, x, y, z, a):
        """Move the E4 to specified joint angles.

        Args:
            position (int): Coordinate mode (0=Absolute G90, 1=Incremental G91).
            x (float): Axis 1 angle.
            y (float): Axis 2 angle.
            z (float): Axis 3 angle.
            a (float): Axis 4 angle.
        """
        position_code = _POSITION_CODES.get(position, "G90")
        self.sendMsg(f"M21{position_code}G00X{x}Y{y}Z{z}A{a}")

    def getAngle(self, num):
        """Get the angle of a specific E4 axis.

        Args:
            num (int): Axis number (1=X, 2=Y, 3=Z, 4=A, 7=D).

        Returns:
            str: Current angle value, or "parameter error/参数错误" if invalid.
        """
        self.getStatus()
        key = self._ANGLE_MAP.get(num)
        if key is None:
            return "parameter error/参数错误"
        return self.mirobot_state_all[key]

    def getCoordinate(self, num):
        """Get a Cartesian coordinate of the E4 end effector.

        Args:
            num (int): Coordinate axis (1=X, 2=Y, 3=Z, 4=RX).

        Returns:
            str: Current coordinate value, or "parameter error/参数错误" if invalid.
        """
        self.getStatus()
        key = self._COORDINATE_MAP.get(num)
        if key is None:
            return "parameter error/参数错误"
        return self.mirobot_state_all[key]

    # Deprecated aliases -- will be removed in v1.2
    @deprecated_alias("writeCoordinate", version=1.2)
    def writecoordinate(self, *args, **kwargs): ...

    @deprecated_alias("writeAngle", version=1.2)
    def writeangle(self, *args, **kwargs): ...

    @deprecated_alias("getCoordinate", version=1.2)
    def getcoordinate(self, *args, **kwargs): ...
