"""Base class for WLKATA robotic arm and controller communication.

This class provides the core functionality for communicating with WLKATA robotic
devices via UART or RS485 interfaces. It includes methods for sending commands,
receiving responses, and basic robot control operations.

All WLKATA robot classes inherit from this base class.
"""

import logging
import re
import time
import warnings

from serial import Serial

logger = logging.getLogger(__name__)

from .utils import (
    _DeprecatedKeyDict,
    _ERROR_MESSAGES,
    _MOTION_CODES,
    _POSITION_CODES,
    _GRIPPER_PWM,
    _PUMP_PWM,
    _STATUS_KEYS,
    _ANGLE_MAP,
    _COORDINATE_MAP,
    build_gpio_cmd,
    parse_gpio_response,
    deprecated_alias,
)


class WLKATA_UART:
    _VALID_HOMING_MODES = set(range(11))
    _HOMING_FALLBACK = "o105=8"
    _ZERO_CMD = "M21 G90 G00 X0 Y0 Z0 A0 B0 C00"
    _AXES = "X{x}Y{y}Z{z}A{a}B{b}C{c}"
    _VERSION_PREFIX = "Mirobot"
    _ANGLE_MAP = _ANGLE_MAP
    _COORDINATE_MAP = _COORDINATE_MAP

    def __init__(self, p: Serial = None, adr: int = None):
        """Initialize the WLKATA UART communication interface.

        Args:
            p: Serial port object (e.g., serial.Serial instance).
                Defaults to None (call init() later to set).
            adr (int): Robot address for RS485 (-1 for UART mode, 0-255 for RS485).
                Defaults to None (call init() later to set).
        """
        self.mirobot_state_all = _DeprecatedKeyDict({
            "state": "-1",
            "angle_A": -1, "angle_B": -1, "angle_C": -1, "angle_D": -1,
            "angle_X": -1, "angle_Y": -1, "angle_Z": -1,
            "coordinate_X": -1, "coordinate_Y": -1, "coordinate_Z": -1,
            "coordinate_RX": -1, "coordinate_RY": -1, "coordinate_RZ": -1,
            "pump": -1, "valve": -1, "mode": -1
        })
        self.gpio_state = [0, 0, 0, 0]

        self.pSerial = p
        self.address = adr

    def init(self, p, adr):
        """Initialize the serial communication.

        Args:
            p: Serial port object (e.g., serial.Serial instance).
            adr (int): Robot address for RS485 (-1 for UART mode, 0-255 for RS485).
        """
        self.pSerial = p
        self.address = adr

    def message_print(self, flag):
        """Enable or disable message printing for debugging.

        Sets the logger level. True sets DEBUG, False sets WARNING.
        An int is interpreted as a logging level directly
        (e.g. logging.DEBUG, logging.INFO).

        Args:
            flag (bool or int): True to enable debug output, False to disable,
                               or a logging level constant.
        """
        if isinstance(flag, bool):
            logger.setLevel(logging.DEBUG if flag else logging.WARNING)
        else:
            logger.setLevel(flag)

    def readMessage(self):
        """Read a message from the serial port.

        Returns:
            str: The received message, or "read error" if no data available.
        """
        if self.pSerial.in_waiting > 0:
            message = self.pSerial.readline().decode('utf-8').strip()
            logger.debug(f"read:\t{message}")
            return message
        else:
            return "read error"

    def sendMsg(self, message):
        """Send a message to the robot.

        Args:
            message (str): The message to send (without \\r\\n).
        """
        if self.address != -1:
            message = f"@{self.address}{message}\r\n"
        else:
            message = f"{message}\r\n"
        self.pSerial.write(message.encode("utf-8"))
        logger.debug(f"write:\t{message}")
        time.sleep(0.1)

    def homing(self, mode=8):
        """Perform robot homing (return to home position).

        Args:
            mode (int): Homing mode. Defaults to 8.
                       Valid modes depend on the robot model.
        """
        if isinstance(mode, int) and mode in self._VALID_HOMING_MODES:
            self.sendMsg(f"o105={mode}")
        else:
            self.sendMsg(self._HOMING_FALLBACK)

    def runFile(self, fileName, num=False):
        """Execute an offline program file stored on the robot controller.

        Args:
            fileName (str or int): Name or number of the file to execute.
            num (bool): If True, use o112 command (with number), else o111.

        Returns:
            int: 1 on success.

        Raises:
            Exception: If file execution fails or returns error.
        """
        prefix = "o112" if num is True else "o111"
        self.sendMsg(f"{prefix}{fileName}")

        response = self.readMessage()
        if response == "ok":
            return 1
        elif response == "error":
            self.__error_except(self.runFile, 4)
        else:
            self.__error_except(self.runFile, 1)

    def cancellation(self):
        """Stop the current robot movement or action immediately.

        Returns:
            int: 1 on success.

        Raises:
            Exception: If the stop command fails.
        """
        self.sendMsg("o117")
        if self.readMessage() == "ok":
            return 1
        else:
            self.__error_except(self.cancellation, 1)

    def gripper(self, num):
        """Control the gripper (if equipped).

        Args:
            num (int): Gripper command:
                      0 - Open/Release
                      1 - Close/Grip (medium force)
                      2 - Close/Grip (high force)

        Returns:
            int: 1 on success.

        Raises:
            Exception: If gripper control fails.
        """
        pwm = _GRIPPER_PWM.get(num, 0)
        self.sendMsg(f"M3 S{pwm}")
        if self.readMessage() == "ok":
            return 1
        else:
            self.__error_except(self.gripper, 1)

    def pump(self, num):
        """Control the air pump (if equipped).

        Args:
            num (int): Pump command:
                      0 - Off
                      1 - Full power (S1000)
                      2 - Half power (S500)

        Returns:
            int: 1 on success.

        Raises:
            Exception: If pump control fails.
        """
        pwm = _PUMP_PWM.get(num, 0)
        self.sendMsg(f"M3 S{pwm}")
        if self.readMessage() == "ok":
            return 1
        else:
            self.__error_except(self.pump, 1)

    def pwmWrite(self, num):
        """Write a raw PWM value to the end effector.

        Args:
            num (int): PWM duty cycle value (0-1000).

        Returns:
            int: 1 on success.

        Raises:
            Exception: If PWM write fails.
        """
        self.sendMsg(f"M3 S{num}")
        if self.readMessage() == "ok":
            return 1
        else:
            self.__error_except(self.pwmWrite, 1)

    def zero(self):
        """Move the robot to the zero position in angle mode.

        This moves all axes to their zero/reference positions.
        """
        self.sendMsg(self._ZERO_CMD)

    def writeCoordinate(self, motion, position, x, y, z, a, b, c):
        """Move the robot to specified Cartesian coordinates.

        Args:
            motion (int): Movement type:
                         0 - Fast (G00)
                         1 - Linear (G01)
                         2 - Joint (G05)
            position (int): Coordinate mode:
                           0 - Absolute (G90)
                           1 - Incremental (G91)
            x (float): X coordinate
            y (float): Y coordinate
            z (float): Z coordinate
            a (float): A rotation (RX)
            b (float): B rotation (RY)
            c (float): C rotation (RZ)
        """
        motion_code = _MOTION_CODES.get(motion, "G00")
        position_code = _POSITION_CODES.get(position, "G90")
        axes = self._AXES.format(x=x, y=y, z=z, a=a, b=b, c=c)
        self.sendMsg(f"M20{position_code}{motion_code}{axes}")

    def speed(self, num):
        """Set the robot movement speed.

        Args:
            num (int): Speed value (0-100).

        Returns:
            int: 1 on success.

        Raises:
            Exception: If speed setting fails.
        """
        self.sendMsg(f"F{num}")
        if self.readMessage() == "ok":
            return 1
        else:
            self.__error_except(self.speed, 1)

    def writeAngle(self, position, x, y, z, a, b, c):
        """Move the robot to specified joint angles.

        Args:
            position (int): Coordinate mode:
                           0 - Absolute (G90)
                           1 - Incremental (G91)
            x (float): Axis 1 angle
            y (float): Axis 2 angle
            z (float): Axis 3 angle
            a (float): Axis 4 angle
            b (float): Axis 5 angle
            c (float): Axis 6 angle
        """
        position_code = _POSITION_CODES.get(position, "G90")
        axes = self._AXES.format(x=x, y=y, z=z, a=a, b=b, c=c)
        self.sendMsg(f"M21{position_code}G00{axes}")

    def writeExpand(self, motion, position, d):
        """Move the 7th axis (external rail/turntable).

        Args:
            motion (int): Movement type:
                         0 - Fast (G00)
                         1 - Linear (G01)
            position (int): Coordinate mode:
                           0 - Absolute (G90)
                           1 - Incremental (G91)
            d (float): 7th axis position value.
        """
        motion_code = _MOTION_CODES.get(motion, "G00")
        position_code = _POSITION_CODES.get(position, "G90")
        self.sendMsg(f"{position_code}{motion_code}D{d}")

    def restart(self):
        """Restart the robot controller.

        Returns:
            int: 1 on success.

        Raises:
            Exception: If restart command fails.
        """
        self.sendMsg("o100")
        if self.readMessage() == "ok":
            return 1
        else:
            self.__error_except(self.restart, 1)

    def version(self):
        """Get the firmware version of the robot controller.

        Note: Currently only available in UART mode, not RS485.

        The response may contain both an EXbox controller version and a robot
        firmware version, or only the robot firmware version. When both are
        present, the EXbox line always comes first.

        Returns:
            tuple: (exbox_version, robot_version) if both are present.
            str: robot_version if only the robot responds.
            str: "查询失败" on timeout.

        Raises:
            UnicodeDecodeError: If response cannot be decoded.
        """
        self.pSerial.flushInput()
        self.pSerial.flushOutput()
        self.sendMsg("$V")

        for _ in range(5):
            line1 = self.pSerial.readline().decode('utf-8').strip()
            if not line1:
                time.sleep(0.1)
                continue

            if line1.startswith('EXbox'):
                line2 = self.pSerial.readline().decode('utf-8').strip()
                if line2.startswith(self._VERSION_PREFIX):
                    return line1, line2
            elif line1.startswith(self._VERSION_PREFIX):
                return line1

            time.sleep(0.1)

        return "查询失败"

    def __error_except(self, f, num):
        """Raise an exception with a descriptive error message.

        Args:
            f (callable): The calling function (used for error message).
            num (int): Error code (1=no reply, 2=parameter, 3=regex, 4=file run).

        Raises:
            Exception: With a message corresponding to the error code.
        """
        msg = _ERROR_MESSAGES.get(num)
        if msg:
            raise Exception(f"{f.__name__}: {msg}")

    def getStatus(self):
        """Query and update the full status of the robot.

        Sends a '?' command to get current position, angles, and state.

        Returns:
            dict or str: Robot status dictionary or "error" if no response.
        """
        self.pSerial.flushInput()
        self.pSerial.flushOutput()
        self.sendMsg("?")
        if self.pSerial.in_waiting > 0:
            line = self.pSerial.readline().decode('utf-8').strip()
            if line[0] == "<" and line[-1] == ">":
                data = self.__parse_response(line)
            else:
                data = -1
        else:
            return "error"

        logger.info(f"status:\t{data}")
        time.sleep(0.1)
        return data

    def __parse_response(self, line):
        """Parse a status response string into the robot state dictionary.

        Args:
            line (str): Raw status response string from the robot.

        Returns:
            dict or str: Parsed state dictionary, or "parse error" if the
                        response does not match the expected format.
        """
        pattern = r'<(\w+),Angle\(ABCDXYZ\):([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),Cartesian coordinate\(XYZ RxRyRz\):([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),Pump PWM:([\d.-]+),Valve PWM:([\d.-]+),Motion_MODE:([\d.-]+)>'
        match = re.match(pattern, line)
        if match:
            self.mirobot_state_all = _DeprecatedKeyDict(
                zip(_STATUS_KEYS, match.groups())
            )
            return self.mirobot_state_all
        else:
            return "parse error"

    def getState(self):
        """Get the current motion state of the robot.

        Returns:
            str: Robot state (e.g., "Idle", "Run", "Alarm").
        """
        self.getStatus()
        return self.mirobot_state_all["state"]

    def getAngle(self, num):
        """Get the angle of a specific robot axis.

        Args:
            num (int): Axis number (1-7):
                      1=X, 2=Y, 3=Z, 4=A, 5=B, 6=C, 7=D

        Returns:
            float: Current angle of the specified axis.

        Raises:
            Exception: If axis number is invalid.
        """
        self.getStatus()
        key = self._ANGLE_MAP.get(num)
        if key is None:
            self.__error_except(self.getAngle, 2)
        return self.mirobot_state_all[key]

    def getCoordinate(self, num):
        """Get the Cartesian coordinate of the robot end effector.

        Args:
            num (int): Coordinate axis (1-6):
                      1=X, 2=Y, 3=Z, 4=RX, 5=RY, 6=RZ

        Returns:
            float: Current coordinate value.

        Raises:
            Exception: If coordinate number is invalid.
        """
        self.getStatus()
        key = self._COORDINATE_MAP.get(num)
        if key is None:
            self.__error_except(self.getCoordinate, 2)
        return self.mirobot_state_all[key]

    def getPump(self):
        """Get the current pump PWM value.

        Returns:
            str: Pump PWM value.
        """
        self.getStatus()
        return self.mirobot_state_all["pump"]

    def getMode(self):
        """Get the current motion mode of the robot.

        Returns:
            str: Motion mode value.
        """
        self.getStatus()
        return self.mirobot_state_all["mode"]

    def getmooe(self):
        """Deprecated: Use getMode() instead."""
        warnings.warn(
            "getmooe() is deprecated and will be removed in v1.2, use getMode() instead",
            DeprecationWarning, stacklevel=2,
        )
        return self.getMode()

    def gpio_init(self):
        """Initialize GPIO pins (disable all enables).

        Sets all GPIO enable states to 0 (disabled).

        Returns:
            int: 1 on success.

        Raises:
            Exception: If GPIO initialization fails.
        """
        for i in range(4):
            self.gpio_state[i] = 0
        self.sendMsg(f"o132={self.gpio_state[0]},{self.gpio_state[1]},{self.gpio_state[2]},{self.gpio_state[3]}")
        if self.readMessage() == "ok":
            return 1
        else:
            self.__error_except(self.gpio_init, 1)

    def gpio_mode_write(self, name, num):
        """Set the mode of a GPIO pin.

        Args:
            name (str): Pin name ("A0", "A1", "D0", or "D1").
            num (int): Mode value to set.

        Returns:
            int: 1 on success.

        Raises:
            Exception: If pin name is invalid or command fails.
        """
        pin = name.capitalize()
        cmd = build_gpio_cmd("o130", pin, num)
        if cmd is None:
            self.__error_except(self.gpio_mode_write, 2)
        self.sendMsg(cmd)
        if self.readMessage() == "ok":
            return 1
        else:
            self.__error_except(self.gpio_mode_write, 1)

    def gpio_mode_read(self, name):
        """Read the mode of a GPIO pin.

        Args:
            name (str): Pin name ("A0", "A1", "D0", or "D1").

        Returns:
            str: Mode value of the specified pin.

        Raises:
            Exception: If pin name is invalid or response parse fails.
        """
        pin = name.capitalize()
        self.sendMsg("o130?")
        response = self.readMessage()
        self.readMessage()
        match = re.match(r'^(\d+),(\d+),(\d+),(\d+)$', response)
        if match:
            result = parse_gpio_response(pin, match)
            if result is None:
                self.__error_except(self.gpio_mode_read, 2)
            return result
        else:
            self.__error_except(self.gpio_mode_read, 3)

    def gpio_output_write(self, name, num):
        """Write a digital or analog output value to a GPIO pin.

        Args:
            name (str): Pin name ("A0", "A1", "D0", or "D1").
            num (int): Output value to write.

        Returns:
            int: 1 on success.

        Raises:
            Exception: If pin name is invalid or command fails.
        """
        pin = name.capitalize()
        cmd = build_gpio_cmd("o131", pin, num)
        if cmd is None:
            self.__error_except(self.gpio_output_write, 2)
        self.sendMsg(cmd)
        if self.readMessage() == "ok":
            return 1
        else:
            self.__error_except(self.gpio_output_write, 1)

    def gpio_input_read(self, name):
        """Read the input value of a GPIO pin.

        Args:
            name (str): Pin name ("A0", "A1", "D0", or "D1").

        Returns:
            str: Input value of the specified pin.

        Raises:
            Exception: If pin name is invalid or response parse fails.
        """
        pin = name.capitalize()
        self.sendMsg("o131?")
        response = self.readMessage()
        self.readMessage()
        match = re.match(r'^(\d+),(\d+),(\d+),(\d+)$', response)
        if match:
            result = parse_gpio_response(pin, match)
            if result is None:
                self.__error_except(self.gpio_input_read, 2)
            return result
        else:
            self.__error_except(self.gpio_input_read, 3)

    def gpio_enable_write(self, name, num):
        """Enable or disable a GPIO pin.

        Args:
            name (str): Pin name ("A0", "A1", "D0", or "D1").
            num (int): Enable state (0=disabled, 1=enabled).

        Returns:
            int: 1 on success.

        Raises:
            Exception: If pin name is invalid or command fails.
        """
        pin = name.capitalize()
        cmd = build_gpio_cmd("o132", pin, num)
        if cmd is None:
            self.__error_except(self.gpio_enable_write, 2)
        self.sendMsg(cmd)
        if self.readMessage() == "ok":
            return 1
        else:
            self.__error_except(self.gpio_enable_write, 1)

    def gpio_enable_read(self, name):
        """Read the enable state of a GPIO pin.

        Args:
            name (str): Pin name ("A0", "A1", "D0", or "D1").

        Returns:
            str: Enable state of the specified pin.

        Raises:
            Exception: If pin name is invalid or response parse fails.
        """
        pin = name.capitalize()
        self.sendMsg("o132?")
        response = self.readMessage()
        self.readMessage()
        match = re.match(r'^(\d+),(\d+),(\d+),(\d+)$', response)
        if match:
            result = parse_gpio_response(pin, match)
            if result is None:
                self.__error_except(self.gpio_enable_read, 2)
            return result
        else:
            self.__error_except(self.gpio_enable_read, 3)

    def gpio_threshold_write(self, name, num):
        """Set the trigger threshold for a GPIO pin.

        Args:
            name (str): Pin name ("A0", "A1", "D0", or "D1").
            num (int): Threshold value.

        Returns:
            int: 1 on success.

        Raises:
            Exception: If pin name is invalid or command fails.
        """
        pin = name.capitalize()
        cmd = build_gpio_cmd("o133", pin, num)
        if cmd is None:
            self.__error_except(self.gpio_threshold_write, 2)
        self.sendMsg(cmd)
        if self.readMessage() == "ok":
            return 1
        else:
            self.__error_except(self.gpio_threshold_write, 1)

    def gpio_threshold_read(self, name):
        """Read the trigger threshold of a GPIO pin.

        Args:
            name (str): Pin name ("A0", "A1", "D0", or "D1").

        Returns:
            str: Threshold value of the specified pin.

        Raises:
            Exception: If pin name is invalid or response parse fails.
        """
        pin = name.capitalize()
        self.sendMsg("o133?")
        response = self.readMessage()
        self.readMessage()
        match = re.match(r'^(\d+),(\d+),(\d+),(\d+)$', response)
        if match:
            result = parse_gpio_response(pin, match)
            if result is None:
                self.__error_except(self.gpio_threshold_read, 2)
            return result
        else:
            self.__error_except(self.gpio_threshold_read, 3)

    def gpio_enable_file_write(self, name, num):
        """Set the trigger file for a GPIO pin.

        Args:
            name (str): Pin name ("A0", "A1", "D0", or "D1").
            num: File number or identifier to associate with the pin trigger.

        Returns:
            int: 1 on success.

        Raises:
            Exception: If pin name is invalid or command fails.
        """
        pin = name.capitalize()
        cmd = build_gpio_cmd("o134", pin, num)
        if cmd is None:
            self.__error_except(self.gpio_enable_file_write, 2)
        self.sendMsg(cmd)
        if self.readMessage() == "ok":
            return 1
        else:
            self.__error_except(self.gpio_enable_file_write, 1)

    def gpio_enable_file_read(self, name):
        """Read the trigger file associated with a GPIO pin.

        Args:
            name (str): Pin name ("A0", "A1", "D0", or "D1").

        Returns:
            str: Trigger file identifier for the specified pin.

        Raises:
            Exception: If pin name is invalid or response parse fails.
        """
        pin = name.capitalize()
        self.sendMsg("o134?")
        response = self.readMessage()
        self.readMessage()
        match = re.match(r'^(.*),(.*),(.*),(.*)$', response)
        if match:
            result = parse_gpio_response(pin, match)
            if result is None:
                self.__error_except(self.gpio_enable_file_read, 2)
            return result
        else:
            self.__error_except(self.gpio_enable_file_read, 3)

    # Deprecated aliases -- will be removed in v1.2
    @deprecated_alias("readMessage", version=1.2)
    def read_message(self, *args, **kwargs): ...

    @deprecated_alias("writeCoordinate", version=1.2)
    def writecoordinate(self, *args, **kwargs): ...

    @deprecated_alias("writeAngle", version=1.2)
    def writeangle(self, *args, **kwargs): ...

    @deprecated_alias("writeExpand", version=1.2)
    def writeexpand(self, *args, **kwargs): ...

    @deprecated_alias("getCoordinate", version=1.2)
    def getcoordinate(self, *args, **kwargs): ...

    @deprecated_alias("getPump", version=1.2)
    def getpump(self, *args, **kwargs): ...

    @deprecated_alias("getMode", version=1.2)
    def getmode(self, *args, **kwargs): ...
