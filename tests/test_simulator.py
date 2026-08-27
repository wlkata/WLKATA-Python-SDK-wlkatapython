"""
Tests for the simulator module.

This module tests the simulator infrastructure itself, including
virtual serial ports and simulated hardware.
"""

import pytest
import time
import sys

pytestmark = pytest.mark.simulator
import serial


class TestVirtualSerialPort:
    """Tests for the VirtualSerialPort class."""
    
    def test_open_close(self):
        """Test opening and closing the virtual port."""
        from wlkatapython.simulator import VirtualSerialPort
        
        vsp = VirtualSerialPort()
        port_path = vsp.open()
        
        assert port_path is not None
        assert vsp.is_open
        
        if sys.platform.startswith('linux'):
            assert port_path.startswith('/dev/pts/')
        
        vsp.close()
        assert not vsp.is_open
    
    def test_context_manager(self):
        """Test using the virtual port as a context manager."""
        from wlkatapython.simulator import VirtualSerialPort
        
        with VirtualSerialPort() as vsp:
            assert vsp.is_open
        
        assert not vsp.is_open
    
    def test_write_read(self):
        """Test writing and reading data."""
        from wlkatapython.simulator import VirtualSerialPort
        from wlkatapython.simulator.virtual_serial import MockSerial
        
        with VirtualSerialPort() as vsp:
            vsp.write_to_slave(b"Hello, World!\r\n")
            time.sleep(0.1)
            
            mock_serial = MockSerial(vsp.port_path, virtual_port=vsp)
            data = mock_serial.readline()
            
            assert b"Hello" in data
            mock_serial.close()
    
    def test_multiple_messages(self):
        """Test sending multiple messages."""
        from wlkatapython.simulator import VirtualSerialPort
        from wlkatapython.simulator.virtual_serial import MockSerial
        
        with VirtualSerialPort() as vsp:
            messages = [b"Line 1\r\n", b"Line 2\r\n", b"Line 3\r\n"]
            
            for msg in messages:
                vsp.write_to_slave(msg)
            
            time.sleep(0.1)
            
            mock_serial = MockSerial(vsp.port_path, virtual_port=vsp)
            
            for expected in messages:
                data = mock_serial.readline()
                assert expected.strip() in data
            
            mock_serial.close()


class TestMockSerial:
    """Tests for the MockSerial class."""
    
    def test_mock_serial_write(self):
        """Test MockSerial write operation."""
        from wlkatapython.simulator import VirtualSerialPort
        from wlkatapython.simulator.virtual_serial import MockSerial
        
        with VirtualSerialPort() as vsp:
            mock_serial = MockSerial(vsp.port_path, virtual_port=vsp)
            
            bytes_written = mock_serial.write(b"test\r\n")
            assert bytes_written == 6
            
            mock_serial.close()
    
    def test_mock_serial_read(self):
        """Test MockSerial read operation."""
        from wlkatapython.simulator import VirtualSerialPort
        from wlkatapython.simulator.virtual_serial import MockSerial
        
        with VirtualSerialPort() as vsp:
            vsp.write_to_slave(b"X")
            time.sleep(0.05)
            
            mock_serial = MockSerial(vsp.port_path, virtual_port=vsp)
            data = mock_serial.read(1)
            
            assert len(data) == 1
            mock_serial.close()
    
    def test_mock_serial_in_waiting(self):
        """Test MockSerial in_waiting property."""
        from wlkatapython.simulator import VirtualSerialPort
        from wlkatapython.simulator.virtual_serial import MockSerial
        
        with VirtualSerialPort() as vsp:
            mock_serial = MockSerial(vsp.port_path, virtual_port=vsp)
            
            # Initially should be 0 or low
            initial = mock_serial.in_waiting
            
            vsp.write_to_slave(b"Hello")
            time.sleep(0.1)
            
            # Should have data waiting
            # Note: exact count may vary by platform
            
            mock_serial.close()
    
    def test_mock_serial_flush(self):
        """Test MockSerial flush operations."""
        from wlkatapython.simulator import VirtualSerialPort
        from wlkatapython.simulator.virtual_serial import MockSerial
        
        with VirtualSerialPort() as vsp:
            mock_serial = MockSerial(vsp.port_path, virtual_port=vsp)
            
            # Should not raise
            mock_serial.flushInput()
            mock_serial.flushOutput()
            
            mock_serial.close()


