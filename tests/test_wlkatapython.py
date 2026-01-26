"""
Tests for the main wlkatapython module.

This module tests the public API of the wlkatapython package,
ensuring all classes are properly exported and functional.
"""

import pytest
import time
import serial

pytestmark = pytest.mark.wlkatapython


class TestModuleImports:
    """Tests for module imports and exports."""
    
    def test_import_wlkatapython(self):
        """Test that wlkatapython can be imported."""
        import wlkatapython
        assert wlkatapython is not None
    
    def test_import_mirobot_uart(self):
        """Test that Mirobot_UART can be imported."""
        from wlkatapython import Mirobot_UART
        assert Mirobot_UART is not None
    
    def test_import_e4_uart(self):
        """Test that E4_UART can be imported."""
        from wlkatapython import E4_UART
        assert E4_UART is not None
    
    def test_import_mt4_uart(self):
        """Test that MT4_UART can be imported."""
        from wlkatapython import MT4_UART
        assert MT4_UART is not None
    
    def test_import_ms4220_uart(self):
        """Test that MS4220_UART can be imported."""
        from wlkatapython import MS4220_UART
        assert MS4220_UART is not None
    
    def test_import_wlkata_uart(self):
        """Test that Wlkata_UART can be imported."""
        from wlkatapython import Wlkata_UART
        assert Wlkata_UART is not None


class TestMirobotViaWlkatapython:
    """Tests for Mirobot accessed via wlkatapython module."""
    
    def test_mirobot_instantiation(self):
        """Test that Mirobot can be instantiated via wlkatapython."""
        import wlkatapython
        
        robot = wlkatapython.Mirobot_UART()
        assert robot is not None
        assert hasattr(robot, 'init')
        assert hasattr(robot, 'homing')
        assert hasattr(robot, 'writeangle')
    
    def test_mirobot_full_workflow(self):
        """Test complete Mirobot workflow via wlkatapython."""
        import wlkatapython
        from simulator import MirobotSimulator
        
        sim = MirobotSimulator()
        sim.start()
        time.sleep(0.1)
        
        try:
            ser = serial.Serial(sim.port_path, 115200, timeout=2.0)
            
            robot = wlkatapython.Mirobot_UART()
            robot.init(ser, -1)
            
            # Test homing
            robot.homing()
            time.sleep(0.7)
            assert sim.state.angle_X == 0.0
            
            # Test movement
            robot.writeangle(0, 30.0, 20.0, 10.0, 0.0, 0.0, 0.0)
            time.sleep(0.3)
            assert sim.state.angle_X == 30.0
            
            # Test end effector
            robot.pwmWrite(500)
            time.sleep(0.2)
            assert sim.state.pump_pwm == 500
            
            # Test status query
            status = robot.getStatus()
            assert status["state"] == "Idle"
            
            ser.close()
        finally:
            sim.stop()


class TestE4ViaWlkatapython:
    """Tests for E4 accessed via wlkatapython module."""
    
    def test_e4_instantiation(self):
        """Test that E4 can be instantiated via wlkatapython."""
        import wlkatapython
        
        robot = wlkatapython.E4_UART()
        assert robot is not None
        assert hasattr(robot, 'init')
        assert hasattr(robot, 'homing')
        assert hasattr(robot, 'writeangle')
    
    def test_e4_full_workflow(self):
        """Test complete E4 workflow via wlkatapython."""
        import wlkatapython
        from simulator import E4Simulator
        
        sim = E4Simulator()
        sim.start()
        time.sleep(0.1)
        
        try:
            ser = serial.Serial(sim.port_path, 115200, timeout=2.0)
            
            robot = wlkatapython.E4_UART()
            robot.init(ser, -1)
            
            robot.homing()
            time.sleep(0.7)
            assert sim.state.angle_X == 0.0
            
            robot.writeangle(0, 25.0, 35.0, 45.0, 55.0)
            time.sleep(0.3)
            assert sim.state.angle_X == 25.0
            
            ser.close()
        finally:
            sim.stop()


class TestMT4ViaWlkatapython:
    """Tests for MT4 accessed via wlkatapython module."""
    
    def test_mt4_instantiation(self):
        """Test that MT4 can be instantiated via wlkatapython."""
        import wlkatapython
        
        robot = wlkatapython.MT4_UART()
        assert robot is not None
        assert hasattr(robot, 'init')
        assert hasattr(robot, 'homing')
    
    def test_mt4_full_workflow(self):
        """Test complete MT4 workflow via wlkatapython."""
        import wlkatapython
        from simulator import MT4Simulator
        
        sim = MT4Simulator()
        sim.start()
        time.sleep(0.1)
        
        try:
            ser = serial.Serial(sim.port_path, 115200, timeout=2.0)
            
            robot = wlkatapython.MT4_UART()
            robot.init(ser, -1)
            
            robot.homing()
            time.sleep(0.7)
            assert sim.state.angle_X == 0.0
            
            ser.close()
        finally:
            sim.stop()


