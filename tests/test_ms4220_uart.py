"""
Tests for the MS4220_UART class.

This module tests all functionality of the MS4220 stepper motor controller
using the simulated hardware.
"""

import pytest
import time
import serial

pytestmark = pytest.mark.ms4220


class TestMS4220Initialization:
    """Tests for MS4220 initialization."""
    
    def test_ms4220_init(self, ms4220):
        """Test that MS4220 can be initialized."""
        assert ms4220 is not None
        assert ms4220.pSerial is not None
        assert ms4220.address == 10
    
    def test_ms4220_inherits_from_wlkata(self, ms4220):
        """Test that MS4220 inherits from WLKATA_UART."""
        assert hasattr(ms4220, 'sendMsg')
        assert hasattr(ms4220, 'read_message')
        assert hasattr(ms4220, 'message_print')


class TestMS4220SpeedControl:
    """Tests for MS4220 speed control."""
    
    def test_speed_positive(self):
        """Test MS4220 positive speed setting."""
        from wlkatapython.simulator import MS4220Simulator
        from wlkatapython.robots import MS4220_UART
        
        sim = MS4220Simulator(address=10)
        sim.start()
        time.sleep(0.1)
        
        try:
            ser = serial.Serial(sim.port_path, 38400, timeout=2.0)
            ms4220 = MS4220_UART()
            ms4220.init(ser, 10)
            
            result = ms4220.speed(75)
            time.sleep(0.2)
            
            assert result == 1
            assert sim.motor_speed == 75
            
            ser.close()
        finally:
            sim.stop()
    
    def test_speed_negative(self):
        """Test MS4220 negative speed setting (reverse)."""
        from wlkatapython.simulator import MS4220Simulator
        from wlkatapython.robots import MS4220_UART
        
        sim = MS4220Simulator(address=10)
        sim.start()
        time.sleep(0.1)
        
        try:
            ser = serial.Serial(sim.port_path, 38400, timeout=2.0)
            ms4220 = MS4220_UART()
            ms4220.init(ser, 10)
            
            result = ms4220.speed(-50)
            time.sleep(0.2)
            
            assert result == 1
            assert sim.motor_speed == -50
            
            ser.close()
        finally:
            sim.stop()
    
    def test_speed_zero(self):
        """Test MS4220 zero speed (stop)."""
        from wlkatapython.simulator import MS4220Simulator
        from wlkatapython.robots import MS4220_UART
        
        sim = MS4220Simulator(address=10)
        sim.start()
        time.sleep(0.1)
        
        try:
            ser = serial.Serial(sim.port_path, 38400, timeout=2.0)
            ms4220 = MS4220_UART()
            ms4220.init(ser, 10)
            
            # First set a non-zero speed
            ms4220.speed(50)
            time.sleep(0.2)
            
            # Then stop
            result = ms4220.speed(0)
            time.sleep(0.2)
            
            assert result == 1
            assert sim.motor_speed == 0
            
            ser.close()
        finally:
            sim.stop()
    
    def test_speed_max(self):
        """Test MS4220 maximum speed."""
        from wlkatapython.simulator import MS4220Simulator
        from wlkatapython.robots import MS4220_UART
        
        sim = MS4220Simulator(address=10)
        sim.start()
        time.sleep(0.1)
        
        try:
            ser = serial.Serial(sim.port_path, 38400, timeout=2.0)
            ms4220 = MS4220_UART()
            ms4220.init(ser, 10)
            
            result = ms4220.speed(100)
            time.sleep(0.2)
            
            assert result == 1
            assert sim.motor_speed == 100
            
            ser.close()
        finally:
            sim.stop()
    
    @pytest.mark.parametrize("speed", [0, 10, 25, 50, 75, 100])
    def test_speed_values(self, speed):
        """Test MS4220 with various speed values."""
        from wlkatapython.simulator import MS4220Simulator
        from wlkatapython.robots import MS4220_UART
        
        sim = MS4220Simulator(address=10)
        sim.start()
        time.sleep(0.1)
        
        try:
            ser = serial.Serial(sim.port_path, 38400, timeout=2.0)
            ms4220 = MS4220_UART()
            ms4220.init(ser, 10)
            
            result = ms4220.speed(speed)
            time.sleep(0.2)
            
            assert result == 1
            assert sim.motor_speed == speed
            
            ser.close()
        finally:
            sim.stop()


class TestMS4220RS485:
    """Tests for MS4220 RS485 addressing."""
    
    def test_different_addresses(self):
        """Test MS4220 with different RS485 addresses."""
        from wlkatapython.simulator import MS4220Simulator
        from wlkatapython.robots import MS4220_UART
        
        for address in [1, 5, 10, 100, 255]:
            sim = MS4220Simulator(address=address)
            sim.start()
            time.sleep(0.1)
            
            try:
                ser = serial.Serial(sim.port_path, 38400, timeout=2.0)
                ms4220 = MS4220_UART()
                ms4220.init(ser, address)
                
                result = ms4220.speed(60)
                time.sleep(0.2)
                
                assert result == 1
                assert sim.motor_speed == 60
                
                ser.close()
            finally:
                sim.stop()
    
    def test_sendmsg_with_address(self):
        """Test that sendMsg includes RS485 address prefix."""
        from wlkatapython.simulator import MS4220Simulator
        from wlkatapython.robots import MS4220_UART
        
        sim = MS4220Simulator(address=15)
        sim.message_print(False)
        sim.start()
        time.sleep(0.1)
        
        try:
            ser = serial.Serial(sim.port_path, 38400, timeout=2.0)
            ms4220 = MS4220_UART()
            ms4220.init(ser, 15)
            
            # Send a raw command
            ms4220.sendMsg("G6 F50")
            time.sleep(0.2)
            
            # Verify it was processed
            assert sim.motor_speed == 50
            
            ser.close()
        finally:
            sim.stop()


class TestMS4220InheritedFunctions:
    """Tests for functions inherited from WLKATA_UART."""
    
    def test_read_message(self):
        """Test MS4220 read_message."""
        from wlkatapython.simulator import MS4220Simulator
        from wlkatapython.robots import MS4220_UART
        
        sim = MS4220Simulator(address=10)
        sim.start()
        time.sleep(0.1)
        
        try:
            ser = serial.Serial(sim.port_path, 38400, timeout=2.0)
            ms4220 = MS4220_UART()
            ms4220.init(ser, 10)
            
            # Send a command that generates a response
            ms4220.sendMsg("G6 F30")
            time.sleep(0.2)
            
            response = ms4220.read_message()
            assert "ok" in response
            
            ser.close()
        finally:
            sim.stop()
    
    def test_message_print(self):
        """Test MS4220 message_print setting."""
        from wlkatapython.simulator import MS4220Simulator
        from wlkatapython.robots import MS4220_UART
        
        sim = MS4220Simulator(address=10)
        sim.start()
        time.sleep(0.1)
        
        try:
            ser = serial.Serial(sim.port_path, 38400, timeout=2.0)
            ms4220 = MS4220_UART()
            ms4220.init(ser, 10)
            
            # Should not raise
            ms4220.message_print(True)
            ms4220.message_print(False)
            
            ser.close()
        finally:
            sim.stop()
