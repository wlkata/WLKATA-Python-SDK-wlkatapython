"""
Tests for JSON-based response configuration.

This module tests the ability to configure simulator responses via JSON files
and separate handler functions.
"""

import pytest
import time
import json

pytestmark = pytest.mark.simulator
import tempfile
import serial
from pathlib import Path

from simulator import MirobotSimulator, create_simulator
from simulator.config.config_loader import ResponseConfigLoader
from simulator.config.handlers import (
    get_handler,
    register_handler,
    HANDLER_REGISTRY,
)


class TestConfigLoader:
    """Tests for the ResponseConfigLoader class."""
    
    def test_loader_initialization(self):
        """Test that loader can be initialized."""
        loader = ResponseConfigLoader()
        assert loader.commands == []
        assert "unknown_command_response" in loader.settings
    
    def test_load_default_mirobot_config(self):
        """Test loading default Mirobot config."""
        loader = ResponseConfigLoader()
        loader.load_default_config("mirobot")
        
        # Should have loaded commands
        assert len(loader.commands) > 0
        
        # Check for known commands
        command_names = [cmd.name for cmd in loader.commands]
        assert "status_query" in command_names
        assert "homing" in command_names
        assert "cartesian_movement" in command_names
    
    def test_load_config_from_dict(self):
        """Test loading config from a dictionary."""
        config = {
            "commands": [
                {
                    "name": "test_cmd",
                    "pattern": "^TEST$",
                    "handler": None,
                    "response": "test_ok",
                    "description": "Test command"
                }
            ],
            "custom_commands": [],
            "settings": {}
        }
        
        loader = ResponseConfigLoader()
        loader.load_from_dict(config)
        
        assert len(loader.commands) == 1
        assert loader.commands[0].name == "test_cmd"
        assert loader.commands[0].default_response == "test_ok"
    
    def test_add_command_programmatically(self):
        """Test adding commands programmatically."""
        loader = ResponseConfigLoader()
        loader.add_command(
            name="dynamic_cmd",
            pattern="^DYNAMIC$",
            handler_name=None,
            response="dynamic_ok",
            description="Dynamic command"
        )
        
        assert len(loader.commands) == 1
        assert loader.commands[0].name == "dynamic_cmd"
    
    def test_process_command(self):
        """Test processing a command."""
        config = {
            "commands": [
                {
                    "name": "greeting",
                    "pattern": "^HELLO$",
                    "handler": None,
                    "response": "world",
                    "description": "Greeting"
                }
            ],
            "custom_commands": [],
            "settings": {}
        }
        
        loader = ResponseConfigLoader()
        loader.load_from_dict(config)
        
        from simulator.simulated_hardware import RobotState
        state = RobotState()
        context = {}
        
        matched, response = loader.process_command("HELLO", state, context)
        
        assert matched is True
        assert response == "world"
    
    def test_process_unknown_command(self):
        """Test processing an unknown command."""
        loader = ResponseConfigLoader()
        loader.load_from_dict({"commands": [], "custom_commands": [], "settings": {}})
        
        from simulator.simulated_hardware import RobotState
        state = RobotState()
        
        matched, response = loader.process_command("UNKNOWN", state, {})
        
        assert matched is False
        assert response == "error"  # Default unknown response
    
    def test_get_command_list(self):
        """Test getting list of configured commands."""
        config = {
            "commands": [
                {"name": "cmd1", "pattern": "^A$", "handler": None, "response": "a"},
                {"name": "cmd2", "pattern": "^B$", "handler": None, "response": "b"},
            ],
            "custom_commands": [],
            "settings": {}
        }
        
        loader = ResponseConfigLoader()
        loader.load_from_dict(config)
        
        cmd_list = loader.get_command_list()
        
        assert len(cmd_list) == 2
        assert cmd_list[0]["name"] == "cmd1"
        assert cmd_list[1]["name"] == "cmd2"


class TestHandlers:
    """Tests for handler functions."""
    
    def test_get_handler(self):
        """Test getting a handler by name."""
        handler = get_handler("handle_status_query")
        assert handler is not None
        assert callable(handler)
    
    def test_get_unknown_handler(self):
        """Test getting an unknown handler."""
        handler = get_handler("nonexistent_handler")
        assert handler is None
    
    def test_register_custom_handler(self):
        """Test registering a custom handler."""
        def my_custom_handler(command, match, state, context):
            return "custom_response"
        
        register_handler("my_custom_handler", my_custom_handler)
        
        handler = get_handler("my_custom_handler")
        assert handler is not None
        assert handler(None, None, None, None) == "custom_response"
    
    def test_handler_modifies_state(self):
        """Test that handlers can modify robot state."""
        from simulator.simulated_hardware import RobotState
        from simulator.config.handlers import handle_pwm_control
        import re
        
        state = RobotState()
        match = re.match(r"^M3 S(\d+)$", "M3 S500")
        context = {}
        
        response = handle_pwm_control("M3 S500", match, state, context)
        
        assert response == "ok"
        assert state.pump_pwm == 500