class TestMS4220ViaWlkatapython:
    """Tests for MS4220 accessed via wlkatapython module."""
    
    def test_ms4220_instantiation(self):
        """Test that MS4220 can be instantiated via wlkatapython."""
        import wlkatapython
        
        robot = wlkatapython.MS4220_UART()
        assert robot is not None
        assert hasattr(robot, 'init')
        assert hasattr(robot, 'speed')
    
    def test_ms4220_full_workflow(self):
        """Test complete MS4220 workflow via wlkatapython."""
        import wlkatapython
        from simulator import MS4220Simulator
        
        sim = MS4220Simulator(address=10)
        sim.start()
        time.sleep(0.1)
        
        try:
            ser = serial.Serial(sim.port_path, 38400, timeout=2.0)
            
            robot = wlkatapython.MS4220_UART()
            robot.init(ser, 10)
            
            robot.speed(75)
            time.sleep(0.2)
            assert sim.motor_speed == 75
            
            ser.close()
        finally:
            sim.stop()


class TestClassInheritance:
    """Tests for class inheritance structure."""
    
    def test_mirobot_inheritance(self):
        """Test Mirobot_UART inheritance chain."""
        import wlkatapython
        from wlkatapython.robots import WLKATA_UART
        
        robot = wlkatapython.Mirobot_UART()
        assert isinstance(robot, WLKATA_UART)
    
    def test_e4_inheritance(self):
        """Test E4_UART inherits from WLKATA_UART."""
        import wlkatapython
        from wlkatapython.robots import WLKATA_UART as Base
        
        robot = wlkatapython.E4_UART()
        assert isinstance(robot, Base)
    
    def test_mt4_inheritance(self):
        """Test MT4_UART inherits from WLKATA_UART."""
        import wlkatapython
        from wlkatapython.robots import WLKATA_UART as Base
        
        robot = wlkatapython.MT4_UART()
        assert isinstance(robot, Base)
    
    def test_ms4220_inheritance(self):
        """Test MS4220_UART inherits from WLKATA_UART."""
        import wlkatapython
        from wlkatapython.robots import WLKATA_UART
        
        robot = wlkatapython.MS4220_UART()
        assert isinstance(robot, WLKATA_UART)


class TestMultipleRobots:
    """Tests for using multiple robots simultaneously."""
    
    def test_two_mirobots(self):
        """Test using two Mirobot instances simultaneously."""
        import wlkatapython
        from simulator import MirobotSimulator
        
        sim1 = MirobotSimulator(address=1)
        sim2 = MirobotSimulator(address=2)
        
        sim1.start()
        sim2.start()
        time.sleep(0.1)
        
        try:
            ser1 = serial.Serial(sim1.port_path, 115200, timeout=2.0)
            ser2 = serial.Serial(sim2.port_path, 115200, timeout=2.0)
            
            robot1 = wlkatapython.Mirobot_UART()
            robot2 = wlkatapython.Mirobot_UART()
            
            robot1.init(ser1, 1)
            robot2.init(ser2, 2)
            
            # Move robot1
            robot1.writeangle(0, 45.0, 0.0, 0.0, 0.0, 0.0, 0.0)
            time.sleep(0.3)
            
            # Move robot2 differently
            robot2.writeangle(0, 0.0, 45.0, 0.0, 0.0, 0.0, 0.0)
            time.sleep(0.3)
            
            # Verify independent states
            assert sim1.state.angle_X == 45.0
            assert sim1.state.angle_Y == 0.0
            assert sim2.state.angle_X == 0.0
            assert sim2.state.angle_Y == 45.0
            
            ser1.close()
            ser2.close()
        finally:
            sim1.stop()
            sim2.stop()
    
    def test_mixed_robots(self):
        """Test using different robot types simultaneously."""
        import wlkatapython
        from simulator import MirobotSimulator, E4Simulator, MS4220Simulator
        
        mirobot_sim = MirobotSimulator()
        e4_sim = E4Simulator()
        ms4220_sim = MS4220Simulator(address=10)
        
        mirobot_sim.start()
        e4_sim.start()
        ms4220_sim.start()
        time.sleep(0.1)
        
        try:
            mirobot_ser = serial.Serial(mirobot_sim.port_path, 115200, timeout=2.0)
            e4_ser = serial.Serial(e4_sim.port_path, 115200, timeout=2.0)
            ms4220_ser = serial.Serial(ms4220_sim.port_path, 38400, timeout=2.0)
            
            mirobot = wlkatapython.Mirobot_UART()
            e4 = wlkatapython.E4_UART()
            ms4220 = wlkatapython.MS4220_UART()
            
            mirobot.init(mirobot_ser, -1)
            e4.init(e4_ser, -1)
            ms4220.init(ms4220_ser, 10)
            
            # Operate all robots
            mirobot.pwmWrite(100)
            e4.homing()
            ms4220.speed(50)
            
            time.sleep(0.7)
            
            # Verify states
            assert mirobot_sim.state.pump_pwm == 100
            assert e4_sim.state.angle_X == 0.0
            assert ms4220_sim.motor_speed == 50
            
            mirobot_ser.close()
            e4_ser.close()
            ms4220_ser.close()
        finally:
            mirobot_sim.stop()
            e4_sim.stop()
            ms4220_sim.stop()
