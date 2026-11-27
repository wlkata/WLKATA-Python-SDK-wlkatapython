"""Unit tests for Harobot_UART and Miromax_UART (Harobot-family protocol)."""

import time
from typing import Optional

import pytest

from wlkatapython import Harobot_UART, Miromax_UART
from wlkatapython.transports import Transport


class RecordingTransport(Transport):
    """In-memory transport that records writes and serves queued RX lines.

    Optional ``auto_replies`` maps a substring of the outbound message to a
    response line queued *after* write (survives flushInput done before write).
    A list of lines is served one per write, the last one repeating.
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
                if isinstance(reply, list):
                    reply = reply.pop(0) if len(reply) > 1 else reply[0]
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

    @property
    def sent(self) -> list:
        """Every command written so far, without its line ending."""
        return [w.decode("utf-8").strip() for w in self.writes]


HAROBOT_STATUS = (
    "<Idle,Cartesian:100.0,20.0,30.0,1.0,2.0,3.0,0.0,"
    "Angle:10.0,20.0,30.0,40.0,50.0,60.0,70.0>"
)

MIROMAX_STATUS = (
    "<Idle|Cartesian:100.0,20.0,30.0,1.0,2.0,3.0|"
    "Angle:10.0,20.0,30.0,40.0,50.0,60.0,70.0>"
)


def miromax_status(state):
    return MIROMAX_STATUS.replace("<Idle", f"<{state}")


@pytest.fixture
def sleeps(monkeypatch):
    """Make time.sleep return at once, recording the requested seconds."""
    calls = []
    monkeypatch.setattr(time, "sleep", calls.append)
    return calls


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
        assert t.sent[-1] == "G07G90X220Y10"
        robot.writeCoordinate(1, 1, z=50)
        assert t.sent[-1] == "G01G91Z50"

    def test_write_coordinate_unknown_motion_is_fast(self, harobot):
        robot, t = harobot
        robot.writeCoordinate(7, 0, x=1)
        assert t.sent[-1] == "G07G90X1"

    def test_write_angle_with_seventh_axis(self, harobot):
        robot, t = harobot
        robot.writeAngle(0, axle1=10, axle2=20, axle7=5)
        assert t.sent[-1] == "G09G90X10Y20D5"

    def test_override_feed_rate(self, harobot):
        class FedHarobot(Harobot_UART):
            _FEED_RATE = 2000

        t = RecordingTransport()
        robot = FedHarobot()
        robot.init(t, -1)
        robot.writeCoordinate(0, 0, x=1)
        assert t.sent[-1] == "G07G90X1F2000"
        robot.writeAngle(0, axle1=1)
        assert t.sent[-1] == "G09G90X1F2000"

    def test_zero_cmd(self, harobot):
        robot, t = harobot
        robot.zero()
        assert t.sent[-1] == "G9 G90 X0 Y0 Z0 A0 B0 C0"

    def test_homing_restarts_then_homes(self, harobot, sleeps):
        robot, t = harobot
        t.auto_replies["o100"] = "ok"
        robot.homing()
        assert t.sent == ["o100", "$h8"]
        assert 3.0 in sleeps  # the controller is given time to come back
        assert t.in_waiting == 0  # restart chatter is dropped before homing

    @pytest.mark.parametrize("mode, command", [
        (0, "$h0"), (3, "$h3"), (8, "$h8"), (10, "$h10"),
        (11, "$h8"), (-1, "$h8"), ("8", "$h8"),
    ])
    def test_homing_modes(self, harobot, sleeps, mode, command):
        robot, t = harobot
        robot.homing(mode)
        assert t.sent[-1] == command

    def test_get_status_parse_ok(self, harobot):
        robot, t = harobot
        t.auto_replies["?"] = HAROBOT_STATUS
        data = robot.getStatus()
        assert data != "error" and data != "parse error"
        assert data["state"] == "Idle"
        assert data["coordinate_X"] == "100.0"
        assert data["coordinate_RZ"] == "3.0"
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

    @pytest.mark.parametrize("tail", [
        "|Ov:100,100,100", "|Ov:50,100,100", "|WCO:0,0,0", "|Ov:1,2,3|WCO:0,0,0",
    ])
    def test_parse_ignores_any_tail(self, harobot, tail):
        robot, _ = harobot
        data = robot._parse_status_response(HAROBOT_STATUS[:-1] + tail + ">")
        assert data["state"] == "Idle"
        assert data["angle_D"] == "70.0"

    def test_parse_rejects_text_that_is_not_a_tail(self, harobot):
        robot, _ = harobot
        line = HAROBOT_STATUS[:-1] + "Ov:100>"
        assert robot._parse_status_response(line) == "parse error"

    def test_parse_accepts_signed_numbers(self, harobot):
        robot, _ = harobot
        line = HAROBOT_STATUS.replace("100.0,20.0", "+100.0,-20.0")
        data = robot._parse_status_response(line)
        assert data["coordinate_X"] == "+100.0"
        assert data["coordinate_Y"] == "-20.0"

    @pytest.mark.parametrize("junk", ["1.2.3", "-", ".", "5.", ".5", "1-2"])
    def test_parse_rejects_malformed_numbers(self, harobot, junk):
        robot, _ = harobot
        line = HAROBOT_STATUS.replace("100.0", junk)
        assert robot._parse_status_response(line) == "parse error"

    def test_failed_parse_keeps_previous_state(self, harobot):
        robot, _ = harobot
        robot._parse_status_response(HAROBOT_STATUS)
        robot._parse_status_response("<Idle,bad>")
        assert robot.mirobot_state_all["coordinate_X"] == "100.0"

    def test_get_status_empty_line(self, harobot):
        robot, t = harobot
        t.auto_replies["?"] = ""
        assert robot.getStatus() == -1

    def test_get_state_does_not_report_an_old_state(self, harobot):
        robot, t = harobot
        t.auto_replies["?"] = [HAROBOT_STATUS, "garbage"]
        assert robot.getState() == "Idle"
        assert robot.getState() == "-1"

    def test_wait_idle_event_reads_harobot_status(self, harobot):
        robot, t = harobot
        robot.setWaitMode("event")
        t.push_line("ok")
        t.push_line(HAROBOT_STATUS.replace("<Idle", "<Run"))
        t.push_line(HAROBOT_STATUS)
        assert robot.waitIdle(timeout=1) is True
        assert robot.mirobot_state_all["angle_D"] == "70.0"
        assert t.timeout == 1.0  # the read timeout is put back

    def test_wait_idle_event_times_out_without_idle(self, harobot):
        robot, t = harobot
        robot.setWaitMode("event")
        t.push_line(HAROBOT_STATUS.replace("<Idle", "<Run"))
        assert robot.waitIdle(timeout=1) is False


class TestMiromaxProtocol:
    def test_version_prefix_and_constants(self):
        assert Miromax_UART._VERSION_PREFIX == "Miromax"
        assert issubclass(Miromax_UART, Harobot_UART)

    def test_message_flag_init(self):
        robot = Miromax_UART(message_flag=False)
        assert robot.address is None

    def test_inherits_motion_format(self, miromax):
        robot, t = miromax
        robot.writeCoordinate(0, 0, x=100)
        assert t.sent[-1] == "G07G90X100"
        robot.writeAngle(0, axle1=15)
        assert t.sent[-1] == "G09G90X15"
        robot.zero()
        assert t.sent[-1] == "G9 G90 X0 Y0 Z0 A0 B0 C0"

    def test_override_feed_rate(self):
        class CustomMiromax(Miromax_UART):
            _FEED_RATE = 2000

        t = RecordingTransport()
        robot = CustomMiromax()
        robot.init(t, -1)
        robot.writeCoordinate(0, 0, x=1)
        assert "F2000" in t.last_text

    # -- homing ------------------------------------------------------------

    @pytest.mark.parametrize("mode, command", [
        (8, "$h"), (0, "$h0"), (7, "$h7"), (10, "$h10"), (11, "$h8"),
    ])
    def test_homing_modes(self, miromax, sleeps, mode, command):
        robot, t = miromax
        robot.homing(mode)
        assert t.sent == [command]  # and no restart before it

    # -- status ------------------------------------------------------------

    def test_get_status_pipe_format(self, miromax):
        robot, t = miromax
        t.auto_replies["?"] = MIROMAX_STATUS
        data = robot.getStatus()
        assert data["state"] == "Idle"
        assert data["coordinate_X"] == "100.0"
        assert data["coordinate_RZ"] == "3.0"
        assert data["angle_X"] == "10.0"
        assert data["angle_A"] == "40.0"
        assert data["angle_D"] == "70.0"
        assert data["pump"] == -1

    def test_get_status_comma_format(self, miromax):
        robot, t = miromax
        t.auto_replies["?"] = HAROBOT_STATUS
        data = robot.getStatus()
        assert data["state"] == "Idle"
        assert data["coordinate_Y"] == "20.0"

    @pytest.mark.parametrize("state", ["Hold:0", "Hold:1", "Run", "Alarm"])
    def test_parse_state_with_substate(self, miromax, state):
        robot, _ = miromax
        data = robot._parse_status_response(miromax_status(state))
        assert data["state"] == state

    def test_parse_pipe_trailing_comma_and_tail(self, miromax):
        robot, _ = miromax
        line = (
            "<Run|Cartesian:1.0,2.0,3.0,4.0,5.0,6.0,|"
            "Angle:-1.5,+2.5,3,4,5,6|Ov:100,100,100>"
        )
        data = robot._parse_status_response(line)
        assert data["state"] == "Run"
        assert data["coordinate_RZ"] == "6.0"
        assert data["angle_X"] == "-1.5"
        assert data["angle_Y"] == "+2.5"
        assert data["angle_C"] == "6"
        assert data["angle_D"] == -1  # six angles sent: the 7th stays unset

    def test_parse_pipe_drops_spare_cartesian(self, miromax):
        robot, _ = miromax
        line = MIROMAX_STATUS.replace("3.0|", "3.0,9.9|")
        data = robot._parse_status_response(line)
        assert "9.9" not in data.values()
        assert data["angle_X"] == "10.0"

    @pytest.mark.parametrize("line", [
        "<Idle|Cartesian:1,2,3,4,5|Angle:1,2,3,4,5,6>",   # five Cartesian
        "<Idle|Cartesian:1,2,3,4,5,6|Angle:1,2,3,4,5>",   # five angles
        "<Idle|Cartesian:1,2,3,4,5,6>",                   # no angles
        "<Idle|Angle:1,2,3,4,5,6|Cartesian:1,2,3,4,5,6>",  # wrong order
        "<Hold:x|Cartesian:1,2,3,4,5,6|Angle:1,2,3,4,5,6>",
    ])
    def test_parse_pipe_errors(self, miromax, line):
        robot, _ = miromax
        assert robot._parse_status_response(line) == "parse error"

    def test_wait_idle_poll_reads_pipe_status(self, miromax, sleeps):
        robot, t = miromax
        t.auto_replies["?"] = [miromax_status("Run"), MIROMAX_STATUS]
        assert robot.waitIdle(timeout=5) is True

    def test_wait_idle_poll_does_not_count_an_old_idle(self, miromax, sleeps):
        robot, t = miromax
        t.auto_replies["?"] = [MIROMAX_STATUS, "garbage"]
        assert robot.getState() == "Idle"
        assert robot.waitIdle(timeout=0.05) is False

    @pytest.mark.parametrize("idle", [MIROMAX_STATUS, HAROBOT_STATUS])
    def test_wait_idle_event_reads_either_format(self, miromax, idle):
        robot, t = miromax
        robot.setWaitMode("event")
        t.push_line(miromax_status("Hold:0"))
        t.push_line(miromax_status("Run"))
        t.push_line(idle)
        assert robot.waitIdle(timeout=1) is True

    def test_wait_idle_event_times_out_without_idle(self, miromax):
        robot, t = miromax
        robot.setWaitMode("event")
        t.push_line(miromax_status("Run"))
        assert robot.waitIdle(timeout=1) is False

    # -- end effectors -----------------------------------------------------

    @pytest.mark.parametrize("kwargs, command", [
        (dict(num=1), "M67 E20 Q87.5"),
        (dict(num=2), "M67 E20 Q97.5"),
        (dict(num=0), "M67 E20 Q92.5"),
        (dict(num=9), "M67 E20 Q92.5"),
        (dict(num=1, speed=1), "M67 E20 Q91.5"),
        (dict(num=2, speed=1), "M67 E20 Q93.5"),
        (dict(num=1, speed=0), "M67 E20 Q91.5"),    # clamped up to 1
        (dict(num=2, speed=99), "M67 E20 Q97.5"),   # clamped down to 5
        (dict(num=1, pin=23), "M67 E23 Q87.5"),
        (dict(num=1, pin=10), "M67 E20 Q87.5"),     # not a gripper channel
    ])
    def test_gripper(self, miromax, kwargs, command):
        robot, t = miromax
        robot.gripper(**kwargs)
        assert t.sent == [command]

    def test_pump_is_not_available(self, miromax):
        robot, t = miromax
        with pytest.raises(NotImplementedError, match="pumpSuction"):
            robot.pump(1)
        assert t.sent == []

    @pytest.mark.parametrize("method, args, command", [
        ("pumpSuction", (1,), "M67 E10 Q100"),
        ("pumpSuction", (0,), "M67 E10 Q0"),
        ("pumpSuction", (2,), "M67 E10 Q0"),
        ("pumpSuction", (1, 11), "M67 E11 Q100"),
        ("pumpSuction", (1, 3), "M67 E10 Q100"),    # unknown channel
        ("pumpGripper", (1,), "M67 E10 Q75"),
        ("pumpGripper", (2,), "M67 E10 Q25"),
        ("pumpGripper", (0,), "M67 E10 Q0"),
        ("pumpGripper", (1, 11), "M67 E11 Q75"),
        ("pumpSoftGripper", (1,), "M67 E10 Q75"),
        ("pumpSoftGripper", (2, 11), "M67 E11 Q25"),
        ("pumpSoftGripper", (), "M67 E10 Q0"),
        ("pwmWrite", (42,), "M67 E10 Q42"),
        ("pwmWrite", (42, 24), "M67 E24 Q42"),
        ("pwmWrite", (42, 0), "M67 E10 Q42"),       # unknown channel
    ])
    def test_pneumatic_and_pwm(self, miromax, method, args, command):
        robot, t = miromax
        getattr(robot, method)(*args)
        assert t.sent == [command]

    # -- cancel ------------------------------------------------------------

    def test_cancellation_pauses_waits_for_hold_then_stops(self, miromax, sleeps):
        robot, t = miromax
        t.auto_replies["?"] = [
            miromax_status("Run"),
            miromax_status("Hold:1"),
            miromax_status("Hold:0"),   # pause settled -> % is sent
            miromax_status("Hold:0"),
            MIROMAX_STATUS,
        ]
        assert robot.cancellation() is True
        assert t.sent[0] == "!"
        stop = t.sent.index("%")
        assert t.sent[1:stop] == ["?", "?", "?"]
        assert set(t.sent[stop + 1:]) == {"?"}
        assert "o117" not in t.sent

    def test_cancellation_when_already_idle(self, miromax, sleeps):
        robot, t = miromax
        t.auto_replies["?"] = MIROMAX_STATUS
        assert robot.cancellation() is True
        assert t.sent[:3] == ["!", "?", "%"]

    def test_cancellation_never_settles_sends_no_stop(self, miromax, sleeps):
        robot, t = miromax
        t.auto_replies["?"] = miromax_status("Hold:1")
        assert robot.cancellation(timeout=0.05) is False
        assert "%" not in t.sent

    def test_cancellation_ignores_unreadable_status(self, miromax, sleeps):
        robot, t = miromax
        robot._parse_status_response(MIROMAX_STATUS)  # last known state: Idle
        t.auto_replies["?"] = "garbage"
        assert robot.cancellation(timeout=0.05) is False
        assert "%" not in t.sent

    def test_cancellation_times_out_waiting_for_idle(self, miromax, sleeps):
        robot, t = miromax
        t.auto_replies["?"] = miromax_status("Hold:0")
        assert robot.cancellation(timeout=0.05) is False
        assert "%" in t.sent
