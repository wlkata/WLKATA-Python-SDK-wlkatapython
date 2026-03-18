"""
Tests for the E4_UART class.

This module tests all functionality of the E4 robot arm control class
(4-axis robot) using the simulated hardware.
"""

import pytest
import time

pytestmark = pytest.mark.e4


class TestE4Initialization:
    """Tests for E4 initialization."""
    
    def test_e4_init(self, e4):
        """Test that E4 can be initialized."""
        assert e4 is not None
        assert e4.pSerial is not None
        assert e4.address == -1
    
    def test_e4_inherits_from_mirobot(self, e4):
        """Test that E4 inherits from Mirobot_UART."""
        assert hasattr(e4, 'mirobot_state_all')
        assert hasattr(e4, 'sendMsg')
        assert hasattr(e4, 'read_message')


class TestE4Homing:
    """Tests for E4 homing functionality."""
    
    def test_homing_default(self, e4_with_sim):
        """Test default homing command."""
        robot, sim = e4_with_sim
        robot.homing()
        time.sleep(0.7)
        
        assert sim.state.angle_X == 0.0
        assert sim.state.angle_Y == 0.0
        assert sim.state.angle_Z == 0.0
        assert sim.state.angle_A == 0.0
    
    @pytest.mark.parametrize("mode", [0, 1, 2, 3, 4, 7, 8, 9, 10])
    def test_homing_modes(self, e4_with_sim, mode):
        """Test E4 homing modes (note: modes 5, 6 use $h)."""
        robot, sim = e4_with_sim
        robot.homing(mode)
        time.sleep(0.2)
    
    def test_homing_fallback(self, e4_with_sim):
        """Test E4 homing fallback ($h command)."""
        robot, sim = e4_with_sim
        robot.homing(99)  # Invalid mode triggers $h
        time.sleep(0.7)
        
        assert sim.state.angle_X == 0.0


class TestE4Movement:
    """Tests for E4 movement commands."""
    
    def test_writeangle(self, e4_with_sim):
        """Test E4 angle-based movement (4 axes)."""
        robot, sim = e4_with_sim
        
        robot.writeangle(0, 25.0, 35.0, 45.0, 55.0)
        time.sleep(0.3)
        
        assert sim.state.angle_X == 25.0
        assert sim.state.angle_Y == 35.0
        assert sim.state.angle_Z == 45.0
        assert sim.state.angle_A == 55.0
    
    def test_writeangle_incremental(self, e4_with_sim):
        """Test E4 incremental angle movement."""
        robot, sim = e4_with_sim
        
        robot.writeangle(1, 10.0, 10.0, 10.0, 10.0)
        time.sleep(0.3)
        # Command should be accepted
    
    def test_writecoordinate_fast(self, e4_with_sim):
        """Test E4 fast Cartesian movement."""
        robot, sim = e4_with_sim
        
        robot.writecoordinate(0, 0, 180.0, 80.0, 160.0, 30.0)
        time.sleep(0.3)
        
        assert sim.state.coordinate_X == 180.0
        assert sim.state.coordinate_Y == 80.0
        assert sim.state.coordinate_Z == 160.0
        assert sim.state.coordinate_RX == 30.0
    
    def test_writecoordinate_linear(self, e4_with_sim):
        """Test E4 linear Cartesian movement."""
        robot, sim = e4_with_sim
        
        robot.writecoordinate(1, 0, 170.0, 60.0, 170.0, 25.0)
        time.sleep(0.3)
        
        assert sim.state.coordinate_X == 170.0
    
    def test_writecoordinate_gate(self, e4_with_sim):
        """Test E4 gate-type movement."""
        robot, sim = e4_with_sim
        
        robot.writecoordinate(2, 0, 165.0, 55.0, 175.0, 20.0)
        time.sleep(0.3)
        
        assert sim.state.coordinate_X == 165.0
    
    def test_zero(self, e4_with_sim):
        """Test E4 returning to zero position."""
        robot, sim = e4_with_sim
        
        # Move away first
        robot.writeangle(0, 30.0, 20.0, 10.0, 5.0)
        time.sleep(0.3)
        
        # Return to zero
        robot.zero()
        time.sleep(0.3)
        
        assert sim.state.angle_X == 0.0
        assert sim.state.angle_Y == 0.0
        assert sim.state.angle_Z == 0.0
        assert sim.state.angle_A == 0.0