class TestSimulatorWithJsonConfig:
    """Tests for simulator using JSON configuration."""
    
    def test_simulator_with_json_config(self):
        """Test simulator using JSON configuration."""
        sim = MirobotSimulator(use_json_config=True)
        port = sim.start()
        time.sleep(0.1)
        
        try:
            ser = serial.Serial(port, 115200, timeout=1.0)
            
            # Test status query
            ser.write(b"?\r\n")
            time.sleep(0.2)
            response = ser.readline().decode()
            
            assert "<" in response
            assert "Idle" in response
            
            # Test custom command from JSON
            ser.write(b"$M\r\n")
            time.sleep(0.2)
            response = ser.readline().decode()
            
            assert "ok" in response
            
            ser.close()
        finally:
            sim.stop()
    
    def test_simulator_custom_command_via_json(self):
        """Test custom commands defined in JSON config."""
        sim = MirobotSimulator(use_json_config=True)
        port = sim.start()
        time.sleep(0.1)
        
        try:
            ser = serial.Serial(port, 115200, timeout=1.0)
            
            # Test $P command (custom position query)
            ser.write(b"$P\r\n")
            time.sleep(0.2)
            response = ser.readline().decode()
            
            assert "X:" in response
            assert "Y:" in response
            assert "Z:" in response
            
            # Test ECHO command
            ser.write(b"ECHO hello world\r\n")
            time.sleep(0.2)
            response = ser.readline().decode()
            
            assert "ECHO:" in response
            assert "hello world" in response
            
            ser.close()
        finally:
            sim.stop()
    
    def test_simulator_load_config_after_init(self):
        """Test loading JSON config after initialization."""
        sim = MirobotSimulator()  # Default mode (no JSON)
        
        # Load JSON config
        sim.load_config_from_json()
        
        port = sim.start()
        time.sleep(0.1)
        
        try:
            ser = serial.Serial(port, 115200, timeout=1.0)
            
            # Custom command should work now
            ser.write(b"$M\r\n")
            time.sleep(0.2)
            response = ser.readline().decode()
            
            assert "ok" in response
            
            ser.close()
        finally:
            sim.stop()
    
    def test_simulator_load_custom_config_dict(self):
        """Test loading custom config from dictionary."""
        config = {
            "commands": [
                {
                    "name": "custom_test",
                    "pattern": "^MYTEST$",
                    "handler": None,
                    "response": "mytest_ok",
                    "description": "My custom test command"
                }
            ],
            "custom_commands": [],
            "settings": {}
        }
        
        sim = MirobotSimulator()
        sim.load_config_from_dict(config)
        
        port = sim.start()
        time.sleep(0.1)
        
        try:
            ser = serial.Serial(port, 115200, timeout=1.0)
            
            ser.write(b"MYTEST\r\n")
            time.sleep(0.2)
            response = ser.readline().decode()
            
            assert "mytest_ok" in response
            
            ser.close()
        finally:
            sim.stop()
    
    def test_simulator_add_json_command(self):
        """Test adding commands via add_json_command."""
        sim = MirobotSimulator()
        
        # Add a custom command
        sim.add_json_command(
            name="dynamic_hello",
            pattern="^HELLO (\\w+)$",
            handler_name="handle_echo",
            response="hello_default",
            description="Say hello"
        )
        
        port = sim.start()
        time.sleep(0.1)
        
        try:
            ser = serial.Serial(port, 115200, timeout=1.0)
            
            ser.write(b"HELLO world\r\n")
            time.sleep(0.2)
            response = ser.readline().decode()
            
            # Should use the echo handler
            assert "ECHO:" in response or "world" in response
            
            ser.close()
        finally:
            sim.stop()
    
    def test_movement_handlers_in_json_config(self):
        """Test that movement handlers work correctly with JSON config."""
        sim = MirobotSimulator(use_json_config=True)
        port = sim.start()
        time.sleep(0.1)
        
        try:
            ser = serial.Serial(port, 115200, timeout=1.0)
            
            # Test homing
            ser.write(b"o105=8\r\n")
            time.sleep(0.6)
            ser.readline()
            
            assert sim.state.angle_X == 0.0
            
            # Test absolute movement
            ser.write(b"M21G90G00X45Y30Z15A0B0C0\r\n")
            time.sleep(0.3)
            ser.readline()
            
            assert sim.state.angle_X == 45.0
            assert sim.state.angle_Y == 30.0
            
            # Test incremental movement
            ser.write(b"M21G91G00X10Y10Z10A0B0C0\r\n")
            time.sleep(0.3)
            ser.readline()
            
            assert sim.state.angle_X == 55.0
            assert sim.state.angle_Y == 40.0
            
            ser.close()
        finally:
            sim.stop()


