"""
Simulated hardware for WLKATA robots.

This module provides simulated robot hardware that responds to commands
as if it were real hardware. Useful for testing without actual robots.

Configuration can be loaded from:
1. Built-in default handlers (legacy mode)
2. JSON configuration files (recommended for customization)
3. Programmatically via add_command_response()
"""

import re
import time
import threading
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple, Pattern, Union
from .virtual_serial import VirtualSerialPort


class RobotModel(Enum):
    """Supported robot models."""
    MIROBOT = "mirobot"
    E4 = "e4"
    MT4 = "mt4"
    MS4220 = "ms4220"


@dataclass
class RobotState:
    """Current state of the simulated robot."""
    # Robot status
    state: str = "Idle"
    
    # Axis angles (for Mirobot: A, B, C, D, X, Y, Z; for E4/MT4: X, Y, Z, A, D)
    angle_A: float = 0.0
    angle_B: float = 0.0
    angle_C: float = 0.0
    angle_D: float = 0.0
    angle_X: float = 0.0
    angle_Y: float = 0.0
    angle_Z: float = 0.0
    
    # Cartesian coordinates
    coordinate_X: float = 150.0
    coordinate_Y: float = 0.0
    coordinate_Z: float = 200.0
    coordinate_RX: float = 0.0
    coordinate_RY: float = 0.0
    coordinate_RZ: float = 0.0
    
    # End effector state
    pump_pwm: int = 0
    valve_pwm: int = 0
    motion_mode: int = 0
    
    # GPIO state
    gpio_mode: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    gpio_output: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    gpio_enable: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    gpio_threshold: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    gpio_files: List[str] = field(default_factory=lambda: ["", "", "", ""])
    
    # Speed setting
    speed: int = 100


@dataclass
class CommandResponse:
    """Configuration for a command response."""
    pattern: str  # Regex pattern to match the command
    response: str  # Response to send (can include {var} placeholders)
    handler: Optional[Callable] = None  # Optional handler function
    delay: float = 0.0  # Optional delay before responding