class TestE4Status:
    """Tests for E4 status queries."""
    
    def test_get_angle(self, e4_with_sim):
        """Test E4 angle retrieval (4 axes)."""
        robot, sim = e4_with_sim
        
        sim.set_state(
            angle_X=15.0,
            angle_Y=25.0,
            angle_Z=35.0,
            angle_A=45.0,
            angle_D=10.0
        )
        
        assert float(robot.getAngle(1)) == 15.0  # X
        assert float(robot.getAngle(2)) == 25.0  # Y
        assert float(robot.getAngle(3)) == 35.0  # Z
        assert float(robot.getAngle(4)) == 45.0  # A
        assert float(robot.getAngle(7)) == 10.0  # D (7th axis)
    
    def test_get_angle_invalid(self, e4_with_sim):
        """Test E4 angle retrieval with invalid axis."""
        robot, sim = e4_with_sim
        
        with pytest.raises(Exception, match="parameter error"):
            robot.getAngle(5)  # Invalid for E4
    
    def test_get_coordinate(self, e4_with_sim):
        """Test E4 coordinate retrieval (4 coordinates)."""
        robot, sim = e4_with_sim
        
        sim.set_state(
            coordinate_X=190.0,
            coordinate_Y=70.0,
            coordinate_Z=165.0,
            coordinate_RX=40.0
        )
        
        assert float(robot.getcoordinate(1)) == 190.0  # X
        assert float(robot.getcoordinate(2)) == 70.0   # Y
        assert float(robot.getcoordinate(3)) == 165.0  # Z
        assert float(robot.getcoordinate(4)) == 40.0   # RX
    
    def test_get_coordinate_invalid(self, e4_with_sim):
        """Test E4 coordinate retrieval with invalid coordinate."""
        robot, sim = e4_with_sim
        
        with pytest.raises(Exception, match="parameter error"):
            robot.getcoordinate(5)  # Invalid for E4
    
    def test_version(self, e4_with_sim):
        """Test E4 version query."""
        robot, sim = e4_with_sim
        
        sim.set_firmware_version("E4 V1.5.0", "EXbox V1.5.0")
        
        version = robot.version()
        
        assert "EXbox" in version[0]
        assert "E4" in version[1]


class TestE4InheritedFunctions:
    """Tests for functions inherited from Mirobot_UART."""
    
    def test_speed(self, e4_with_sim):
        """Test E4 speed control (inherited)."""
        robot, sim = e4_with_sim
        
        result = robot.speed(75)
        time.sleep(0.2)
        
        assert result == 1
        assert sim.state.speed == 75
    
    def test_pwm_write(self, e4_with_sim):
        """Test E4 PWM control (inherited)."""
        robot, sim = e4_with_sim
        
        result = robot.pwmWrite(600)
        time.sleep(0.2)
        
        assert result == 1
        assert sim.state.pump_pwm == 600
    
    def test_gripper(self, e4_with_sim):
        """Test E4 gripper control (inherited)."""
        robot, sim = e4_with_sim
        
        result = robot.gripper(1)
        time.sleep(0.2)
        
        assert result == 1
    
    def test_pump(self, e4_with_sim):
        """Test E4 pump control (inherited)."""
        robot, sim = e4_with_sim
        
        result = robot.pump(1)
        time.sleep(0.2)
        
        assert result == 1
        assert sim.state.pump_pwm == 1000
    
    def test_restart(self, e4_with_sim):
        """Test E4 restart command (inherited)."""
        robot, sim = e4_with_sim
        
        result = robot.restart()
        time.sleep(0.2)
        
        assert result == 1
    
    def test_cancellation(self, e4_with_sim):
        """Test E4 cancellation command (inherited)."""
        robot, sim = e4_with_sim
        
        result = robot.cancellation()
        time.sleep(0.2)
        
        assert result == 1
