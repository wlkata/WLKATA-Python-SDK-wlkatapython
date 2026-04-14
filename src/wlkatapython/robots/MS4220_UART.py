import serial

from .base import WLKATA_UART


class MS4220_UART(WLKATA_UART):
    """Control class for the WLKATA MS4220 stepper motor controller.

    Inherits from WLKATA_UART and overrides communication methods
    for the MS4220's RS485-based protocol.
    """

    def __init__(self):
        """Initialize the MS4220 controller state."""
        super().__init__()
        self.address = None
        self.pSerial = None

    def init(self, p, adr):
        """Initialize the serial communication for the MS4220.

        Args:
            p: Serial port object (e.g., serial.Serial instance).
            adr (int): RS485 address (0-255, or -1 for UART mode).
        """
        self.pSerial = p
        self.address = adr

    def speed(self, num):
        """Set the stepper motor speed.

        Args:
            num (int): Speed value (-100 to 100).

        Returns:
            int: 1 on success.

        Raises:
            Exception: If speed setting fails.
        """
        if num > 100:
            num = 100
        elif num < -100:
            num = -100
        self.sendMsg(f"G6 F{num}")

        if self.readMessage() == "ok":
            return 1
        else:
            self.__error_except(self.speed, 1)