class SimulatedHardware:
    """
    Base class for simulated robot hardware.
    
    This class provides the infrastructure for:
    - Creating a virtual serial port
    - Processing incoming commands
    - Sending responses
    - Simulating heartbeat messages
    
    Configuration can be loaded from:
    1. Built-in default handlers (legacy mode - default)
    2. JSON configuration files via load_config_from_json()
    3. Programmatically via add_command_response()
    """
    
    def __init__(self, model: RobotModel, address: int = -1, use_json_config: bool = False):
        """
        Initialize the simulated hardware.
        
        Args:
            model: The robot model to simulate
            address: RS485 address (-1 for UART mode)
            use_json_config: If True, load commands from JSON config file instead
                           of using built-in handlers
        """
        self.model = model
        self.address = address
        self.state = RobotState()
        self._virtual_port = VirtualSerialPort()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_interval: float = 0.0  # 0 = disabled
        self._heartbeat_message: str = ""
        self._command_responses: List[Tuple[Pattern, CommandResponse]] = []
        self._custom_handlers: Dict[str, Callable] = {}
        self._message_flag = False  # Debug printing
        self._config_loader = None  # JSON config loader
        self._firmware_version = "Robot V1.0.0"
        self._exbox_version = "EXbox V1.0.0"
        
        # Register command handlers
        if use_json_config:
            self.load_config_from_json()
        else:
            self._register_default_commands()
    
    def load_config_from_json(self, config_path: Optional[str] = None) -> None:
        """
        Load command responses from a JSON configuration file.
        
        Args:
            config_path: Path to JSON config file. If None, uses the default
                        config for this model from simulator/config/
        """
        from .config.config_loader import ResponseConfigLoader
        
        self._config_loader = ResponseConfigLoader()
        
        if config_path:
            self._config_loader.load_config(config_path)
        else:
            self._config_loader.load_default_config(self.model.value)
    
    def load_config_from_dict(self, config: Dict) -> None:
        """
        Load command responses from a configuration dictionary.
        
        Args:
            config: Configuration dictionary with 'commands', 'custom_commands',
                   and 'settings' keys
        """
        from .config.config_loader import ResponseConfigLoader
        
        self._config_loader = ResponseConfigLoader()
        self._config_loader.load_from_dict(config)
    
    def add_json_command(
        self,
        name: str,
        pattern: str,
        handler_name: Optional[str] = None,
        response: Optional[str] = None,
        description: str = ""
    ) -> None:
        """
        Add a command to the JSON config loader.
        
        This is useful for adding custom commands when using JSON configuration.
        
        Args:
            name: Command name
            pattern: Regex pattern to match
            handler_name: Name of handler function (must be registered in handlers.py)
            response: Default response if handler returns None
            description: Description of the command
        """
        if self._config_loader is None:
            from .config.config_loader import ResponseConfigLoader
            self._config_loader = ResponseConfigLoader()
        
        self._config_loader.add_command(name, pattern, handler_name, response, description)
    
    def _register_default_commands(self):
        """Register default command handlers. Override in subclasses."""
        pass
    
    def add_command_response(self, pattern: str, response: str, 
                              handler: Optional[Callable] = None,
                              delay: float = 0.0):
        """
        Add a custom command response.
        
        Args:
            pattern: Regex pattern to match the command
            response: Response string (can use {state.field} for state values)
            handler: Optional callback(command, state) -> Optional[str]
            delay: Delay before sending response
        """
        compiled = re.compile(pattern)
        cmd_response = CommandResponse(pattern, response, handler, delay)
        self._command_responses.append((compiled, cmd_response))
    
    def set_command_response(self, pattern: str, response: str):
        """
        Set/update a command response by pattern.
        
        Args:
            pattern: The pattern to update
            response: New response string
        """
        for i, (compiled, cmd_resp) in enumerate(self._command_responses):
            if cmd_resp.pattern == pattern:
                self._command_responses[i] = (
                    compiled,
                    CommandResponse(pattern, response, cmd_resp.handler, cmd_resp.delay)
                )
                return
        # Not found, add new
        self.add_command_response(pattern, response)
    
    def start(self) -> str:
        """
        Start the simulated hardware.
        
        Returns:
            Path to the virtual serial port that can be used by clients.
        """
        port_path = self._virtual_port.open()
        self._running = True
        
        # Start command processing thread
        self._thread = threading.Thread(target=self._process_commands, daemon=True)
        self._thread.start()
        
        # Start heartbeat thread if enabled
        if self._heartbeat_interval > 0:
            self._heartbeat_thread = threading.Thread(target=self._send_heartbeats, daemon=True)
            self._heartbeat_thread.start()
        
        return port_path
    
    def stop(self):
        """Stop the simulated hardware."""
        self._running = False
        
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        
        if self._heartbeat_thread is not None:
            self._heartbeat_thread.join(timeout=2.0)
            self._heartbeat_thread = None
        
        self._virtual_port.close()
    
    def set_heartbeat(self, interval: float, message: str):
        """
        Configure heartbeat messages.
        
        Args:
            interval: Interval between heartbeats in seconds (0 to disable)
            message: Heartbeat message to send
        """
        self._heartbeat_interval = interval
        self._heartbeat_message = message
        
        # If already running, start/stop heartbeat thread
        if self._running and interval > 0 and self._heartbeat_thread is None:
            self._heartbeat_thread = threading.Thread(target=self._send_heartbeats, daemon=True)
            self._heartbeat_thread.start()
    
    def set_state(self, **kwargs):
        """
        Update the robot state.
        
        Args:
            **kwargs: State fields to update (e.g., angle_X=45.0)
        """
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
    
    def message_print(self, flag: bool):
        """Enable/disable debug message printing."""
        self._message_flag = flag
    
    def _process_commands(self):
        """Main loop for processing incoming commands."""
        buffer = b""
        
        while self._running:
            try:
                # Read data from the virtual port
                data = self._virtual_port.read_from_slave(1024)
                if data:
                    buffer += data
                    
                    # Process complete lines
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        line = line.rstrip(b"\r")
                        
                        if line:
                            command = line.decode('utf-8', errors='ignore')
                            self._handle_command(command)
                else:
                    time.sleep(0.01)
            except Exception as e:
                if self._message_flag:
                    print(f"Error processing command: {e}")
                time.sleep(0.01)
    
    def _handle_command(self, command: str):
        """
        Handle an incoming command.
        
        Args:
            command: The command string
        """
        if self._message_flag:
            print(f"Simulator received: {command}")
        
        # Strip address prefix if present
        original_command = command
        if command.startswith("@"):
            # Extract address and command
            match = re.match(r"@(\d+)(.*)", command)
            if match:
                addr = int(match.group(1))
                if self.address != -1 and addr != self.address:
                    return  # Not for us
                command = match.group(2)
        
        # Try JSON config loader first if available
        if self._config_loader is not None:
            context = {
                'send_response': self._send_response,
                'firmware_version': getattr(self, '_firmware_version', 'Robot V1.0.0'),
                'exbox_version': getattr(self, '_exbox_version', 'EXbox V1.0.0'),
            }
            matched, response = self._config_loader.process_command(command, self.state, context)
            if matched and response is not None:
                self._send_response(response)
                return
            elif matched:
                # Handler was called but returned None, and no default response
                return
        
        # Fall back to legacy command responses
        for pattern, cmd_response in self._command_responses:
            match = pattern.match(command)
            if match:
                if cmd_response.delay > 0:
                    time.sleep(cmd_response.delay)
                
                response = None
                
                # Call handler if present
                if cmd_response.handler:
                    response = cmd_response.handler(command, match, self.state)
                
                # Use predefined response if handler didn't return one
                if response is None:
                    response = self._format_response(cmd_response.response)
                
                self._send_response(response)
                return
        
        # No matching command - send error
        if self._message_flag:
            print(f"No handler for command: {command}")
        self._send_response("error")
    
    def _format_response(self, template: str) -> str:
        """
        Format a response template with state values.
        
        Args:
            template: Response template with {field} placeholders
            
        Returns:
            Formatted response string
        """
        # Replace {state.field} with actual values
        def replace_state(match):
            field = match.group(1)
            if hasattr(self.state, field):
                return str(getattr(self.state, field))
            return match.group(0)
        
        return re.sub(r'\{state\.(\w+)\}', replace_state, template)
    
    def _send_response(self, response: str):
        """
        Send a response to the client.
        
        Args:
            response: Response string to send
        """
        if self._message_flag:
            print(f"Simulator sending: {response}")
        
        data = (response + "\r\n").encode('utf-8')
        self._virtual_port.write_to_slave(data)
    
    def _send_heartbeats(self):
        """Thread function for sending periodic heartbeat messages."""
        while self._running and self._heartbeat_interval > 0:
            time.sleep(self._heartbeat_interval)
            if self._running:
                message = self._format_response(self._heartbeat_message)
                self._send_response(message)
    
    @property
    def port_path(self) -> Optional[str]:
        """Get the path to the virtual serial port."""
        return self._virtual_port.port_path
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


