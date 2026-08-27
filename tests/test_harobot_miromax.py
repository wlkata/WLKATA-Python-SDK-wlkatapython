"""Unit tests for Harobot_UART and Miromax_UART (Harobot-family protocol)."""

from typing import Optional

import pytest

from wlkatapython import Harobot_UART, Miromax_UART
from wlkatapython.transports import Transport


class RecordingTransport(Transport):
    """In-memory transport that records writes and serves queued RX lines.

    Optional ``auto_replies`` maps a substring of the outbound message to a
    response line queued *after* write (survives flushInput done before write).
    """

    def __init__(self, auto_replies=None):
        self.writes = []
        self._rx = b""
        self._connected = True
        self._timeout = 1.0
        self.auto_replies = dict(auto_replies or {})

    def connect(self):
        self._connected = True

    def disconnect(self):
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def write(self, data: bytes):
        self.writes.append(data)
        text = data.decode("utf-8", errors="replace")
        for needle, reply in self.auto_replies.items():
            if needle in text:
                self.push_line(reply)

    def readline(self) -> bytes:
        if b"\n" in self._rx:
            line, _, self._rx = self._rx.partition(b"\n")
            return line + b"\n"
        out, self._rx = self._rx, b""
        return out

    def flushInput(self):
        self._rx = b""

    def flushOutput(self):
        return

    @property
    def in_waiting(self) -> int:
        return len(self._rx)

    @property
    def timeout(self) -> Optional[float]:
        return self._timeout

    @timeout.setter
    def timeout(self, value: Optional[float]):
        self._timeout = value

    def push_line(self, text: str):
        self._rx += text.encode("utf-8") + b"\n"

    @property
    def last_text(self) -> str:
        return self.writes[-1].decode("utf-8") if self.writes else ""


HAROBOT_STATUS = (
    "<Idle,Cartesian:100.0,20.0,30.0,1.0,2.0,3.0,0.0,"
    "Angle:10.0,20.0,30.0,40.0,50.0,60.0,70.0>"
)


@pytest.fixture
def harobot():
    t = RecordingTransport()
    robot = Harobot_UART()
    robot.init(t, -1)
    return robot, t


@pytest.fixture
def miromax():
    t = RecordingTransport()
    robot = Miromax_UART()
    robot.init(t, -1)
    return robot, t


class TestHarobotProtocol:
    def test_message_flag_init(self):
        robot = Harobot_UART(message_flag=True)
        assert robot.pSerial is None

    def test_gripper_pump_pwm(self, harobot):
        robot, t = harobot
        robot.gripper(1)
        assert "M67 E0 Q4" in t.last_text
        robot.gripper(99)  # unknown preset -> 0
        assert "M67 E0 Q0" in t.last_text
        robot.pump(1)
        assert "M67 E0 Q100" in t.last_text
        robot.pump(2)
        assert "M67 E0 Q50" in t.last_text
        robot.pwmWrite(42)
        assert "M67 E0 Q42" in t.last_text

    def test_write_coordinate_fast_and_linear(self, harobot):
        robot, t = harobot
        robot.writeCoordinate(0, 0, x=220, y=10)
        assert t.last_text.startswith("G07G90")
        assert "X220" in t.last_text and "Y10" in t.last_text
        assert "F4000" in t.last_text
        robot.writeCoordinate(1, 1, z=50)
        assert t.last_text.startswith("G01G91")
        assert "Z50" in t.last_text

    def test_write_angle_with_seventh_axis(self, harobot):
        robot, t = harobot
        robot.writeAngle(0, axle1=10, axle2=20, axle7=5)
        assert t.last_text.startswith("G09G90")
        assert "X10" in t.last_text and "Y20" in t.last_text
        assert "D5" in t.last_text
        assert "F4000" in t.last_text

    def test_get_status_parse_ok(self, harobot):
        robot, t = harobot
        t.auto_replies["?"] = HAROBOT_STATUS
        data = robot.getStatus()
        assert data != "error" and data != "parse error"
        assert data["state"] == "Idle"
        assert data["coordinate_X"] == "100.0"
        assert data["angle_X"] == "10.0"
        assert data["angle_D"] == "70.0"
        assert data["pump"] == -1

    def test_get_status_error_when_empty(self, harobot):
        robot, t = harobot
        assert robot.getStatus() == "error"

    def test_get_status_invalid_line(self, harobot):
        robot, t = harobot
        t.auto_replies["?"] = "not-a-status"
        assert robot.getStatus() == -1

    def test_parse_error(self, harobot):
        robot, _ = harobot
        assert robot._parse_status_response("<Idle,bad>") == "parse error"

    def test_parse_alias(self, harobot):
        robot, _ = harobot
        data = robot._parse_harobot_response(HAROBOT_STATUS)
        assert data["state"] == "Idle"

    def test_zero_cmd(self, harobot):
        robot, t = harobot
        robot.zero()
        assert "G9 G90" in t.last_text or robot._ZERO_CMD in t.last_text.replace("\r\n", "")


class TestMiromaxProtocol:
    def test_version_prefix_and_constants(self):
        assert Miromax_UART._VERSION_PREFIX == "Miromax"
        assert issubclass(Miromax_UART, Harobot_UART)

    def test_message_flag_init(self):
        robot = Miromax_UART(message_flag=False)
        assert robot.address is None

    def test_inherits_command_format(self, miromax):
        robot, t = miromax
        robot.writeCoordinate(0, 0, x=100)
        assert t.last_text.startswith("G07G90")
        assert "F4000" in t.last_text
        robot.writeAngle(0, axle1=15)
        assert t.last_text.startswith("G09G90")
        robot.gripper(1)
        assert "M67 E0 Q4" in t.last_text

    def test_get_status(self, miromax):
        robot, t = miromax
        t.auto_replies["?"] = HAROBOT_STATUS
        data = robot.getStatus()
        assert data["state"] == "Idle"
        assert data["coordinate_Y"] == "20.0"

    def test_override_feed_rate(self):
        class CustomMiromax(Miromax_UART):
            _FEED_RATE = 2000

        t = RecordingTransport()
        robot = CustomMiromax()
        robot.init(t, -1)
        robot.writeCoordinate(0, 0, x=1)
        assert "F2000" in t.last_text