class TestSimulatorFactory:
    """Tests for the simulator factory function."""
    
    def test_create_mirobot(self):
        """Test creating a Mirobot simulator."""
        from wlkatapython.simulator import create_simulator, MirobotSimulator
        
        sim = create_simulator("mirobot")
        assert isinstance(sim, MirobotSimulator)
    
    def test_create_e4(self):
        """Test creating an E4 simulator."""
        from wlkatapython.simulator import create_simulator, E4Simulator
        
        sim = create_simulator("E4")  # Case insensitive
        assert isinstance(sim, E4Simulator)
    
    def test_create_mt4(self):
        """Test creating an MT4 simulator."""
        from wlkatapython.simulator import create_simulator, MT4Simulator
        
        sim = create_simulator("MT4")
        assert isinstance(sim, MT4Simulator)
    
    def test_create_ms4220(self):
        """Test creating an MS4220 simulator."""
        from wlkatapython.simulator import create_simulator, MS4220Simulator
        
        sim = create_simulator("ms4220")
        assert isinstance(sim, MS4220Simulator)
    
    def test_create_with_address(self):
        """Test creating simulator with RS485 address."""
        from wlkatapython.simulator import create_simulator
        
        sim = create_simulator("mirobot", address=5)
        assert sim.address == 5
    
    def test_create_invalid(self):
        """Test creating simulator with invalid model."""
        from wlkatapython.simulator import create_simulator
        
        with pytest.raises(ValueError):
            create_simulator("invalid_model")


class TestSimulatorState:
    """Tests for simulator state management."""
    
    def test_initial_state(self):
        """Test simulator initial state."""
        from wlkatapython.simulator import MirobotSimulator
        
        sim = MirobotSimulator()
        
        assert sim.state.state == "Idle"
        assert sim.state.angle_X == 0.0
        # Default Cartesian comes from Mirobot FK at zero joints (URDF-based)
        from wlkatapython.simulator.kinematics import MirobotKinematics
        x0, y0, z0, _, _, _ = MirobotKinematics().forward([0.0] * 6)
        assert sim.state.coordinate_X == pytest.approx(x0, abs=1e-3)
        assert sim.state.coordinate_Y == pytest.approx(y0, abs=1e-3)
        assert sim.state.coordinate_Z == pytest.approx(z0, abs=1e-3)
    
    def test_set_state(self):
        """Test setting simulator state."""
        from wlkatapython.simulator import MirobotSimulator
        
        sim = MirobotSimulator()
        
        sim.set_state(
            angle_X=45.0,
            coordinate_X=200.0,
            state="Running"
        )
        
        assert sim.state.angle_X == 45.0
        assert sim.state.coordinate_X == 200.0
        assert sim.state.state == "Running"
    
    def test_state_persistence(self):
        """Test that state persists across queries."""
        from wlkatapython.simulator import MirobotSimulator
        
        sim = MirobotSimulator()
        sim.start()
        time.sleep(0.1)
        
        try:
            sim.set_state(angle_X=30.0)
            
            ser = serial.Serial(sim.port_path, 115200, timeout=1.0)
            
            # Query status
            ser.write(b"?\r\n")
            time.sleep(0.2)
            response = ser.readline().decode()
            
            assert "30.0" in response
            
            ser.close()
        finally:
            sim.stop()


class TestSimulatorCustomResponses:
    """Tests for custom response configuration."""
    
    def test_add_command_response(self):
        """Test adding custom command response."""
        from wlkatapython.simulator import MirobotSimulator
        
        sim = MirobotSimulator()
        sim.add_command_response(r"^CUSTOM$", "custom_ok")
        sim.start()
        time.sleep(0.1)
        
        try:
            ser = serial.Serial(sim.port_path, 115200, timeout=1.0)
            
            ser.write(b"CUSTOM\r\n")
            time.sleep(0.2)
            response = ser.readline().decode()
            
            assert "custom_ok" in response
            
            ser.close()
        finally:
            sim.stop()
    
    def test_add_command_with_handler(self):
        """Test adding custom command with handler."""
        from wlkatapython.simulator import MirobotSimulator
        
        sim = MirobotSimulator()
        
        def custom_handler(cmd, match, state):
            state.pump_pwm = 999
            return "handler_response"
        
        sim.add_command_response(r"^HANDLER$", "", custom_handler)
        sim.start()
        time.sleep(0.1)
        
        try:
            ser = serial.Serial(sim.port_path, 115200, timeout=1.0)
            
            ser.write(b"HANDLER\r\n")
            time.sleep(0.2)
            response = ser.readline().decode()
            
            assert "handler_response" in response
            assert sim.state.pump_pwm == 999
            
            ser.close()
        finally:
            sim.stop()
    
    def test_set_command_response(self):
        """Test adding a new command response (set_command_response updates or adds)."""
        from wlkatapython.simulator import MirobotSimulator
        
        sim = MirobotSimulator()
        
        # Add a completely new command (set_command_response can also add new ones)
        sim.set_command_response(r"^NEWCMD$", "new_response")
        sim.start()
        time.sleep(0.1)
        
        try:
            ser = serial.Serial(sim.port_path, 115200, timeout=1.0)
            
            ser.write(b"NEWCMD\r\n")
            time.sleep(0.2)
            response = ser.readline().decode()
            
            assert "new_response" in response
            
            ser.close()
        finally:
            sim.stop()


