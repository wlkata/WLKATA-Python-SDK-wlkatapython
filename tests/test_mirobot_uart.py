"""
Tests for the Mirobot_UART class.

This module tests all functionality of the Mirobot robot arm control class
using the simulated hardware.
"""

import pytest
import time

pytestmark = pytest.mark.mirobot


class TestMirobotInitialization:
    """Tests for Mirobot initialization and connection."""
    
    def test_mirobot_init(self, mirobot):
        """Test that Mirobot can be initialized."""
        assert mirobot is not None
        assert mirobot.pSerial is not None
        assert mirobot.address == -1
    
    def test_mirobot_initial_state(self, mirobot):
        """Test that Mirobot has correct initial state dictionary."""
        assert "state" in mirobot.mirobot_state_all
        assert "angle_A" in mirobot.mirobot_state_all
        assert "coordinate_X" in mirobot.mirobot_state_all
        assert "pump" in mirobot.mirobot_state_all
    
    def test_message_print_flag(self, mirobot):
        """Test the message print flag setting."""
        mirobot.message_print(True)
        # No assertion needed - just verify it doesn't raise
        mirobot.message_print(False)


class TestMirobotHoming:
    """Tests for homing functionality."""
    
    def test_homing_default(self, mirobot_with_sim, wait_for_idle):
        """Test default homing command (mode 8)."""
        robot, sim = mirobot_with_sim
        robot.homing()
        time.sleep(0.7)
        
        # Check that angles are reset to zero
        assert sim.state.angle_X == 0.0
        assert sim.state.angle_Y == 0.0
        assert sim.state.angle_Z == 0.0
    
    @pytest.mark.parametrize("mode", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    def test_homing_modes(self, mirobot_with_sim, mode):
        """Test all homing modes."""
        robot, sim = mirobot_with_sim
        robot.homing(mode)
        time.sleep(0.2)
        # Command should be accepted


class TestMirobotMovement:
    """Tests for movement commands."""
    
    def test_writeangle(self, mirobot_with_sim, wait_for_idle):
        """Test angle-based movement."""
        robot, sim = mirobot_with_sim
        
        robot.writeangle(0, 45.0, 30.0, 15.0, 10.0, 5.0, 0.0)
        time.sleep(0.3)
        
        assert sim.state.angle_X == 45.0
        assert sim.state.angle_Y == 30.0
        assert sim.state.angle_Z == 15.0
        assert sim.state.angle_A == 10.0
        assert sim.state.angle_B == 5.0
        assert sim.state.angle_C == 0.0
    
    def test_writeangle_incremental(self, mirobot_with_sim):
        """Test incremental angle movement."""
        robot, sim = mirobot_with_sim
        
        # First move to a known position (absolute: position=0)
        robot.writeangle(0, 10.0, 10.0, 10.0, 0.0, 0.0, 0.0)
        time.sleep(0.3)
        
        assert sim.state.angle_X == 10.0
        assert sim.state.angle_Y == 10.0
        assert sim.state.angle_Z == 10.0
        
        # Then move incrementally (position=1 means G91)
        robot.writeangle(1, 5.0, 5.0, 5.0, 0.0, 0.0, 0.0)
        time.sleep(0.3)
        
        # Should add to current position
        assert sim.state.angle_X == 15.0
        assert sim.state.angle_Y == 15.0
        assert sim.state.angle_Z == 15.0
    
    def test_writeangle_incremental_negative(self, mirobot_with_sim):
        """Test incremental angle movement with negative values."""
        robot, sim = mirobot_with_sim
        
        # First move to a known position
        robot.writeangle(0, 30.0, 30.0, 30.0, 0.0, 0.0, 0.0)
        time.sleep(0.3)
        
        # Move incrementally with negative values
        robot.writeangle(1, -10.0, -10.0, -10.0, 0.0, 0.0, 0.0)
        time.sleep(0.3)
        
        assert sim.state.angle_X == 20.0
        assert sim.state.angle_Y == 20.0
        assert sim.state.angle_Z == 20.0
    
    def test_writecoordinate_fast(self, mirobot_with_sim, wait_for_idle):
        """Test fast Cartesian movement (G00)."""
        robot, sim = mirobot_with_sim
        
        robot.writecoordinate(0, 0, 200.0, 100.0, 150.0, 0.0, 0.0, 0.0)
        time.sleep(0.3)
        
        assert sim.state.coordinate_X == 200.0
        assert sim.state.coordinate_Y == 100.0
        assert sim.state.coordinate_Z == 150.0
    
    def test_writecoordinate_linear(self, mirobot_with_sim, wait_for_idle):
        """Test linear Cartesian movement (G01)."""
        robot, sim = mirobot_with_sim
        
        robot.writecoordinate(1, 0, 180.0, 50.0, 180.0, 45.0, 0.0, 0.0)
        time.sleep(0.3)
        
        assert sim.state.coordinate_X == 180.0
        assert sim.state.coordinate_Y == 50.0
        assert sim.state.coordinate_Z == 180.0
    
    def test_writecoordinate_gate(self, mirobot_with_sim):
        """Test gate-type movement (G05)."""
        robot, sim = mirobot_with_sim
        
        robot.writecoordinate(2, 0, 160.0, 60.0, 170.0, 30.0, 15.0, 0.0)
        time.sleep(0.3)
        
        assert sim.state.coordinate_X == 160.0
    
    def test_zero(self, mirobot_with_sim):
        """Test returning to zero position."""
        robot, sim = mirobot_with_sim
        
        # First move away from zero
        robot.writeangle(0, 45.0, 30.0, 15.0, 0.0, 0.0, 0.0)
        time.sleep(0.3)
        
        # Return to zero
        robot.zero()
        time.sleep(0.3)
        
        # Check angles returned to zero
        assert sim.state.angle_X == 0.0
        assert sim.state.angle_Y == 0.0
        assert sim.state.angle_Z == 0.0
    
    def test_writecoordinate_incremental(self, mirobot_with_sim):
        """Test incremental Cartesian movement."""
        robot, sim = mirobot_with_sim
        
        # First move to a known position (absolute: position=0)
        robot.writecoordinate(0, 0, 100.0, 50.0, 150.0, 0.0, 0.0, 0.0)
        time.sleep(0.3)
        
        assert sim.state.coordinate_X == 100.0
        assert sim.state.coordinate_Y == 50.0
        assert sim.state.coordinate_Z == 150.0
        
        # Then move incrementally (position=1 means G91)
        robot.writecoordinate(0, 1, 10.0, 10.0, 10.0, 0.0, 0.0, 0.0)
        time.sleep(0.3)
        
        # Should add to current position
        assert sim.state.coordinate_X == 110.0
        assert sim.state.coordinate_Y == 60.0
        assert sim.state.coordinate_Z == 160.0
    
    def test_writeexpand(self, mirobot_with_sim):
        """Test 7th axis (expand) movement."""
        robot, sim = mirobot_with_sim
        
        robot.writeexpand(0, 0, 50.0)
        time.sleep(0.2)
        
        assert sim.state.angle_D == 50.0
    
    def test_writeexpand_incremental(self, mirobot_with_sim):
        """Test 7th axis (expand) incremental movement."""
        robot, sim = mirobot_with_sim
        
        # First move to absolute position
        robot.writeexpand(0, 0, 30.0)
        time.sleep(0.2)
        
        assert sim.state.angle_D == 30.0
        
        # Then move incrementally (position=1 means G91)
        robot.writeexpand(0, 1, 20.0)
        time.sleep(0.2)
        
        # Should add to current position
        assert sim.state.angle_D == 50.0


class TestMirobotEndEffector:
    """Tests for end effector control (gripper, pump, PWM)."""
    
    def test_gripper_close(self, mirobot_with_sim):
        """Test gripper close command."""
        robot, sim = mirobot_with_sim
        
        result = robot.gripper(0)
        time.sleep(0.2)
        
        assert result == 1
        assert sim.state.pump_pwm == 0
    
    def test_gripper_open_partial(self, mirobot_with_sim):
        """Test gripper partial open command."""
        robot, sim = mirobot_with_sim
        
        result = robot.gripper(1)
        time.sleep(0.2)
        
        assert result == 1
        assert sim.state.pump_pwm == 40
    
    def test_gripper_open_full(self, mirobot_with_sim):
        """Test gripper full open command."""
        robot, sim = mirobot_with_sim
        
        result = robot.gripper(2)
        time.sleep(0.2)
        
        assert result == 1
        assert sim.state.pump_pwm == 60
    
    def test_pump_off(self, mirobot_with_sim):
        """Test pump off command."""
        robot, sim = mirobot_with_sim
        
        result = robot.pump(0)
        time.sleep(0.2)
        
        assert result == 1
        assert sim.state.pump_pwm == 0
    
    def test_pump_suction(self, mirobot_with_sim):
        """Test pump suction command."""
        robot, sim = mirobot_with_sim
        
        result = robot.pump(1)
        time.sleep(0.2)
        
        assert result == 1
        assert sim.state.pump_pwm == 1000
    
    def test_pump_blow(self, mirobot_with_sim):
        """Test pump blow command."""
        robot, sim = mirobot_with_sim
        
        result = robot.pump(2)
        time.sleep(0.2)
        
        assert result == 1
        assert sim.state.pump_pwm == 500
    
    def test_pwm_write(self, mirobot_with_sim):
        """Test direct PWM control."""
        robot, sim = mirobot_with_sim
        
        result = robot.pwmWrite(750)
        time.sleep(0.2)
        
        assert result == 1
        assert sim.state.pump_pwm == 750
    
    @pytest.mark.parametrize("pwm_value", [0, 100, 500, 750, 1000])
    def test_pwm_write_values(self, mirobot_with_sim, pwm_value):
        """Test PWM control with various values."""
        robot, sim = mirobot_with_sim
        
        result = robot.pwmWrite(pwm_value)
        time.sleep(0.2)
        
        assert result == 1
        assert sim.state.pump_pwm == pwm_value


class TestMirobotSpeed:
    """Tests for speed control."""
    
    def test_speed_control(self, mirobot_with_sim):
        """Test speed setting."""
        robot, sim = mirobot_with_sim
        
        result = robot.speed(80)
        time.sleep(0.2)
        
        assert result == 1
        assert sim.state.speed == 80
    
    @pytest.mark.parametrize("speed", [0, 25, 50, 75, 100])
    def test_speed_values(self, mirobot_with_sim, speed):
        """Test speed control with various values."""
        robot, sim = mirobot_with_sim
        
        result = robot.speed(speed)
        time.sleep(0.2)
        
        assert result == 1
        assert sim.state.speed == speed


class TestMirobotStatus:
    """Tests for status queries."""
    
    def test_get_status(self, mirobot_with_sim):
        """Test getting full robot status."""
        robot, sim = mirobot_with_sim
        
        # Set some known values
        sim.set_state(
            state="Idle",
            angle_X=30.0,
            angle_Y=20.0,
            coordinate_X=175.0,
            pump_pwm=100
        )
        
        status = robot.getStatus()
        
        assert isinstance(status, dict)
        assert status["state"] == "Idle"
        assert float(status["angle_X"]) == 30.0
        assert float(status["coordinate_X"]) == 175.0
        assert int(status["pump"]) == 100
    
    def test_get_state(self, mirobot_with_sim):
        """Test getting robot state."""
        robot, sim = mirobot_with_sim
        
        sim.set_state(state="Idle")
        state = robot.getState()
        
        assert state == "Idle"
    
    def test_get_angle(self, mirobot_with_sim):
        """Test getting individual axis angles."""
        robot, sim = mirobot_with_sim
        
        sim.set_state(
            angle_X=45.0,
            angle_Y=30.0,
            angle_Z=15.0,
            angle_A=10.0,
            angle_B=5.0,
            angle_C=2.0,
            angle_D=1.0
        )
        
        assert float(robot.getAngle(1)) == 45.0  # X
        assert float(robot.getAngle(2)) == 30.0  # Y
        assert float(robot.getAngle(3)) == 15.0  # Z
        assert float(robot.getAngle(4)) == 10.0  # A
        assert float(robot.getAngle(5)) == 5.0   # B
        assert float(robot.getAngle(6)) == 2.0   # C
        assert float(robot.getAngle(7)) == 1.0   # D
    
    def test_get_coordinate(self, mirobot_with_sim):
        """Test getting individual coordinates."""
        robot, sim = mirobot_with_sim
        
        sim.set_state(
            coordinate_X=200.0,
            coordinate_Y=50.0,
            coordinate_Z=180.0,
            coordinate_RX=45.0,
            coordinate_RY=30.0,
            coordinate_RZ=15.0
        )
        
        assert float(robot.getcoordinate(1)) == 200.0  # X
        assert float(robot.getcoordinate(2)) == 50.0   # Y
        assert float(robot.getcoordinate(3)) == 180.0  # Z
        assert float(robot.getcoordinate(4)) == 45.0   # RX
        assert float(robot.getcoordinate(5)) == 30.0   # RY
        assert float(robot.getcoordinate(6)) == 15.0   # RZ
    
    def test_get_pump(self, mirobot_with_sim):
        """Test getting pump PWM value."""
        robot, sim = mirobot_with_sim
        
        sim.set_state(pump_pwm=500)
        pump_value = robot.getpump()
        
        assert int(pump_value) == 500
    
    def test_get_mooe(self, mirobot_with_sim):
        """Test getting motion mode."""
        robot, sim = mirobot_with_sim
        
        sim.set_state(motion_mode=1)
        mooe = robot.getmooe()
        
        assert int(mooe) == 1


class TestMirobotGPIO:
    """Tests for GPIO functionality."""
    
    def test_gpio_init(self, mirobot_with_sim):
        """Test GPIO initialization."""
        robot, sim = mirobot_with_sim
        
        result = robot.gpio_init()
        time.sleep(0.2)
        
        assert result == 1
        assert all(e == 0 for e in sim.state.gpio_enable)
    
    def test_gpio_mode_write(self, mirobot_with_sim):
        """Test GPIO mode setting."""
        robot, sim = mirobot_with_sim
        
        result = robot.gpio_mode_write("A0", 1)
        time.sleep(0.2)
        
        assert result == 1
        assert sim.state.gpio_mode[0] == 1
    
    def test_gpio_mode_read(self, mirobot_with_sim):
        """Test GPIO mode reading."""
        robot, sim = mirobot_with_sim
        
        sim.state.gpio_mode = [1, 2, 3, 4]
        
        mode = robot.gpio_mode_read("A0")
        assert mode == "1"
        
        mode = robot.gpio_mode_read("A1")
        assert mode == "2"
        
        mode = robot.gpio_mode_read("D0")
        assert mode == "3"
        
        mode = robot.gpio_mode_read("D1")
        assert mode == "4"
    
    def test_gpio_output_write(self, mirobot_with_sim):
        """Test GPIO output setting."""
        robot, sim = mirobot_with_sim
        
        result = robot.gpio_output_write("D0", 1)
        time.sleep(0.2)
        
        assert result == 1
        assert sim.state.gpio_output[2] == 1
    
    def test_gpio_input_read(self, mirobot_with_sim):
        """Test GPIO input reading."""
        robot, sim = mirobot_with_sim
        
        sim.state.gpio_output = [100, 200, 300, 400]
        
        value = robot.gpio_input_read("A0")
        assert value == "100"
    
    def test_gpio_enable_write(self, mirobot_with_sim):
        """Test GPIO enable setting."""
        robot, sim = mirobot_with_sim
        
        result = robot.gpio_enable_write("A1", 1)
        time.sleep(0.2)
        
        assert result == 1
        assert sim.state.gpio_enable[1] == 1
    
    def test_gpio_enable_read(self, mirobot_with_sim):
        """Test GPIO enable reading."""
        robot, sim = mirobot_with_sim
        
        sim.state.gpio_enable = [1, 0, 1, 0]
        
        value = robot.gpio_enable_read("A0")
        assert value == "1"
        
        value = robot.gpio_enable_read("A1")
        assert value == "0"
    
    def test_gpio_threshold_write(self, mirobot_with_sim):
        """Test GPIO threshold setting."""
        robot, sim = mirobot_with_sim
        
        result = robot.gpio_threshold_write("D1", 512)
        time.sleep(0.2)
        
        assert result == 1
        assert sim.state.gpio_threshold[3] == 512
    
    def test_gpio_threshold_read(self, mirobot_with_sim):
        """Test GPIO threshold reading."""
        robot, sim = mirobot_with_sim
        
        sim.state.gpio_threshold = [100, 200, 300, 400]
        
        value = robot.gpio_threshold_read("D0")
        assert value == "300"


class TestMirobotSystem:
    """Tests for system commands."""
    
    def test_restart(self, mirobot_with_sim):
        """Test restart command."""
        robot, sim = mirobot_with_sim
        
        result = robot.restart()
        time.sleep(0.2)
        
        assert result == 1
    
    def test_cancellation(self, mirobot_with_sim):
        """Test cancellation command."""
        robot, sim = mirobot_with_sim
        
        result = robot.cancellation()
        time.sleep(0.2)
        
        assert result == 1
    
    def test_version(self, mirobot_with_sim):
        """Test version query."""
        robot, sim = mirobot_with_sim
        
        sim.set_firmware_version("Mirobot V2.0.0", "EXbox V2.0.0")
        
        version = robot.version()
        
        # Version returns a tuple (exbox, mirobot)
        assert "EXbox" in version[0]
        assert "Mirobot" in version[1]
    
    def test_send_msg(self, mirobot_with_sim):
        """Test raw message sending."""
        robot, sim = mirobot_with_sim
        
        robot.sendMsg("o100")  # Restart command
        time.sleep(0.2)
        
        response = robot.read_message()
        assert "ok" in response


class TestMirobotRS485:
    """Tests for RS485 addressing mode."""
    
    def test_rs485_addressing(self, mirobot_rs485):
        """Test RS485 addressed commands."""
        robot, sim = mirobot_rs485
        
        robot.homing()
        time.sleep(0.7)
        
        # Command should work with correct address
        assert sim.state.angle_X == 0.0
    
    def test_rs485_sendmsg_format(self, mirobot_rs485):
        """Test that RS485 messages include address prefix."""
        robot, sim = mirobot_rs485
        sim.message_print(False)
        
        # The sendMsg method should add the @address prefix
        robot.sendMsg("o100")
        time.sleep(0.2)
        
        # Should have been processed correctly
        response = robot.read_message()
        assert "ok" in response