class TestConfigFile:
    """Tests for config file operations."""
    
    def test_save_and_load_config(self):
        """Test saving and loading configuration."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            config_path = f.name
        
        try:
            # Create and configure loader
            loader = ResponseConfigLoader()
            loader.add_command("test1", "^T1$", None, "t1_ok")
            loader.add_command("test2", "^T2$", None, "t2_ok")
            
            # Save config
            loader.save_config(config_path)
            
            # Load into new loader
            loader2 = ResponseConfigLoader()
            loader2.load_config(config_path)
            
            assert len(loader2.commands) == 2
            
            # Verify commands work
            from simulator.simulated_hardware import RobotState
            state = RobotState()
            
            matched, response = loader2.process_command("T1", state, {})
            assert matched and response == "t1_ok"
            
            matched, response = loader2.process_command("T2", state, {})
            assert matched and response == "t2_ok"
            
        finally:
            Path(config_path).unlink(missing_ok=True)
    
    def test_config_file_not_found(self):
        """Test loading non-existent config file."""
        loader = ResponseConfigLoader()
        
        with pytest.raises(FileNotFoundError):
            loader.load_config("/nonexistent/path/config.json")
    
    def test_default_config_exists(self):
        """Test that default mirobot config file exists."""
        config_path = ResponseConfigLoader.get_default_config_path("mirobot")
        assert config_path.exists()


class TestConfigInheritance:
    """Tests for configuration inheritance."""
    
    def test_base_config_exists(self):
        """Test that base config file exists."""
        config_path = ResponseConfigLoader.get_default_config_path("base")
        assert config_path.exists()
    
    def test_mirobot_extends_base(self):
        """Test that Mirobot config extends base config."""
        loader = ResponseConfigLoader()
        loader.load_default_config("mirobot")
        
        # Should have commands from both base and mirobot
        command_names = [cmd.name for cmd in loader.commands]
        
        # Base commands
        assert "version_query" in command_names
        assert "restart" in command_names
        
        # Mirobot-specific
        assert any("gpio" in name for name in command_names)
    
    def test_e4_extends_base(self):
        """Test that E4 config extends base config."""
        loader = ResponseConfigLoader()
        loader.load_default_config("e4")
        
        command_names = [cmd.name for cmd in loader.commands]
        
        # Base commands
        assert "version_query" in command_names
        
        # E4 should have status_query with E4-specific handler
        status_cmd = next(c for c in loader.commands if c.name == "status_query")
        assert status_cmd.handler_name == "handle_e4_status_query"
    
    def test_handler_override(self):
        """Test that model config can override base handlers."""
        # Load base config
        base_loader = ResponseConfigLoader()
        base_loader.load_default_config("base")
        base_status = next(c for c in base_loader.commands if c.name == "status_query")
        
        # Load mirobot config (should override)
        mirobot_loader = ResponseConfigLoader()
        mirobot_loader.load_default_config("mirobot")
        mirobot_status = next(c for c in mirobot_loader.commands if c.name == "status_query")
        
        # Handlers should be different
        assert mirobot_status.handler_name == "handle_mirobot_status_query"
    
    def test_disabled_command(self):
        """Test that commands can be disabled."""
        # E4 config disables expand_axis
        loader = ResponseConfigLoader()
        loader.load_default_config("e4")
        
        command_names = [cmd.name for cmd in loader.commands]
        assert "expand_axis" not in command_names
    
    def test_mt4_shares_e4_handlers(self):
        """Test that MT4 uses the same handlers as E4."""
        e4_loader = ResponseConfigLoader()
        e4_loader.load_default_config("e4")
        
        mt4_loader = ResponseConfigLoader()
        mt4_loader.load_default_config("mt4")
        
        # Both should use E4 handlers
        e4_status = next(c for c in e4_loader.commands if c.name == "status_query")
        mt4_status = next(c for c in mt4_loader.commands if c.name == "status_query")
        
        assert e4_status.handler_name == mt4_status.handler_name
    
    def test_ms4220_independent_config(self):
        """Test that MS4220 has independent config (no base)."""
        loader = ResponseConfigLoader()
        loader.load_default_config("ms4220")
        
        command_names = [cmd.name for cmd in loader.commands]
        
        # Should have MS4220-specific commands
        assert "speed_set" in command_names
        assert "position_absolute" in command_names
        
        # Should NOT have base robot commands
        assert "cartesian_movement" not in command_names
        assert "angle_movement" not in command_names


class TestCaseInsensitive:
    """Tests for case-insensitive command matching."""
    
    def test_lowercase_command(self):
        """Test that lowercase commands work."""
        loader = ResponseConfigLoader()
        loader.load_default_config("mirobot")
        
        from simulator.simulated_hardware import RobotState
        state = RobotState()
        
        # Send lowercase version of $V command
        matched, _ = loader.process_command("$v", state, {})
        assert matched
    
    def test_mixed_case_command(self):
        """Test that mixed case commands work."""
        loader = ResponseConfigLoader()
        loader.load_default_config("mirobot")
        
        from simulator.simulated_hardware import RobotState
        state = RobotState()
        
        # Send mixed case movement command
        matched, _ = loader.process_command("m21g90g00x45y30z0a0b0c0", state, {})
        assert matched
    
    def test_uppercase_command(self):
        """Test that uppercase commands work."""
        loader = ResponseConfigLoader()
        loader.load_default_config("mirobot")
        
        from simulator.simulated_hardware import RobotState
        state = RobotState()
        
        # Send uppercase command
        matched, _ = loader.process_command("M21G90G00X45Y30Z0A0B0C0", state, {})
        assert matched


class TestModelSpecificHandlers:
    """Tests for model-specific handlers."""
    
    def test_mirobot_status_format(self):
        """Test Mirobot status response format (6-axis)."""
        from simulator.config.handlers import handle_mirobot_status_query
        from simulator.simulated_hardware import RobotState
        
        state = RobotState()
        state.angle_X = 10.0
        state.angle_Y = 20.0
        state.angle_Z = 30.0
        
        response = handle_mirobot_status_query("?", None, state, {})
        
        assert "Angle(ABCDXYZ)" in response
        assert "10.0" in response
        assert "20.0" in response
        assert "30.0" in response
    
    def test_e4_status_format(self):
        """Test E4 status response format (4-axis)."""
        from simulator.config.handlers import handle_e4_status_query
        from simulator.simulated_hardware import RobotState
        
        state = RobotState()
        state.angle_X = 15.0
        state.angle_Y = 25.0
        
        response = handle_e4_status_query("?", None, state, {})
        
        assert "Angle(XYZA)" in response
        assert "15.0" in response
        assert "25.0" in response
        # Should NOT have 6-axis format
        assert "Angle(ABCDXYZ)" not in response
    
    def test_e4_angle_movement(self):
        """Test E4 angle movement (4-axis only)."""
        from simulator.config.handlers import handle_e4_angle_movement
        from simulator.simulated_hardware import RobotState
        import re
        
        state = RobotState()
        state.angle_X = 0.0
        
        match = re.match(r".*", "M21G90G00X45Y30Z15A10")
        handle_e4_angle_movement("M21G90G00X45Y30Z15A10", match, state, {})
        
        assert state.angle_X == 45.0
        assert state.angle_Y == 30.0
        assert state.angle_Z == 15.0
        assert state.angle_A == 10.0
        # B and C should be unchanged (not supported on E4)
        assert state.angle_B == 0.0
        assert state.angle_C == 0.0
    
    def test_ms4220_status_format(self):
        """Test MS4220 status response format."""
        from simulator.config.handlers import handle_ms4220_status_query
        from simulator.simulated_hardware import RobotState
        
        state = RobotState()
        state.motor_position = 1000
        state.motor_speed = 500
        state.motor_state = "Running"
        
        response = handle_ms4220_status_query("?", None, state, {})
        
        assert "Running" in response
        assert "Position:1000" in response
        assert "Speed:500" in response
    
    def test_ms4220_relative_movement(self):
        """Test MS4220 relative movement."""
        from simulator.config.handlers import handle_ms4220_relative
        from simulator.simulated_hardware import RobotState
        import re
        
        state = RobotState()
        state.motor_position = 100
        
        match = re.match(r"^R([-\d]+)$", "R50")
        handle_ms4220_relative("R50", match, state, {})
        
        assert state.motor_position == 150
