"""
Tests for the MT4_UART class.

This module tests all functionality of the MT4 robot arm control class
(4-axis robot) using the simulated hardware.
"""

import pytest
import time

pytestmark = pytest.mark.mt4


class TestMT4Initialization:
    """Tests for MT4 initialization."""
    
    def test_mt4_init(self, mt4):
        """Test that MT4 can be initialized."""
        assert mt4 is not None
        assert mt4.pSerial is not None
        assert mt4.address == -1
    
    def test_mt4_inherits_from_mirobot(self, mt4):
        """Test that MT4 inherits from Mirobot_UART."""
        assert hasattr(mt4, 'mirobot_state_all')
        assert hasattr(mt4, 'sendMsg')
        assert hasattr(mt4, 'read_message')


class TestMT4Homing:
    """Tests for MT4 homing functionality."""
    
    def test_homing_default(self, mt4_with_sim):
        """Test default homing command."""
        robot, sim = mt4_with_sim
        robot.homing()
        time.sleep(0.7)
        
        assert sim.state.angle_X == 0.0
        assert sim.state.angle_Y == 0.0
        assert sim.state.angle_Z == 0.0
        assert sim.state.angle_A == 0.0
    
    @pytest.mark.parametrize("mode", [0, 1, 2, 3, 4, 7, 8, 9, 10])
    def test_homing_modes(self, mt4_with_sim, mode):
        """Test MT4 homing modes."""
        robot, sim = mt4_with_sim
        robot.homing(mode)
        time.sleep(0.2)
    
    def test_homing_fallback(self, mt4_with_sim):
        """Test MT4 homing fallback ($h command)."""
        robot, sim = mt4_with_sim
        robot.homing(99)  # Invalid mode triggers $h
        time.sleep(0.7)
        
        assert sim.state.angle_X == 0.0

    @pytest.mark.parametrize("mode", [3.5, 8.0, -1, "8", None])
    def test_homing_invalid_mode_falls_back(self, mt4_with_sim, mode):
        """Test that non-int or out-of-range modes fall back to $h."""
        robot, sim = mt4_with_sim
        robot.homing(mode)
        time.sleep(0.2)
        # Should not raise; falls back to $h


class TestMT4Movement:
    """Tests for MT4 movement commands."""
    
    def test_writeangle(self, mt4_with_sim):
        """Test MT4 angle-based movement (4 axes)."""
        robot, sim = mt4_with_sim
        
        robot.writeangle(0, 20.0, 30.0, 40.0, 50.0)
        time.sleep(0.3)
        
        assert sim.state.angle_X == 20.0
        assert sim.state.angle_Y == 30.0
        assert sim.state.angle_Z == 40.0
        assert sim.state.angle_A == 50.0
    
    def test_writecoordinate(self, mt4_with_sim):
        """Test MT4 Cartesian movement."""
        robot, sim = mt4_with_sim
        
        robot.writecoordinate(0, 0, 175.0, 75.0, 155.0, 35.0)
        time.sleep(0.3)
        
        assert sim.state.coordinate_X == 175.0
        assert sim.state.coordinate_Y == 75.0
        assert sim.state.coordinate_Z == 155.0
        assert sim.state.coordinate_RX == 35.0
    
    def test_zero(self, mt4_with_sim):
        """Test MT4 returning to zero position."""
        robot, sim = mt4_with_sim
        
        robot.writeangle(0, 25.0, 15.0, 5.0, 3.0)
        time.sleep(0.3)
        
        robot.zero()
        time.sleep(0.3)
        
        assert sim.state.angle_X == 0.0
        assert sim.state.angle_Y == 0.0


class TestMT4Status:
    """Tests for MT4 status queries."""
    
    def test_get_angle(self, mt4_with_sim):
        """Test MT4 angle retrieval."""
        robot, sim = mt4_with_sim
        
        sim.set_state(
            angle_X=12.0,
            angle_Y=22.0,
            angle_Z=32.0,
            angle_A=42.0
        )
        
        assert float(robot.getAngle(1)) == 12.0
        assert float(robot.getAngle(2)) == 22.0
        assert float(robot.getAngle(3)) == 32.0
        assert float(robot.getAngle(4)) == 42.0
    
    def test_get_coordinate(self, mt4_with_sim):
        """Test MT4 coordinate retrieval."""
        robot, sim = mt4_with_sim
        
        sim.set_state(
            coordinate_X=185.0,
            coordinate_Y=65.0,
            coordinate_Z=160.0,
            coordinate_RX=35.0
        )
        
        assert float(robot.getcoordinate(1)) == 185.0
        assert float(robot.getcoordinate(2)) == 65.0
        assert float(robot.getcoordinate(3)) == 160.0
        assert float(robot.getcoordinate(4)) == 35.0
    
    def test_version_with_exbox(self, mt4_with_sim):
        """Test MT4 version query when both EXbox and robot respond.

        Note: MT4 hardware uses 'E4' as the firmware prefix, same as E4.
        """
        robot, sim = mt4_with_sim
        
        sim.set_firmware_version("E4 V1.2.0", "EXbox V1.2.0")
        
        version = robot.version()
        
        assert isinstance(version, tuple)
        assert "EXbox" in version[0]
        assert "E4" in version[1]

    def test_version_robot_only(self, mt4_with_sim):
        """Test MT4 version query when only the robot responds (no EXbox)."""
        robot, sim = mt4_with_sim

        sim.set_firmware_version("E4 V1.2.0", "")

        version = robot.version()

        assert isinstance(version, tuple)
        assert version[0] == ""
        assert "E4" in version[1]


class TestMT4InheritedFunctions:
    """Tests for functions inherited from Mirobot_UART."""
    
    def test_speed(self, mt4_with_sim):
        """Test MT4 speed control."""
        robot, sim = mt4_with_sim
        
        result = robot.speed(60)
        time.sleep(0.2)
        
        assert result == 1
        assert sim.state.speed == 60
    
    def test_pwm_write(self, mt4_with_sim):
        """Test MT4 PWM control."""
        robot, sim = mt4_with_sim
        
        result = robot.pwmWrite(400)
        time.sleep(0.2)
        
        assert result == 1
        assert sim.state.pump_pwm == 400
    
    def test_gripper(self, mt4_with_sim):
        """Test MT4 gripper control."""
        robot, sim = mt4_with_sim
        
        result = robot.gripper(2)
        time.sleep(0.2)
        
        assert result == 1
        assert sim.state.pump_pwm == 60
    
    def test_pump(self, mt4_with_sim):
        """Test MT4 pump control."""
        robot, sim = mt4_with_sim
        
        result = robot.pump(2)
        time.sleep(0.2)
        
        assert result == 1
        assert sim.state.pump_pwm == 500
    
    def test_restart(self, mt4_with_sim):
        """Test MT4 restart command."""
        robot, sim = mt4_with_sim
        
        result = robot.restart()
        time.sleep(0.2)
        
        assert result == 1
    
    def test_get_status(self, mt4_with_sim):
        """Test MT4 status query."""
        robot, sim = mt4_with_sim
        
        sim.set_state(state="Idle", angle_X=10.0)
        
        status = robot.getStatus()
        
        assert isinstance(status, dict)
        assert status["state"] == "Idle"