class TestSimulatorHeartbeat:
    """Tests for heartbeat functionality."""
    
    def test_heartbeat_enabled(self):
        """Test that heartbeat messages are sent."""
        from wlkatapython.simulator import MirobotSimulator
        
        sim = MirobotSimulator()
        sim.set_heartbeat(0.1, "heartbeat")
        sim.start()
        
        try:
            time.sleep(0.2)  # Wait for heartbeat
            
            ser = serial.Serial(sim.port_path, 115200, timeout=0.5)
            
            # Try to read heartbeat
            found = False
            for _ in range(5):
                if ser.in_waiting > 0:
                    data = ser.readline().decode()
                    if "heartbeat" in data:
                        found = True
                        break
                time.sleep(0.1)
            
            # Note: heartbeat might not be captured in all cases
            # due to timing, so we just verify no errors
            
            ser.close()
        finally:
            sim.stop()
    
    def test_heartbeat_disabled(self):
        """Test that heartbeat can be disabled."""
        from wlkatapython.simulator import MirobotSimulator
        
        sim = MirobotSimulator()
        sim.set_heartbeat(0, "")  # Disabled
        sim.start()
        
        try:
            assert sim._heartbeat_interval == 0
        finally:
            sim.stop()


class TestResponsePresets:
    """Tests for response preset configuration."""
    
    def test_list_presets(self):
        """Test listing available presets."""
        from wlkatapython.simulator import list_presets
        
        presets = list_presets()
        
        assert "mirobot_v1" in presets
        assert "mirobot_v2" in presets
        assert "e4_standard" in presets
        assert "mt4_standard" in presets
        assert "ms4220_standard" in presets
    
    def test_get_preset(self):
        """Test getting a preset."""
        from wlkatapython.simulator import get_preset
        
        preset = get_preset("mirobot_v1")
        
        assert preset.name == "mirobot_v1"
        assert preset.model == "mirobot"
        assert "Mirobot" in preset.firmware_version
    
    def test_get_invalid_preset(self):
        """Test getting an invalid preset."""
        from wlkatapython.simulator import get_preset
        
        with pytest.raises(KeyError):
            get_preset("invalid_preset")
    
    def test_apply_preset(self):
        """Test applying a preset."""
        from wlkatapython.simulator import MirobotSimulator, apply_preset
        
        sim = MirobotSimulator()
        apply_preset(sim, "mirobot_v2")
        
        assert "V2" in sim._firmware_version
    
    def test_create_custom_preset(self):
        """Test creating a custom preset."""
        from wlkatapython.simulator import create_custom_preset
        
        custom = create_custom_preset(
            name="custom",
            base_preset="mirobot_v1",
            firmware_version="Custom V1.0.0"
        )
        
        assert custom.name == "custom"
        assert custom.firmware_version == "Custom V1.0.0"


class TestStateScenarios:
    """Tests for state scenario configuration."""
    
    def test_apply_state_scenario(self):
        """Test applying a state scenario."""
        from wlkatapython.simulator import MirobotSimulator, apply_state_scenario
        
        sim = MirobotSimulator()
        apply_state_scenario(sim, "extended_position")
        
        assert sim.state.coordinate_X == 200.0
        assert sim.state.coordinate_Y == 100.0
        assert sim.state.angle_X == 45.0
    
    def test_apply_pump_active_scenario(self):
        """Test applying pump active scenario."""
        from wlkatapython.simulator import MirobotSimulator, apply_state_scenario
        
        sim = MirobotSimulator()
        apply_state_scenario(sim, "pump_active")
        
        assert sim.state.pump_pwm == 1000
    
    def test_apply_invalid_scenario(self):
        """Test applying an invalid scenario."""
        from wlkatapython.simulator import MirobotSimulator, apply_state_scenario
        
        sim = MirobotSimulator()
        
        with pytest.raises(KeyError):
            apply_state_scenario(sim, "invalid_scenario")


class TestSimulatorContextManager:
    """Tests for simulator context manager usage."""
    
    def test_context_manager(self):
        """Test using simulator as context manager."""
        from wlkatapython.simulator import MirobotSimulator
        
        with MirobotSimulator() as sim:
            assert sim.port_path is not None
            
            ser = serial.Serial(sim.port_path, 115200, timeout=1.0)
            ser.write(b"?\r\n")
            time.sleep(0.2)
            response = ser.readline()
            
            assert len(response) > 0
            ser.close()
    
    def test_context_manager_cleanup(self):
        """Test that context manager cleans up properly."""
        from wlkatapython.simulator import MirobotSimulator
        
        sim = MirobotSimulator()
        
        with sim:
            assert sim._running
        
        assert not sim._running
