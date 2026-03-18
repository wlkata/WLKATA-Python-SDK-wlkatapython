"""Base class for WLKATA robotic arm and controller communication.

This module defines :class:`WLKATA_UART`, the abstract base class that every
WLKATA robot driver inherits from.  It handles UART / RS485 serial transport,
G-code command formatting, status parsing, GPIO helpers, and axis-aware
motion commands.

Subclasses **must** define three class-level attributes:

* ``axis_count``  (``int``)  — number of motion axes (``4`` or ``6``).
* ``_version_prefix``  (``str``)  — expected prefix of the firmware version
  response (e.g. ``"Mirobot"``, ``"E4"``).
* ``_homing_fallback``  (``str``)  — command sent when the requested homing
  mode is not in the valid set (e.g. ``"o105=8"``, ``"$h"``).
"""

from __future__ import annotations

import re
import time
from abc import ABC
from typing import Any, Callable, Union

import serial


class WLKATA_UART(ABC):
    """Abstract base class for WLKATA robot UART/RS485 communication.

    Subclasses must set ``axis_count``, ``_version_prefix``, and
    ``_homing_fallback`` as class attributes.  Failing to do so will raise
    ``TypeError`` at instantiation.
    """

    # --- mandatory class attributes (enforced by __init_subclass__) ----------

    axis_count: int              # 4 or 6
    _version_prefix: str         # e.g. "Mirobot", "E4"
    _homing_fallback: str        # e.g. "o105=8", "$h"

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Ensure every concrete subclass declares required class attributes.

        Raises:
            TypeError: If a subclass is missing ``axis_count``,
                ``_version_prefix``, or ``_homing_fallback``.
        """
        super().__init_subclass__(**kwargs)
        for attr in ("axis_count", "_version_prefix", "_homing_fallback"):
            if not hasattr(cls, attr):
                raise TypeError(
                    f"Subclass {cls.__name__} must define class attribute '{attr}'"
                )

    # --- axis-dependent lookup tables (built once per subclass) --------------

    # Angle map: axis number → state-dict key
    _ANGLE_MAP_6 = {
        1: "angle_X", 2: "angle_Y", 3: "angle_Z",
        4: "angle_A", 5: "angle_B", 6: "angle_C", 7: "angle_D",
    }
    _ANGLE_MAP_4 = {
        1: "angle_X", 2: "angle_Y", 3: "angle_Z",
        4: "angle_A", 7: "angle_D",
    }

    # Coordinate map: axis number → state-dict key
    _COORD_MAP_6 = {
        1: "coordinate_X", 2: "coordinate_Y", 3: "coordinate_Z",
        4: "coordinate_RX", 5: "coordinate_RY", 6: "coordinate_RZ",
    }
    _COORD_MAP_4 = {
        1: "coordinate_X", 2: "coordinate_Y", 3: "coordinate_Z",
        4: "coordinate_RX",
    }

    # Homing: valid modes per axis count
    _VALID_HOMING_MODES_6 = set(range(0, 11))          # 0-10
    _VALID_HOMING_MODES_4 = {0, 1, 2, 3, 4, 7, 8, 9, 10}

    # Axis labels used in G-code commands
    _AXES_6 = ("X", "Y", "Z", "A", "B", "C")
    _AXES_4 = ("X", "Y", "Z", "A")

    def __init__(self) -> None:
        """Initialize the WLKATA UART communication interface.

        Sets up internal state variables for robot status tracking, GPIO
        control, and resolves axis-dependent lookup tables based on
        ``axis_count``.

        Raises:
            ValueError: If ``axis_count`` is not ``4`` or ``6``.
        """
        self.__message_flag = False
        self.mirobot_state_all = {
            "state": "-1",
            "angle_A": -1, "angle_B": -1, "angle_C": -1, "angle_D": -1,
            "angle_X": -1, "angle_Y": -1, "angle_Z": -1,
            "coordinate_X": -1, "coordinate_Y": -1, "coordinate_Z": -1,
            "coordinate_RX": -1, "coordinate_RY": -1, "coordinate_RZ": -1,
            "pump": -1, "valve": -1, "mode": -1
        }
        self.gpio_state = [0, 0, 0, 0]

        # resolve axis-dependent tables once
        if self.axis_count == 6:
            self._angle_map = self._ANGLE_MAP_6
            self._coord_map = self._COORD_MAP_6
            self._valid_homing_modes = self._VALID_HOMING_MODES_6
            self._axes = self._AXES_6
        elif self.axis_count == 4:
            self._angle_map = self._ANGLE_MAP_4
            self._coord_map = self._COORD_MAP_4
            self._valid_homing_modes = self._VALID_HOMING_MODES_4
            self._axes = self._AXES_4
        else:
            raise ValueError(f"Unsupported axis_count: {self.axis_count} (must be 4 or 6)")
        

    def message_print(self, flag: bool) -> None:
        """Enable or disable debug printing of sent/received messages.

        Args:
            flag: ``True`` to print every serial read/write to *stdout*,
                ``False`` to suppress output.
        """
        self.__message_flag = flag

    def read_message(self) -> str:
        """Read a single line from the serial port.

        Returns:
            The decoded line (stripped of whitespace), or ``"read error"``
            if no data is waiting.
        """
        if self.pSerial.in_waiting > 0:
            line = self.pSerial.readline().decode('utf-8').strip()
            if self.__message_flag:
                print(f"read:\t{line}")
            return line
        else:
            return "read error"

    def sendMsg(self, message: str) -> None:
        """Send a command string to the robot.

        A ``\\r\\n`` terminator is appended automatically.  When an RS485
        address is configured (``address != -1``), the message is prefixed
        with ``@<address>``.

        Args:
            message: The command string to send (without ``\\r\\n``).
        """
        message = f"{message}\r\n"

        if self.address != -1:
            message = f"@{self.address}{message}"

        self.pSerial.write(message.encode("utf-8"))

        if self.__message_flag:
            print(f"write:\t{message}")

        time.sleep(0.1)

    def init(self, p: serial.Serial, adr: int) -> None:
        """Bind a serial port and set the RS485 address.

        This must be called before any other communication method.

        Args:
            p: An open ``serial.Serial`` instance.
            adr: RS485 address (``0``-``255``), or ``-1`` for plain UART mode.
        """
        self.pSerial = p
        self.address = adr


    def homing(self, mode: int = 8) -> None:
        """Perform robot homing (return to home position).

        The set of accepted modes is determined by ``axis_count``.  If *mode*
        is not in the valid set, the class-level ``_homing_fallback`` command
        is sent instead.

        Note:
            Homing is asynchronous — the robot may still be moving after
            this method returns.

        Args:
            mode: Homing mode.  Defaults to ``8``.
        """
        if mode in self._valid_homing_modes:
            self.sendMsg(f"o105={mode}")
        else:
            self.sendMsg(self._homing_fallback)

    def runFile(self, fileName: Union[str, int], num: bool = False) -> int:
        """Execute an offline program file stored on the robot controller.

        Args:
            fileName: Name or number of the file to execute.
            num: If ``True``, use the ``o112`` command (by number);
                otherwise use ``o111`` (by name).

        Returns:
            ``1`` on success.

        Raises:
            Exception: If the controller replies with an error or no ``"ok"``.
        """
        cmd = "o112" if num else "o111"
        self.sendMsg(f"{cmd}{fileName}")

        reply = self.read_message()
        if reply == "ok":
            return 1
        elif reply == "error":
            self.__error_except(self.runFile, 4)
        else:
            self.__error_except(self.runFile, 1)

    def cancellation(self) -> int:
        """Stop the current robot movement immediately.

        Returns:
            ``1`` on success.

        Raises:
            Exception: If the controller does not reply ``"ok"``.
        """
        self.sendMsg("o117")
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.cancellation, 1)

    def gripper(self, num: int) -> int:
        """Control the gripper (if equipped).

        Args:
            num: Gripper command — ``0`` = open/release, ``1`` = close
                (medium force), ``2`` = close (high force).

        Returns:
            ``1`` on success.

        Raises:
            Exception: If the controller does not reply ``"ok"``.
        """
        pwm = {0: 0, 1: 40, 2: 60}.get(num, 0)
        self.sendMsg(f"M3 S{pwm}")
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.gripper, 1)

    def pump(self, num: int) -> int:
        """Control the air pump (if equipped).

        Args:
            num: Pump command — ``0`` = off, ``1`` = full power (PWM 1000),
                ``2`` = half power (PWM 500).

        Returns:
            ``1`` on success.

        Raises:
            Exception: If the controller does not reply ``"ok"``.
        """
        pwm = {0: 0, 1: 1000, 2: 500}.get(num, 0)
        self.sendMsg(f"M3 S{pwm}")
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.pump, 1)

    def pwmWrite(self, num: int) -> int:
        """Set the PWM output directly.

        Args:
            num: PWM duty value in the range ``0``–``1000``.

        Returns:
            ``1`` on success.

        Raises:
            Exception: If the controller does not reply ``"ok"``.
        """
        self.sendMsg(f"M3 S{num}")
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.pwmWrite, 1)

    def zero(self) -> None:
        """Move all axes to their zero/reference positions.

        The number of axes zeroed is determined by ``axis_count``.

        Note:
            Movement is asynchronous — the robot may still be moving after
            this method returns.
        """
        coords = "".join(f"{ax}0" for ax in self._axes)
        self.sendMsg(f"M21 G90 G00 {coords}")

    def writecoordinate(self, motion: int, position: int, *axes_values: float) -> None:
        """Move the robot to specified Cartesian coordinates.

        Args:
            motion: Movement type — ``0`` = fast (G00), ``1`` = linear (G01),
                ``2`` = joint/gate (G05).
            position: Coordinate mode — ``0`` = absolute (G90),
                ``1`` = incremental (G91).
            *axes_values: Coordinate values matching the robot's axes.
                6-axis robots expect ``(x, y, z, a, b, c)``;
                4-axis robots expect ``(x, y, z, a)``.
        """
        motion_code = {0: "G00", 1: "G01", 2: "G05"}.get(motion, "G00")
        position_code = {0: "G90", 1: "G91"}.get(position, "G90")
        coords = "".join(f"{ax}{val}" for ax, val in zip(self._axes, axes_values))
        self.sendMsg(f"M20{position_code}{motion_code}{coords}")

    def speed(self, num: int) -> int:
        """Set the robot movement speed.

        Args:
            num: Speed value in the range ``0``–``100``.

        Returns:
            ``1`` on success.

        Raises:
            Exception: If the controller does not reply ``"ok"``.
        """
        self.sendMsg(f"F{num}")
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.speed, 1)

    def writeangle(self, position: int, *axes_values: float) -> None:
        """Move the robot to specified joint angles.

        Args:
            position: Coordinate mode — ``0`` = absolute (G90),
                ``1`` = incremental (G91).
            *axes_values: Angle values matching the robot's axes.
                6-axis robots expect ``(x, y, z, a, b, c)``;
                4-axis robots expect ``(x, y, z, a)``.
        """
        position_code = {0: "G90", 1: "G91"}.get(position, "G90")
        coords = "".join(f"{ax}{val}" for ax, val in zip(self._axes, axes_values))
        self.sendMsg(f"M21{position_code}G00{coords}")

    def writeexpand(self, motion: int, position: int, d: float) -> None:
        """Move the 7th (expansion) axis.

        Args:
            motion: Movement type — ``0`` = fast (G00), ``1`` = linear (G01).
            position: Coordinate mode — ``0`` = absolute (G90),
                ``1`` = incremental (G91).
            d: Target position or offset for the 7th axis.
        """
        motion_code = {0: "G00", 1: "G01"}.get(motion, "G00")
        position_code = {0: "G90", 1: "G91"}.get(position, "G90")
        self.sendMsg(f"{position_code}{motion_code}D{d}")

    def restart(self) -> int:
        """Restart the robot controller.

        Returns:
            ``1`` on success.

        Raises:
            Exception: If the controller does not reply ``"ok"``.
        """
        self.sendMsg("o100")
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.restart, 1)

    def version(self) -> Union[tuple[str, str], str]:
        """Query the firmware version of the robot controller.

        Sends the ``$V`` command and waits for a two-line response whose
        first line starts with ``"EXbox"`` and whose second line starts
        with ``_version_prefix``.

        Note:
            Currently only available in UART mode, not RS485.

        Returns:
            A ``(controller_version, robot_version)`` tuple on success,
            or ``"Query failed"`` if no valid response is received within
            five attempts.

        Raises:
            UnicodeDecodeError: If the serial response cannot be decoded.
        """
        self.pSerial.flushInput()
        self.pSerial.flushOutput()
        self.sendMsg("$V")

        for _ in range(5):
            line1 = self.pSerial.readline().decode('utf-8').strip()
            line2 = self.pSerial.readline().decode('utf-8').strip()

            if line1.startswith('EXbox') and line2.startswith(self._version_prefix):
                return line1, line2

            time.sleep(0.1)

        return "Query failed"

    # --- internal error helper ------------------------------------------------

    _ERROR_MESSAGES: dict[int, str] = {
        1: "No reply - 'ok'",
        2: "parameter error",
        3: "regular expression error",
        4: "File run error",
    }

    def __error_except(self, f: Callable[..., Any], num: int) -> None:
        """Raise an ``Exception`` with a standardised message.

        Args:
            f: The calling method (used for its ``__name__``).
            num: Error code key into ``_ERROR_MESSAGES``.

        Raises:
            Exception: If *num* maps to a known message.
        """
        msg = self._ERROR_MESSAGES.get(num)
        if msg:
            raise Exception(f"{f.__name__}: {msg}")

    def getStatus(self) -> Union[dict[str, str], str, int]:
        """Query and update the full status of the robot.

        Sends a ``?`` command and parses the angle / coordinate / pump /
        valve / mode response.

        Returns:
            A status dictionary on success, ``-1`` if the response could not
            be parsed, or ``"error"`` if no data was waiting on the serial
            port.
        """
        self.pSerial.flushInput()
        self.pSerial.flushOutput()
        self.sendMsg("?")
        if self.pSerial.in_waiting > 0:
            line = self.pSerial.readline().decode('utf-8').strip()
            if line.startswith("<") and line.endswith(">"):
                data = self.__parse_response(line)
            else:
                data = -1
        else:
            return "error"

        time.sleep(0.1)
        return data

    # --- status response parsing ----------------------------------------------

    _STATUS_PATTERN: re.Pattern[str] = re.compile(
        r'<(\w+),Angle\(ABCDXYZ\):([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),'
        r'Cartesian coordinate\(XYZ RxRyRz\):([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),'
        r'Pump PWM:([\d.-]+),Valve PWM:([\d.-]+),Motion_MODE:([\d.-]+)>'
    )

    _STATUS_KEYS: list[str] = [
        "state",
        "angle_A", "angle_B", "angle_C", "angle_D",
        "angle_X", "angle_Y", "angle_Z",
        "coordinate_X", "coordinate_Y", "coordinate_Z",
        "coordinate_RX", "coordinate_RY", "coordinate_RZ",
        "pump", "valve", "mode",
    ]

    def __parse_response(self, line: str) -> Union[dict[str, str], str]:
        """Parse a ``<…>`` status response into a dictionary.

        Args:
            line: The raw status line (including angle brackets).

        Returns:
            A dictionary keyed by ``_STATUS_KEYS``, or ``"parse error"``
            if the line does not match the expected pattern.
        """
        match = self._STATUS_PATTERN.match(line)
        if match:
            self.mirobot_state_all = dict(zip(self._STATUS_KEYS, match.groups()))
            return self.mirobot_state_all
        else:
            return "parse error"

    def getState(self) -> str:
        """Return the current motion state of the robot (e.g. ``"Idle"``, ``"Run"``).

        Returns:
            The state string from the most recent status query.
        """
        self.getStatus()
        return self.mirobot_state_all["state"]

    def getAngle(self, num: int) -> str:
        """Get the angle of a specific robot axis.

        Args:
            num: Axis number.  Valid values depend on ``axis_count``:
                6-axis — ``1`` (X), ``2`` (Y), ``3`` (Z), ``4`` (A),
                ``5`` (B), ``6`` (C), ``7`` (D).
                4-axis — ``1`` (X), ``2`` (Y), ``3`` (Z), ``4`` (A),
                ``7`` (D).

        Returns:
            The current angle as a numeric string.

        Raises:
            Exception: If *num* does not map to a valid axis.
        """
        key = self._angle_map.get(num)
        if key is None:
            self.__error_except(self.getAngle, 2)
            return
        self.getStatus()
        return self.mirobot_state_all[key]

    def getcoordinate(self, num: int) -> str:
        """Get a Cartesian coordinate of the robot end-effector.

        Args:
            num: Coordinate axis.  Valid values depend on ``axis_count``:
                6-axis — ``1`` (X), ``2`` (Y), ``3`` (Z), ``4`` (RX),
                ``5`` (RY), ``6`` (RZ).
                4-axis — ``1`` (X), ``2`` (Y), ``3`` (Z), ``4`` (RX).

        Returns:
            The current coordinate as a numeric string.

        Raises:
            Exception: If *num* does not map to a valid coordinate.
        """
        key = self._coord_map.get(num)
        if key is None:
            self.__error_except(self.getcoordinate, 2)
            return
        self.getStatus()
        return self.mirobot_state_all[key]

    def getpump(self) -> str:
        """Get the current pump PWM value.

        Returns:
            The pump PWM value as a numeric string.
        """
        self.getStatus()
        return self.mirobot_state_all["pump"]

    def getmode(self) -> str:
        """Get the current motion mode of the robot.

        Returns:
            The motion mode as a numeric string.
        """
        self.getStatus()
        return self.mirobot_state_all["mode"]


    # ---- GPIO helpers --------------------------------------------------------

    def gpio_init(self) -> int:
        """Disable all GPIO enables (reset to 0).

        Returns:
            ``1`` on success.

        Raises:
            Exception: If the controller does not reply ``"ok"``.
        """
        self.gpio_state = [0, 0, 0, 0]
        self.sendMsg("o132=0,0,0,0")
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.gpio_init, 1)

    _GPIO_PIN_INDEX: dict[str, int] = {"A0": 0, "A1": 1, "D0": 2, "D1": 3}

    def __gpio_pin_cmd(self, cmd_prefix: str, name: str, value: Any) -> str | None:
        """Build a GPIO command that places *value* at the correct pin slot.

        Args:
            cmd_prefix: Command prefix, e.g. ``"o130="``.
            name: Pin name — ``"A0"``, ``"A1"``, ``"D0"``, or ``"D1"``
                (case-insensitive).
            value: Value to place at the pin position.

        Returns:
            The formatted command string, or ``None`` if *name* is invalid.
        """
        pin_name = name.capitalize()
        idx = self._GPIO_PIN_INDEX.get(pin_name)
        if idx is None:
            return None
        parts = [""] * 4
        parts[idx] = str(value)
        return f"{cmd_prefix}{','.join(parts)}"

    def __gpio_pin_read(
        self,
        query_cmd: str,
        name: str,
        caller: Callable[..., Any],
        pattern: str = r'^([\d]+),([\d]+),([\d]+),([\d]+)$',
    ) -> str | None:
        """Send a GPIO query and return the value for the specified pin.

        Args:
            query_cmd: Query command to send, e.g. ``"o130?"``.
            name: Pin name — ``"A0"``, ``"A1"``, ``"D0"``, or ``"D1"``
                (case-insensitive).
            caller: The calling method (used for error reporting).
            pattern: Regex with four capture groups to parse the response.

        Returns:
            The matched value string for the requested pin.

        Raises:
            Exception: If the pin name is invalid or the response does not
                match *pattern*.
        """
        pin_name = name.capitalize()
        idx = self._GPIO_PIN_INDEX.get(pin_name)
        if idx is None:
            self.__error_except(caller, 2)
            return
        self.sendMsg(query_cmd)
        response = self.read_message()
        self.read_message()  # consume second line
        match = re.match(pattern, response)
        if match:
            return match.group(idx + 1)
        else:
            self.__error_except(caller, 3)

    def gpio_mode_write(self, name: str, num: int) -> int:
        """Set the GPIO mode for a pin.

        Args:
            name: Pin name (``"A0"``, ``"A1"``, ``"D0"``, or ``"D1"``).
            num: Mode value to write.

        Returns:
            ``1`` on success.

        Raises:
            Exception: On invalid pin name or missing ``"ok"`` reply.
        """
        cmd = self.__gpio_pin_cmd("o130=", name, num)
        if cmd is None:
            self.__error_except(self.gpio_mode_write, 2)
            return
        self.sendMsg(cmd)
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.gpio_mode_write, 1)

    def gpio_mode_read(self, name: str) -> str:
        """Read the GPIO mode for a pin.

        Args:
            name: Pin name (``"A0"``, ``"A1"``, ``"D0"``, or ``"D1"``).

        Returns:
            The mode value as a string.

        Raises:
            Exception: On invalid pin name or unparseable response.
        """
        return self.__gpio_pin_read("o130?", name, self.gpio_mode_read)

    def gpio_output_write(self, name: str, num: int) -> int:
        """Set the GPIO digital/analog output value for a pin.

        Args:
            name: Pin name (``"A0"``, ``"A1"``, ``"D0"``, or ``"D1"``).
            num: Output value to write.

        Returns:
            ``1`` on success.

        Raises:
            Exception: On invalid pin name or missing ``"ok"`` reply.
        """
        cmd = self.__gpio_pin_cmd("o131=", name, num)
        if cmd is None:
            self.__error_except(self.gpio_output_write, 2)
            return
        self.sendMsg(cmd)
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.gpio_output_write, 1)

    def gpio_input_read(self, name: str) -> str:
        """Read the GPIO input value for a pin.

        Args:
            name: Pin name (``"A0"``, ``"A1"``, ``"D0"``, or ``"D1"``).

        Returns:
            The input value as a string.

        Raises:
            Exception: On invalid pin name or unparseable response.
        """
        return self.__gpio_pin_read("o131?", name, self.gpio_input_read)

    def gpio_enable_write(self, name: str, num: int) -> int:
        """Set the GPIO enable state for a pin.

        Args:
            name: Pin name (``"A0"``, ``"A1"``, ``"D0"``, or ``"D1"``).
            num: Enable value (``0`` = disabled, ``1`` = enabled).

        Returns:
            ``1`` on success.

        Raises:
            Exception: On invalid pin name or missing ``"ok"`` reply.
        """
        cmd = self.__gpio_pin_cmd("o132=", name, num)
        if cmd is None:
            self.__error_except(self.gpio_enable_write, 2)
            return
        self.sendMsg(cmd)
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.gpio_enable_write, 1)

    def gpio_enable_read(self, name: str) -> str:
        """Read the GPIO enable state for a pin.

        Args:
            name: Pin name (``"A0"``, ``"A1"``, ``"D0"``, or ``"D1"``).

        Returns:
            The enable state as a string.

        Raises:
            Exception: On invalid pin name or unparseable response.
        """
        return self.__gpio_pin_read("o132?", name, self.gpio_enable_read)

    def gpio_threshold_write(self, name: str, num: int) -> int:
        """Set the GPIO trigger threshold for a pin.

        Args:
            name: Pin name (``"A0"``, ``"A1"``, ``"D0"``, or ``"D1"``).
            num: Threshold value.

        Returns:
            ``1`` on success.

        Raises:
            Exception: On invalid pin name or missing ``"ok"`` reply.
        """
        cmd = self.__gpio_pin_cmd("o133=", name, num)
        if cmd is None:
            self.__error_except(self.gpio_threshold_write, 2)
            return
        self.sendMsg(cmd)
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.gpio_threshold_write, 1)

    def gpio_threshold_read(self, name: str) -> str:
        """Read the GPIO trigger threshold for a pin.

        Args:
            name: Pin name (``"A0"``, ``"A1"``, ``"D0"``, or ``"D1"``).

        Returns:
            The threshold value as a string.

        Raises:
            Exception: On invalid pin name or unparseable response.
        """
        return self.__gpio_pin_read("o133?", name, self.gpio_threshold_read)

    def gpio_enable_file_write(self, name: str, num: int) -> int:
        """Set the GPIO trigger file number for a pin.

        Args:
            name: Pin name (``"A0"``, ``"A1"``, ``"D0"``, or ``"D1"``).
            num: File number to associate with the pin trigger.

        Returns:
            ``1`` on success.

        Raises:
            Exception: On invalid pin name or missing ``"ok"`` reply.
        """
        cmd = self.__gpio_pin_cmd("o134=", name, num)
        if cmd is None:
            self.__error_except(self.gpio_enable_file_write, 2)
            return
        self.sendMsg(cmd)
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.gpio_enable_file_write, 1)

    def gpio_enable_file_read(self, name: str) -> str:
        """Read the GPIO trigger file name for a pin.

        Args:
            name: Pin name (``"A0"``, ``"A1"``, ``"D0"``, or ``"D1"``).

        Returns:
            The trigger file name/number as a string.

        Raises:
            Exception: On invalid pin name or unparseable response.
        """
        return self.__gpio_pin_read("o134?", name, self.gpio_enable_file_read,
                                    pattern=r'^(.*),(.*),(.*),(.*)$')
