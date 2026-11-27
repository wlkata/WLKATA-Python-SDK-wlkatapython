"""WLKATA Miromax UART/RS485 control class.

Shares the Harobot's motion commands (G07/G01 Cartesian, G09 angles) and its
status parser, which also reads the Miromax's pipe-separated status line. The
Miromax differs in how it homes, in its end effectors (analog channels 10-11
and 20-25 rather than channel 0) and in how a motion is cancelled.
"""

import time
from typing import Optional

from ..transports import Connection
from .Harobot_UART import Harobot_UART


class Miromax_UART(Harobot_UART):
    """Control class for the WLKATA Miromax robotic arm.

    Motion commands match ``Harobot_UART``. Model-specific values live on
    class attributes so they can diverge without forking protocol methods.
    """

    _VERSION_PREFIX = "Miromax"
    _VALID_HOMING_MODES = set(range(11))
    # Mode 8 is the bare $h; the other modes are $h{mode}
    _HOMING_OVERRIDES = {8: "$h"}
    _HOMING_FALLBACK = "$h8"
    # Unlike the Harobot, the Miromax homes without restarting first
    _HOMING_RESTARTS = False

    # Analog channels (the E word of M67) an end effector may be wired to
    _ANALOG_PINS = (10, 11, 20, 21, 22, 23, 24, 25)
    _DEFAULT_ANALOG_PIN = 10

    # Pneumatic end effectors: Q value per command, 0 (power off) otherwise
    _SUCTION_Q = {1: 100}
    _PNEUMATIC_GRIPPER_Q = {1: 75, 2: 25}

    # Electric gripper: Q is this value when off, lower by the speed level to
    # open and higher by it to close
    _GRIPPER_PINS = (20, 21, 22, 23)
    _DEFAULT_GRIPPER_PIN = 20
    _GRIPPER_OFF_Q = 92.5
    _GRIPPER_SPEEDS = (1, 5)

    def __init__(
        self,
        p: Optional[Connection] = None,
        adr: Optional[int] = None,
        message_flag: bool = False,
    ):
        super().__init__(p, adr, message_flag=message_flag)

    def _analog_write(self, pin, q):
        """Send one analog output; an unknown pin falls back to the default."""
        if pin not in self._ANALOG_PINS:
            pin = self._DEFAULT_ANALOG_PIN
        self.sendMsg(f"M67 E{pin} Q{q}")

    def gripper(self, num=0, pin=20, speed=5):
        """Control the electric gripper.

        Args:
            num (int): 1 to open, 2 to close, anything else to power off.
            pin (int): Analog channel the gripper is on (20-23). Defaults to
                20, which is also used for any other value.
            speed (int): Speed level 1-5 (clamped). Defaults to 5.
        """
        if pin not in self._GRIPPER_PINS:
            pin = self._DEFAULT_GRIPPER_PIN
        slowest, fastest = self._GRIPPER_SPEEDS
        level = min(max(int(speed), slowest), fastest)
        if num == 1:
            q = self._GRIPPER_OFF_Q - level
        elif num == 2:
            q = self._GRIPPER_OFF_Q + level
        else:
            q = self._GRIPPER_OFF_Q
        self.sendMsg(f"M67 E{pin} Q{q}")

    def pump(self, num):
        """Not available on the Miromax.

        Raises:
            NotImplementedError: Always. Use ``pumpSuction``, ``pumpGripper``
                or ``pumpSoftGripper`` for the pneumatic end effectors.
        """
        raise NotImplementedError(
            "Miromax_UART has no pump(); use pumpSuction(), pumpGripper() "
            "or pumpSoftGripper()"
        )

    def pumpSuction(self, num=0, pin=10):
        """Control the vacuum suction cup.

        Args:
            num (int): 1 to suck, anything else to power off.
            pin (int): Analog channel. Defaults to 10.
        """
        self._analog_write(pin, self._SUCTION_Q.get(num, 0))

    def pumpGripper(self, num=0, pin=10):
        """Control the pneumatic gripper.

        Args:
            num (int): 1 to open, 2 to close, anything else to power off.
            pin (int): Analog channel. Defaults to 10.
        """
        self._analog_write(pin, self._PNEUMATIC_GRIPPER_Q.get(num, 0))

    def pumpSoftGripper(self, num=0, pin=10):
        """Control the pneumatic soft gripper (same output as ``pumpGripper``).

        Args:
            num (int): 1 to open, 2 to close, anything else to power off.
            pin (int): Analog channel. Defaults to 10.
        """
        self._analog_write(pin, self._PNEUMATIC_GRIPPER_Q.get(num, 0))

    def pwmWrite(self, num, pin=10):
        """Write a raw value to an analog channel.

        Args:
            num: Output value (0-100).
            pin (int): Analog channel. Defaults to 10.
        """
        self._analog_write(pin, num)

    def cancellation(self, timeout=30):
        """Stop the current motion.

        Pauses the arm (``!``), waits for it to finish decelerating (status
        ``Hold:0``, or ``Idle`` if it was not moving), then stops (``%``) and
        waits for Idle. If the arm never reports ``Hold:0``, the stop is not
        sent.

        Args:
            timeout (float): Maximum seconds for each of the two waits. 0
                means no timeout.

        Returns:
            bool: True once the arm is Idle after the stop, False on timeout.
        """
        self.sendMsg("!")
        if not self._waitHoldSettled(timeout):
            return False
        self.sendMsg("%")
        return self._waitIdlePoll(timeout)

    def _waitHoldSettled(self, timeout=30):
        """Poll status until the pause has settled or *timeout* passes."""
        deadline = time.monotonic() + timeout if timeout else None
        while True:
            if self.getState() in ("Hold:0", "Idle"):
                return True
            if deadline and time.monotonic() > deadline:
                return False
            time.sleep(0.1)


if __name__ == "__main__":
    import serial

    robot = Miromax_UART(message_flag=True)
    robot.init(serial.Serial("COM4", 115200, timeout=1), -1)
    robot.restart()
    robot.homing()
    robot.writeAngle(0, axle1=70)
    robot.writeCoordinate(0, 0, 220)
    robot.zero()