class MirobotSimulator(SimulatedHardware):
    """Simulated Mirobot robot arm."""
    
    def __init__(self, address: int = -1, use_json_config: bool = False):
        super().__init__(RobotModel.MIROBOT, address, use_json_config)
        self._firmware_version = "Mirobot V1.0.0"
        self._exbox_version = "EXbox V1.0.0"
    
    def _register_default_commands(self):
        """Register Mirobot-specific command handlers."""
        
        # Status query
        def handle_status(cmd, match, state):
            return (f"<{state.state},"
                    f"Angle(ABCDXYZ):{state.angle_A:.1f},{state.angle_B:.1f},"
                    f"{state.angle_C:.1f},{state.angle_D:.1f},{state.angle_X:.1f},"
                    f"{state.angle_Y:.1f},{state.angle_Z:.1f},"
                    f"Cartesian coordinate(XYZ RxRyRz):{state.coordinate_X:.1f},"
                    f"{state.coordinate_Y:.1f},{state.coordinate_Z:.1f},"
                    f"{state.coordinate_RX:.1f},{state.coordinate_RY:.1f},"
                    f"{state.coordinate_RZ:.1f},"
                    f"Pump PWM:{state.pump_pwm},Valve PWM:{state.valve_pwm},"
                    f"Motion_MODE:{state.motion_mode}>")
        
        self.add_command_response(r"^\?$", "", handle_status)
        
        # Version query
        def handle_version(cmd, match, state):
            self._send_response(self._exbox_version)
            return self._firmware_version
        
        self.add_command_response(r"^\$V$", "", handle_version)
        
        # Homing command
        def handle_homing(cmd, match, state):
            state.state = "Home"
            # Reset all angles to zero
            state.angle_A = state.angle_B = state.angle_C = 0.0
            state.angle_D = state.angle_X = state.angle_Y = state.angle_Z = 0.0
            # Set default home position
            state.coordinate_X = 150.0
            state.coordinate_Y = 0.0
            state.coordinate_Z = 200.0
            state.coordinate_RX = state.coordinate_RY = state.coordinate_RZ = 0.0
            
            # Schedule state change back to Idle
            def set_idle():
                time.sleep(0.5)
                state.state = "Idle"
            threading.Thread(target=set_idle, daemon=True).start()
            
            return "ok"
        
        self.add_command_response(r"^o105=\d+$", "", handle_homing)
        self.add_command_response(r"^\$h$", "", handle_homing)
        
        # Restart command
        self.add_command_response(r"^o100$", "ok")
        
        # Stop command
        self.add_command_response(r"^o117$", "ok")
        
        # Gripper/Pump PWM control
        def handle_pwm(cmd, match, state):
            pwm_value = int(match.group(1))
            state.pump_pwm = pwm_value
            return "ok"
        
        self.add_command_response(r"^M3 S(\d+)$", "", handle_pwm)
        
        # Speed control
        def handle_speed(cmd, match, state):
            speed = int(match.group(1))
            state.speed = speed
            return "ok"
        
        self.add_command_response(r"^F(\d+)$", "", handle_speed)
        
        # Cartesian movement (M20)
        def handle_cartesian(cmd, match, state):
            state.state = "Run"
            
            # Check if incremental mode (G91) or absolute mode (G90)
            is_incremental = "G91" in cmd.upper()
            
            # Parse coordinates from command
            coords = re.findall(r"([XYZABC])([-\d.]+)", cmd)
            for axis, value in coords:
                val = float(value)
                if axis == "X":
                    state.coordinate_X = state.coordinate_X + val if is_incremental else val
                elif axis == "Y":
                    state.coordinate_Y = state.coordinate_Y + val if is_incremental else val
                elif axis == "Z":
                    state.coordinate_Z = state.coordinate_Z + val if is_incremental else val
                elif axis == "A":
                    state.coordinate_RX = state.coordinate_RX + val if is_incremental else val
                elif axis == "B":
                    state.coordinate_RY = state.coordinate_RY + val if is_incremental else val
                elif axis == "C":
                    state.coordinate_RZ = state.coordinate_RZ + val if is_incremental else val
            
            def set_idle():
                time.sleep(0.2)
                state.state = "Idle"
            threading.Thread(target=set_idle, daemon=True).start()
            
            return "ok"
        
        self.add_command_response(r"^M20.*", "", handle_cartesian)
        
        # Angle movement (M21)
        def handle_angle(cmd, match, state):
            state.state = "Run"
            
            # Check if incremental mode (G91) or absolute mode (G90)
            is_incremental = "G91" in cmd.upper()
            
            # Parse angles from command
            coords = re.findall(r"([XYZABC])([-\d.]+)", cmd)
            for axis, value in coords:
                val = float(value)
                if axis == "X":
                    state.angle_X = state.angle_X + val if is_incremental else val
                elif axis == "Y":
                    state.angle_Y = state.angle_Y + val if is_incremental else val
                elif axis == "Z":
                    state.angle_Z = state.angle_Z + val if is_incremental else val
                elif axis == "A":
                    state.angle_A = state.angle_A + val if is_incremental else val
                elif axis == "B":
                    state.angle_B = state.angle_B + val if is_incremental else val
                elif axis == "C":
                    state.angle_C = state.angle_C + val if is_incremental else val
            
            def set_idle():
                time.sleep(0.2)
                state.state = "Idle"
            threading.Thread(target=set_idle, daemon=True).start()
            
            return "ok"
        
        self.add_command_response(r"^M21.*", "", handle_angle)
        
        # Expand axis (7th axis)
        def handle_expand(cmd, match, state):
            # Check if incremental mode (G91) or absolute mode (G90)
            is_incremental = "G91" in cmd.upper()
            
            coords = re.findall(r"D([-\d.]+)", cmd)
            if coords:
                val = float(coords[0])
                state.angle_D = state.angle_D + val if is_incremental else val
            return "ok"
        
        self.add_command_response(r"^G9[01]G0[01]D.*", "", handle_expand)
        
        # GPIO mode query
        def handle_gpio_mode_query(cmd, match, state):
            modes = ",".join(str(m) for m in state.gpio_mode)
            self._send_response(modes)
            return "ok"
        
        self.add_command_response(r"^o130\?$", "", handle_gpio_mode_query)
        
        # GPIO mode set
        def handle_gpio_mode_set(cmd, match, state):
            values = match.group(1).split(",")
            for i, val in enumerate(values):
                if val and i < 4:
                    state.gpio_mode[i] = int(val)
            return "ok"
        
        self.add_command_response(r"^o130=(.*)$", "", handle_gpio_mode_set)
        
        # GPIO output/input query
        def handle_gpio_io_query(cmd, match, state):
            outputs = ",".join(str(o) for o in state.gpio_output)
            self._send_response(outputs)
            return "ok"
        
        self.add_command_response(r"^o131\?$", "", handle_gpio_io_query)
        
        # GPIO output set
        def handle_gpio_io_set(cmd, match, state):
            values = match.group(1).split(",")
            for i, val in enumerate(values):
                if val and i < 4:
                    state.gpio_output[i] = int(val)
            return "ok"
        
        self.add_command_response(r"^o131=(.*)$", "", handle_gpio_io_set)
        
        # GPIO enable query
        def handle_gpio_enable_query(cmd, match, state):
            enables = ",".join(str(e) for e in state.gpio_enable)
            self._send_response(enables)
            return "ok"
        
        self.add_command_response(r"^o132\?$", "", handle_gpio_enable_query)
        
        # GPIO enable set
        def handle_gpio_enable_set(cmd, match, state):
            values = match.group(1).split(",")
            for i, val in enumerate(values):
                if val and i < 4:
                    state.gpio_enable[i] = int(val)
            return "ok"
        
        self.add_command_response(r"^o132=(.*)$", "", handle_gpio_enable_set)
        
        # GPIO threshold query
        def handle_gpio_threshold_query(cmd, match, state):
            thresholds = ",".join(str(t) for t in state.gpio_threshold)
            self._send_response(thresholds)
            return "ok"
        
        self.add_command_response(r"^o133\?$", "", handle_gpio_threshold_query)
        
        # GPIO threshold set
        def handle_gpio_threshold_set(cmd, match, state):
            values = match.group(1).split(",")
            for i, val in enumerate(values):
                if val and i < 4:
                    state.gpio_threshold[i] = int(val)
            return "ok"
        
        self.add_command_response(r"^o133=(.*)$", "", handle_gpio_threshold_set)
        
        # GPIO file query
        def handle_gpio_file_query(cmd, match, state):
            files = ",".join(state.gpio_files)
            self._send_response(files)
            return "ok"
        
        self.add_command_response(r"^o134\?$", "", handle_gpio_file_query)
        
        # GPIO file set  
        def handle_gpio_file_set(cmd, match, state):
            values = match.group(1).split(",")
            for i, val in enumerate(values):
                if val and i < 4:
                    state.gpio_files[i] = val
            return "ok"
        
        self.add_command_response(r"^o134=(.*)$", "", handle_gpio_file_set)
        
        # Run file
        self.add_command_response(r"^o11[12].*$", "ok")
    
    def set_firmware_version(self, version: str, exbox_version: str = None):
        """
        Set the firmware version strings.
        
        Args:
            version: Robot firmware version
            exbox_version: Optional EXbox version
        """
        self._firmware_version = version
        if exbox_version:
            self._exbox_version = exbox_version


