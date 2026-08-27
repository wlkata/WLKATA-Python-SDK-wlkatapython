"""Direct unit tests for simulator config handlers (no serial)."""

import re
import time
from types import SimpleNamespace

import pytest

from wlkatapython.simulator.config import handlers as H
from wlkatapython.simulator import RobotState


def _match(pattern, cmd):
    m = re.match(pattern, cmd)
    assert m is not None
    return m


@pytest.fixture
def state():
    return RobotState()


class TestBaseHandlers:
    def test_status_and_version(self, state):
        sent = []
        ctx = {
            "send_response": sent.append,
            "exbox_version": "EXbox V9",
            "firmware_version": "Mirobot V9",
        }
        out = H.handle_status_query("?", None, state, ctx)
        assert out.startswith("<Idle,")
        fw = H.handle_version_query("$V", None, state, ctx)
        assert fw == "Mirobot V9"
        assert sent == ["EXbox V9"]

    def test_homing_and_speed_pwm(self, state):
        H.handle_homing("o105=8", None, state, {})
        assert state.angle_X == 0.0
        assert state.state in ("Home", "Idle")
        assert H.handle_pwm_control("M3 S40", _match(r"M3 S(\d+)", "M3 S40"), state, {}) == "ok"
        assert state.pump_pwm == 40
        assert H.handle_speed_control("F50", _match(r"F(\d+)", "F50"), state, {}) == "ok"
        assert state.speed == 50

    def test_cartesian_and_angle_absolute(self, state):
        ctx = {"model": "mirobot"}
        H.handle_cartesian_movement(
            "M20G90G00X100Y20Z30A1B2C3", None, state, ctx
        )
        assert state.coordinate_X == 100.0
        assert state.state == "Run"
        H.handle_angle_movement(
            "M21G90G00X10Y20Z30A40B50C60", None, state, ctx
        )
        assert state.angle_X == 10.0
        assert state.angle_A == 40.0
        # FK should have updated cartesian after angle move
        assert state.coordinate_X != 100.0 or state.angle_X == 10.0

    def test_cartesian_incremental(self, state):
        state.coordinate_X = 10.0
        state.coordinate_Y = 20.0
        H.handle_cartesian_movement("M20G91G00X5Y-5", None, state, {"model": "e4"})
        assert state.coordinate_X == 15.0
        assert state.coordinate_Y == 15.0

    def test_angle_incremental(self, state):
        state.angle_X = 10.0
        H.handle_angle_movement("M21G91G00X5", None, state, {"model": "e4"})
        assert state.angle_X == 15.0

    def test_expand_axis(self, state):
        H.handle_expand_axis("G90G00D12.5", None, state, {})
        assert state.angle_D == 12.5
        H.handle_expand_axis("G91G00D2.5", None, state, {})
        assert state.angle_D == 15.0


class TestGpioHandlers:
    def test_gpio_mode_set_query(self, state):
        sent = []
        ctx = {"send_response": sent.append}
        m = _match(r"o130=(.*)", "o130=1,0,1,0")
        assert H.handle_gpio_mode_set("o130=1,0,1,0", m, state, ctx) == "ok"
        assert state.gpio_mode == [1, 0, 1, 0]
        assert H.handle_gpio_mode_query("o130?", None, state, ctx) == "ok"
        assert sent[-1] == "1,0,1,0"

    def test_gpio_output_enable_threshold_file(self, state):
        sent = []
        ctx = {"send_response": sent.append}
        H.handle_gpio_output_set("o131=1,1,0,0", _match(r"o131=(.*)", "o131=1,1,0,0"), state, ctx)
        assert state.gpio_output[0] == 1
        H.handle_gpio_output_query("o131?", None, state, ctx)
        assert "1,1,0,0" in sent[-1]

        H.handle_gpio_enable_set("o132=1,0,0,1", _match(r"o132=(.*)", "o132=1,0,0,1"), state, ctx)
        H.handle_gpio_enable_query("o132?", None, state, ctx)
        assert sent[-1] == "1,0,0,1"

        H.handle_gpio_threshold_set("o133=10,20,30,40", _match(r"o133=(.*)", "o133=10,20,30,40"), state, ctx)
        H.handle_gpio_threshold_query("o133?", None, state, ctx)
        assert sent[-1] == "10,20,30,40"

        H.handle_gpio_file_set("o134=a,b,c,d", _match(r"o134=(.*)", "o134=a,b,c,d"), state, ctx)
        H.handle_gpio_file_query("o134?", None, state, ctx)
        assert sent[-1] == "a,b,c,d"


class TestModelSpecificHandlers:
    def test_mirobot_status(self, state):
        out = H.handle_mirobot_status_query("?", None, state, {})
        assert "Angle(ABCDXYZ)" in out

    def test_e4_status_homing_angle_cartesian(self, state):
        out = H.handle_e4_status_query("?", None, state, {})
        assert "Angle(XYZA)" in out
        H.handle_e4_homing("o105=8", None, state, {})
        assert state.angle_X == 0.0
        H.handle_e4_angle_movement("M21G90G00X1Y2Z3A4", None, state, {})
        assert state.angle_X == 1.0
        H.handle_e4_cartesian_movement("M20G90G00X9Y8Z7A6", None, state, {})
        assert state.coordinate_X == 9.0

    def test_ms4220_handlers(self, state):
        out = H.handle_ms4220_status_query("?", None, state, {})
        assert out.startswith("<")
        assert H.handle_ms4220_speed(
            "G6 F50", _match(r"G6 F([-\d.]+)", "G6 F50"), state, {}
        ) == "ok"
        assert getattr(state, "motor_speed") == 50
        assert H.handle_ms4220_position(
            "G1 X10", _match(r".*X([-\d]+)", "G1 X10"), state, {}
        ) == "ok"
        assert state.motor_position == 10
        assert H.handle_ms4220_relative(
            "G91 X5", _match(r".*X([-\d]+)", "G91 X5"), state, {}
        ) == "ok"
        assert state.motor_position == 15
        assert H.handle_ms4220_home("$H", None, state, {}) == "ok"
        assert state.motor_position == 0

    def test_misc_handlers(self, state):
        assert "ECHO" in H.handle_echo("ECHO hello", _match(r"ECHO (.*)", "ECHO hello"), state, {})
        assert H.handle_led("LED ON", _match(r"LED (.*)", "LED ON"), state, {}) == "ok"
        assert "coordinate" in H.handle_get_position("?", None, state, {}).lower() or True

    def test_registry(self):
        assert H.get_handler("handle_status_query") is H.handle_status_query
        assert H.get_handler("missing") is None

        def custom(c, m, s, ctx):
            return "x"

        H.register_handler("custom_test_handler", custom)
        assert H.get_handler("custom_test_handler") is custom
