import re
import time
from typing import Optional

from ..transports import Connection
from .base import WLKATA_UART
from .utils import (
    _POSITION_CODES,
    _STATUS_NUMBER,
    _DeprecatedKeyDict,
    build_axes_string,
    status_number_groups,
)

# Comma-separated status (Harobot):
#   <state,Cartesian:X,Y,Z,RX,RY,RZ,W,Angle:A1,...,A7[|anything]>
_COMMA_STATUS_RE = re.compile(
    r"^<(\w+),Cartesian:"
    + status_number_groups(7)
    + r",Angle:"
    + status_number_groups(7)
    + r"(?:\|.*)?>$"
)

# Pipe-separated status (Miromax):
#   <state|Cartesian:X,Y,Z,RX,RY,RZ[,W]|Angle:A1,...,A6[,A7][|anything]>
# where state may carry a sub-state, as in Hold:0 or Hold:1
_PIPE_STATUS_RE = re.compile(
    r"^<([A-Za-z]+(?::\d+)?)\|Cartesian:([^|]+)\|Angle:([^|>]+)(?:\|.*)?>$"
)

_STATUS_NUMBER_RE = re.compile(_STATUS_NUMBER)


class Harobot_UART(WLKATA_UART):
    """Control class for the WLKATA Harobot 7-axis robotic arm.

    Inherits from WLKATA_UART. Key protocol differences from the base:
    - Homing: restarts the controller, then sends $h{mode}
    - Motion commands: G07 (fast) / G01 (linear) with format {motion}{position}{axes}
    - Angle commands: G09{position}{axes}
    - End effector: M67 E0 Q{value} instead of M3 S{value}
    - Status response: Cartesian-first format with 7 Cartesian + 7 Angle values

    Subclasses (e.g. ``Miromax_UART``) can override the class constants below
    without changing the command protocol.
    """

    _VALID_HOMING_MODES = set(range(11))
    _HOMING_PREFIX = "$h"
    _HOMING_FALLBACK = "$h8"
    # The Harobot restarts its controller before it homes
    _HOMING_RESTARTS = True
    # Seconds the controller is given to come back up after a restart
    _RESTART_SETTLE_S = 3.0
    _ZERO_CMD = "G9 G90 X0 Y0 Z0 A0 B0 C0"
    _VERSION_PREFIX = "Harobot"

    # End-effector Q values for gripper()/pump() presets
    _GRIPPER_Q = {0: 0, 1: 4, 2: 7.5}
    _PUMP_Q = {0: 0, 1: 100, 2: 50}

    # Feed rate appended to motion / angle commands as F{rate}; None sends
    # none, and the arm keeps the speed last set with speed()
    _FEED_RATE = None

    # Motion G-codes (fast vs linear Cartesian)
    _MOTION_FAST = "G07"
    _MOTION_LINEAR = "G01"
    _MOTION_ANGLE = "G09"

    # State-dict keys for the status values, in the order the arm sends them.
    # A value past the end of a tuple (the spare 7th Cartesian) is dropped.
    _CARTESIAN_KEYS = (
        "coordinate_X", "coordinate_Y", "coordinate_Z",
        "coordinate_RX", "coordinate_RY", "coordinate_RZ",
    )
    _ANGLE_KEYS = (
        "angle_X", "angle_Y", "angle_Z",
        "angle_A", "angle_B", "angle_C", "angle_D",
    )

    def __init__(
        self,
        p: Optional[Connection] = None,
        adr: Optional[int] = None,
        message_flag: bool = False,
    ):
        super().__init__(p, adr)
        if message_flag:
            self.message_print(message_flag)

    def homing(self, mode=8):
        """Perform robot homing (return to home position).

        When ``_HOMING_RESTARTS`` is set (the Harobot), the controller is
        restarted first and given ``_RESTART_SETTLE_S`` seconds to come back.

        Args:
            mode (int): Homing mode (0-10). Defaults to 8.
        """
        if self._HOMING_RESTARTS:
            self.restart()
            time.sleep(self._RESTART_SETTLE_S)
            # Drop what the controller printed while it restarted
            self.pSerial.flushInput()
        super().homing(mode)

    def gripper(self, num):
        q = self._GRIPPER_Q.get(num, 0)
        self.sendMsg(f"M67 E0 Q{q}")

    def pump(self, num):
        q = self._PUMP_Q.get(num, 0)
        self.sendMsg(f"M67 E0 Q{q}")

    def pwmWrite(self, num):
        self.sendMsg(f"M67 E0 Q{num}")

    def _feed_suffix(self):
        """Return the F word for motion commands, or "" when none is set."""
        if self._FEED_RATE is None:
            return ""
        return f"F{self._FEED_RATE}"

    def writeCoordinate(self, motion, position, x=None, y=None, z=None,
                        a=None, b=None, c=None):
        """Move to specified Cartesian coordinates.

        Args:
            motion (int): Movement type (0=Fast, 1=Linear).
            position (int): Coordinate mode (0=Absolute G90, 1=Incremental G91).
            x/y/z/a/b/c (float, optional): Coordinate values.
        """
        motion_code = self._MOTION_LINEAR if motion == 1 else self._MOTION_FAST
        position_code = _POSITION_CODES.get(position, "G90")
        axes = build_axes_string(x=x, y=y, z=z, a=a, b=b, c=c)
        self.sendMsg(f"{motion_code}{position_code}{axes}{self._feed_suffix()}")

    def writeAngle(self, position, axle1=None, axle2=None, axle3=None,
                   axle4=None, axle5=None, axle6=None, axle7=None):
        """Move to specified joint angles for up to 7 axes.

        Args:
            position (int): Coordinate mode (0=Absolute G90, 1=Incremental G91).
            axle1-7 (float, optional): Joint angles for axes 1-7 (X,Y,Z,A,B,C,D).
        """
        position_code = _POSITION_CODES.get(position, "G90")
        axes = build_axes_string(x=axle1, y=axle2, z=axle3, a=axle4, b=axle5, c=axle6)
        if axle7 is not None:
            axes += f"D{axle7}"
        self.sendMsg(
            f"{self._MOTION_ANGLE}{position_code}{axes}{self._feed_suffix()}"
        )

    def _parse_status_line(self, line):
        return self._parse_status_response(line)

    def _parse_status_response(self, line):
        """Parse a status line in either format into the state dictionary.

        Two formats are understood, whichever the arm sends:

        - comma-separated (Harobot):
          ``<state,Cartesian:X,Y,Z,RX,RY,RZ,W,Angle:A1,...,A7[|...]>``
        - pipe-separated (Miromax):
          ``<state|Cartesian:X,Y,Z,RX,RY,RZ|Angle:A1,...,A7[|...]>``

        Anything after a further ``|`` (an ``Ov:`` or ``WCO:`` tail) is
        ignored. Values the arm did not send stay at -1.

        Returns:
            dict or str: Parsed state dictionary, or "parse error".
        """
        match = _PIPE_STATUS_RE.match(line)
        if match:
            cartesian = _STATUS_NUMBER_RE.findall(match.group(2))
            angles = _STATUS_NUMBER_RE.findall(match.group(3))
            if len(cartesian) < 6 or len(angles) < 6:
                return "parse error"
        else:
            match = _COMMA_STATUS_RE.match(line)
            if not match:
                return "parse error"
            values = match.groups()[1:]
            cartesian, angles = values[:7], values[7:]

        data = {"state": match.group(1)}
        data.update(dict.fromkeys(self._CARTESIAN_KEYS + self._ANGLE_KEYS, -1))
        data.update(zip(self._CARTESIAN_KEYS, cartesian))
        data.update(zip(self._ANGLE_KEYS, angles))
        data.update(pump=-1, valve=-1, mode=-1)
        self.mirobot_state_all = _DeprecatedKeyDict(data)
        return self.mirobot_state_all

    # Back-compat alias used by older call sites / tests
    _parse_harobot_response = _parse_status_response


if __name__ == "__main__":
    import serial
    robot = Harobot_UART(message_flag=True)
    robot.init(serial.Serial('COM4', 115200, timeout=1), -1)
    robot.restart()
    robot.homing()
    robot.pump(1)
    time.sleep(1)
    robot.pump(2)
    time.sleep(1)
    robot.pump(0)
    time.sleep(1)
    robot.writeAngle(0, axle1=70)
    robot.writeCoordinate(0, 0, 220)
    robot.zero()