class E4Simulator(SimulatedHardware):
    """Simulated E4 robot arm (4-axis)."""
    
    def __init__(self, address: int = -1, use_json_config: bool = False):
        super().__init__(RobotModel.E4, address, use_json_config)
        self._firmware_version = "E4 V1.0.0"
        self._exbox_version = "EXbox V1.0.0"
    
    def _register_default_commands(self):
        """Register E4-specific command handlers."""
        
        # Status query (same format as Mirobot but fewer axes)
        def handle_status(cmd, match, state):
            return (f"<{state.state},"
                    f"Angle(ABCDXYZ):{state.angle_A:.1f},{state.angle_B:.1f},"
                    f"{state.angle_C:.1f},{state.angle_D:.1f},{state.angle_X:.1f},"
                    f"{state.angle_Y:.1f},{state.angle_Z:.1f},"
                    f"Cartesian coordinate(XYZ RxRyRz):{state.coordinate_X:.1f},"
                    f"{state.coordinate_Y:.1f},{state.coordinate_Z:.1f},"
                    f"{state.coordinate_RX:.1f},{state.coordinate_RY:.1f},"
                    f"{state.coordinate_RZ:.1f},"
                    f"Pump PWM:{state.pump_pwm},Valve PWM:{state.valve_pwm},"
                    f"Motion_MODE:{state.motion_mode}>")
        
        self.add_command_response(r"^\?$", "", handle_status)
        
        # Version query
        def handle_version(cmd, match, state):
            self._send_response(self._exbox_version)
            return self._firmware_version
        
        self.add_command_response(r"^\$V$", "", handle_version)
        
        # Homing command
        def handle_homing(cmd, match, state):
            state.state = "Home"
            state.angle_A = state.angle_X = state.angle_Y = state.angle_Z = 0.0
            state.coordinate_X = 150.0
            state.coordinate_Y = 0.0
            state.coordinate_Z = 200.0
            state.coordinate_RX = 0.0
            
            def set_idle():
                time.sleep(0.5)
                state.state = "Idle"
            threading.Thread(target=set_idle, daemon=True).start()
            
            return "ok"
        
        self.add_command_response(r"^o105=\d+$", "", handle_homing)
        self.add_command_response(r"^\$h$", "", handle_homing)
        
        # Common commands
        self.add_command_response(r"^o100$", "ok")  # Restart
        self.add_command_response(r"^o117$", "ok")  # Stop
        
        # PWM control with state update
        def handle_pwm(cmd, match, state):
            pwm_value = int(match.group(1))
            state.pump_pwm = pwm_value
            return "ok"
        
        self.add_command_response(r"^M3 S(\d+)$", "", handle_pwm)
        
        # Speed control with state update
        def handle_speed(cmd, match, state):
            speed = int(match.group(1))
            state.speed = speed
            return "ok"
        
        self.add_command_response(r"^F(\d+)$", "", handle_speed)
        
        # Movement commands (4-axis)
        def handle_cartesian(cmd, match, state):
            state.state = "Run"
            
            # Check if incremental mode (G91) or absolute mode (G90)
            is_incremental = "G91" in cmd.upper()
            
            coords = re.findall(r"([XYZA])([-\d.]+)", cmd)
            for axis, value in coords:
                val = float(value)
                if axis == "X":
                    state.coordinate_X = state.coordinate_X + val if is_incremental else val
                elif axis == "Y":
                    state.coordinate_Y = state.coordinate_Y + val if is_incremental else val
                elif axis == "Z":
                    state.coordinate_Z = state.coordinate_Z + val if is_incremental else val
                elif axis == "A":
                    state.coordinate_RX = state.coordinate_RX + val if is_incremental else val
            
            def set_idle():
                time.sleep(0.2)
                state.state = "Idle"
            threading.Thread(target=set_idle, daemon=True).start()
            
            return "ok"
        
        self.add_command_response(r"^M20.*", "", handle_cartesian)
        
        def handle_angle(cmd, match, state):
            state.state = "Run"
            
            # Check if incremental mode (G91) or absolute mode (G90)
            is_incremental = "G91" in cmd.upper()
            
            coords = re.findall(r"([XYZA])([-\d.]+)", cmd)
            for axis, value in coords:
                val = float(value)
                if axis == "X":
                    state.angle_X = state.angle_X + val if is_incremental else val
                elif axis == "Y":
                    state.angle_Y = state.angle_Y + val if is_incremental else val
                elif axis == "Z":
                    state.angle_Z = state.angle_Z + val if is_incremental else val
                elif axis == "A":
                    state.angle_A = state.angle_A + val if is_incremental else val
            
            def set_idle():
                time.sleep(0.2)
                state.state = "Idle"
            threading.Thread(target=set_idle, daemon=True).start()
            
            return "ok"
        
        self.add_command_response(r"^M21.*", "", handle_angle)
    
    def set_firmware_version(self, version: str, exbox_version: str = None):
        """Set the firmware version strings."""
        self._firmware_version = version
        if exbox_version:
            self._exbox_version = exbox_version


