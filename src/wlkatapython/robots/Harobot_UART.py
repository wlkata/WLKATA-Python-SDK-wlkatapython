import re
import time

from .base import WLKATA_UART
from .utils import _POSITION_CODES, _DeprecatedKeyDict, build_axes_string


_HAROBOT_GRIPPER_Q = {0: 0, 1: 4, 2: 7.5}
_HAROBOT_PUMP_Q = {0: 0, 1: 100, 2: 50}

# Maps each regex group in the Harobot status response to a state-dict key.
# None entries are skipped (spare 7th Cartesian value and optional Ov tag).
_HAROBOT_STATUS_KEYS = (
    "state",
    "coordinate_X", "coordinate_Y", "coordinate_Z",
    "coordinate_RX", "coordinate_RY", "coordinate_RZ",
    None,                                          # spare 7th Cartesian
    "angle_X", "angle_Y", "angle_Z",
    "angle_A", "angle_B", "angle_C", "angle_D",
    None,                                          # optional |Ov:... tag
)


class Harobot_UART(WLKATA_UART):
    """Control class for the WLKATA Harobot 7-axis robotic arm.

    Inherits from WLKATA_UART. Key protocol differences from the base:
    - Motion commands: G07 (fast) / G01 (linear) with format {motion}{position}{axes}F4000
    - Angle commands: G09{position}{axes}F4000
    - End effector: M67 E0 Q{value} instead of M3 S{value}
    - Status response: Cartesian-first format with 7 Cartesian + 7 Angle values
    - homing() triggers a restart first
    """

    _VALID_HOMING_MODES = set(range(11))
    _HOMING_FALLBACK = "o105=8"
    _ZERO_CMD = "G9 G90 X0 Y0 Z0 A0 B0 C0 F4000"
    _VERSION_PREFIX = "Harobot"

    def __init__(self, p=None, adr=None, message_flag=False):
        super().__init__(p, adr)
        if message_flag:
            self.message_print(message_flag)

    def gripper(self, num):
        q = _HAROBOT_GRIPPER_Q.get(num, 0)
        self.sendMsg(f"M67 E0 Q{q}")

    def pump(self, num):
        q = _HAROBOT_PUMP_Q.get(num, 0)
        self.sendMsg(f"M67 E0 Q{q}")

    def pwmWrite(self, num):
        self.sendMsg(f"M67 E0 Q{num}")

    def writeCoordinate(self, motion, position, x=None, y=None, z=None,
                        a=None, b=None, c=None):
        """Move the Harobot to specified Cartesian coordinates.

        Args:
            motion (int): Movement type (0=Fast G07, 1=Linear G01).
            position (int): Coordinate mode (0=Absolute G90, 1=Incremental G91).
            x/y/z/a/b/c (float, optional): Coordinate values.
        """
        motion_code = "G07" if motion == 0 else "G01"
        position_code = _POSITION_CODES.get(position, "G90")
        axes = build_axes_string(x=x, y=y, z=z, a=a, b=b, c=c)
        self.sendMsg(f"{motion_code}{position_code}{axes}F4000")

    def writeAngle(self, position, axle1=None, axle2=None, axle3=None,
                   axle4=None, axle5=None, axle6=None, axle7=None):
        """Move the Harobot to specified joint angles for up to 7 axes.

        Args:
            position (int): Coordinate mode (0=Absolute G90, 1=Incremental G91).
            axle1-7 (float, optional): Joint angles for axes 1-7 (X,Y,Z,A,B,C,D).
        """
        position_code = _POSITION_CODES.get(position, "G90")
        axes = build_axes_string(x=axle1, y=axle2, z=axle3, a=axle4, b=axle5, c=axle6)
        if axle7 is not None:
            axes += f"D{axle7}"
        self.sendMsg(f"G09{position_code}{axes}F4000")

    def getStatus(self):
        """Query and update the full status of the Harobot.

        The Harobot response format differs from the base:
        <state,Cartesian:X,Y,Z,RX,RY,RZ,W,Angle:A1,A2,A3,A4,A5,A6,A7[|Ov:...]>
        """
        self.pSerial.flushInput()
        self.pSerial.flushOutput()
        self.sendMsg("?")
        if self.pSerial.in_waiting > 0:
            line = self.pSerial.readline().decode('utf-8').strip()
            if line and line[0] == "<" and line[-1] == ">":
                data = self._parse_harobot_response(line)
            else:
                data = -1
        else:
            return "error"
        time.sleep(0.1)
        return data

    def _parse_harobot_response(self, line):
        pattern = (
            r'<(\w+),Cartesian:'
            r'([\d.-]+),([\d.-]+),([\d.-]+),'
            r'([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),'
            r'Angle:'
            r'([\d.-]+),([\d.-]+),([\d.-]+),'
            r'([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+)'
            r'([|Ov:100,100,100])*>'
        )
        match = re.match(pattern, line)
        if match:
            data = {k: v for k, v in zip(_HAROBOT_STATUS_KEYS, match.groups()) if k is not None}
            data.update(pump=-1, valve=-1, mode=-1)
            self.mirobot_state_all = _DeprecatedKeyDict(data)
            return self.mirobot_state_all
        else:
            return "parse error"


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