class MT4Simulator(SimulatedHardware):
    """Simulated MT4 robot arm (4-axis)."""
    
    def __init__(self, address: int = -1, use_json_config: bool = False):
        super().__init__(RobotModel.MT4, address, use_json_config)
        self._firmware_version = "MT4 V1.0.0"
        self._exbox_version = "EXbox V1.0.0"
    
    def _register_default_commands(self):
        """Register MT4-specific command handlers (similar to E4)."""
        
        # Status query
        def handle_status(cmd, match, state):
            return (f"<{state.state},"
                    f"Angle(ABCDXYZ):{state.angle_A:.1f},{state.angle_B:.1f},"
                    f"{state.angle_C:.1f},{state.angle_D:.1f},{state.angle_X:.1f},"
                    f"{state.angle_Y:.1f},{state.angle_Z:.1f},"
                    f"Cartesian coordinate(XYZ RxRyRz):{state.coordinate_X:.1f},"
                    f"{state.coordinate_Y:.1f},{state.coordinate_Z:.1f},"
                    f"{state.coordinate_RX:.1f},{state.coordinate_RY:.1f},"
                    f"{state.coordinate_RZ:.1f},"
                    f"Pump PWM:{state.pump_pwm},Valve PWM:{state.valve_pwm},"
                    f"Motion_MODE:{state.motion_mode}>")
        
        self.add_command_response(r"^\?$", "", handle_status)
        
        # Version query
        def handle_version(cmd, match, state):
            self._send_response(self._exbox_version)
            return self._firmware_version
        
        self.add_command_response(r"^\$V$", "", handle_version)
        
        # Homing command
        def handle_homing(cmd, match, state):
            state.state = "Home"
            state.angle_A = state.angle_X = state.angle_Y = state.angle_Z = 0.0
            state.coordinate_X = 150.0
            state.coordinate_Y = 0.0
            state.coordinate_Z = 200.0
            state.coordinate_RX = 0.0
            
            def set_idle():
                time.sleep(0.5)
                state.state = "Idle"
            threading.Thread(target=set_idle, daemon=True).start()
            
            return "ok"
        
        self.add_command_response(r"^o105=\d+$", "", handle_homing)
        self.add_command_response(r"^\$h$", "", handle_homing)
        
        # Common commands
        self.add_command_response(r"^o100$", "ok")  # Restart
        self.add_command_response(r"^o117$", "ok")  # Stop
        
        # PWM control with state update
        def handle_pwm(cmd, match, state):
            pwm_value = int(match.group(1))
            state.pump_pwm = pwm_value
            return "ok"
        
        self.add_command_response(r"^M3 S(\d+)$", "", handle_pwm)
        
        # Speed control with state update
        def handle_speed(cmd, match, state):
            speed = int(match.group(1))
            state.speed = speed
            return "ok"
        
        self.add_command_response(r"^F(\d+)$", "", handle_speed)
        
        # Movement commands
        def handle_cartesian(cmd, match, state):
            state.state = "Run"
            
            # Check if incremental mode (G91) or absolute mode (G90)
            is_incremental = "G91" in cmd.upper()
            
            coords = re.findall(r"([XYZA])([-\d.]+)", cmd)
            for axis, value in coords:
                val = float(value)
                if axis == "X":
                    state.coordinate_X = state.coordinate_X + val if is_incremental else val
                elif axis == "Y":
                    state.coordinate_Y = state.coordinate_Y + val if is_incremental else val
                elif axis == "Z":
                    state.coordinate_Z = state.coordinate_Z + val if is_incremental else val
                elif axis == "A":
                    state.coordinate_RX = state.coordinate_RX + val if is_incremental else val
            
            def set_idle():
                time.sleep(0.2)
                state.state = "Idle"
            threading.Thread(target=set_idle, daemon=True).start()
            
            return "ok"
        
        self.add_command_response(r"^M20.*", "", handle_cartesian)
        
        def handle_angle(cmd, match, state):
            state.state = "Run"
            
            # Check if incremental mode (G91) or absolute mode (G90)
            is_incremental = "G91" in cmd.upper()
            
            coords = re.findall(r"([XYZA])([-\d.]+)", cmd)
            for axis, value in coords:
                val = float(value)
                if axis == "X":
                    state.angle_X = state.angle_X + val if is_incremental else val
                elif axis == "Y":
                    state.angle_Y = state.angle_Y + val if is_incremental else val
                elif axis == "Z":
                    state.angle_Z = state.angle_Z + val if is_incremental else val
                elif axis == "A":
                    state.angle_A = state.angle_A + val if is_incremental else val
            
            def set_idle():
                time.sleep(0.2)
                state.state = "Idle"
            threading.Thread(target=set_idle, daemon=True).start()
            
            return "ok"
        
        self.add_command_response(r"^M21.*", "", handle_angle)
    
    def set_firmware_version(self, version: str, exbox_version: str = None):
        """Set the firmware version strings."""
        self._firmware_version = version
        if exbox_version:
            self._exbox_version = exbox_version


class MS4220Simulator(SimulatedHardware):
    """Simulated MS4220 stepper motor controller."""
    
    def __init__(self, address: int = 10, use_json_config: bool = False):
        super().__init__(RobotModel.MS4220, address, use_json_config)
        self._motor_speed = 0
        self._motor_position = 0
    
    def _register_default_commands(self):
        """Register MS4220-specific command handlers."""
        
        # Speed control
        def handle_speed(cmd, match, state):
            speed_match = re.search(r"F([-\d]+)", cmd)
            if speed_match:
                self._motor_speed = int(speed_match.group(1))
            return "ok"
        
        self.add_command_response(r"^G6 F[-\d]+$", "", handle_speed)
        
        # Position control
        def handle_position(cmd, match, state):
            pos_match = re.search(r"P([-\d]+)", cmd)
            if pos_match:
                self._motor_position = int(pos_match.group(1))
            return "ok"
        
        self.add_command_response(r"^G6 P[-\d]+$", "", handle_position)
        
        # Stop command
        self.add_command_response(r"^G6 S0$", "ok")
        
        # Status query
        def handle_status(cmd, match, state):
            return f"Speed:{self._motor_speed},Position:{self._motor_position}"
        
        self.add_command_response(r"^\?$", "", handle_status)
    
    @property
    def motor_speed(self) -> int:
        """Get the current motor speed setting."""
        return self._motor_speed
    
    @property
    def motor_position(self) -> int:
        """Get the current motor position."""
        return self._motor_position


def create_simulator(model: str, address: int = -1) -> SimulatedHardware:
    """
    Factory function to create a simulator for the specified model.
    
    Args:
        model: Robot model name ("mirobot", "e4", "mt4", "ms4220")
        address: RS485 address (-1 for UART mode)
        
    Returns:
        A SimulatedHardware instance for the specified model
        
    Raises:
        ValueError: If the model is not recognized
    """
    model_lower = model.lower()
    
    if model_lower == "mirobot":
        return MirobotSimulator(address)
    elif model_lower == "e4":
        return E4Simulator(address)
    elif model_lower == "mt4":
        return MT4Simulator(address)
    elif model_lower == "ms4220":
        return MS4220Simulator(address if address != -1 else 10)
    else:
        raise ValueError(f"Unknown model: {model}. Supported models: mirobot, e4, mt4, ms4220")
