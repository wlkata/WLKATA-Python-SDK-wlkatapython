# WLKATA Robot Simulator

This module provides simulated hardware for testing the WLKATA robot control library without requiring actual hardware.

## Supported Models

- **Mirobot**: 6-axis robot arm
- **E4**: 4-axis robot arm
- **MT4**: 4-axis robot arm
- **MS4220**: Stepper motor controller

## Quick Start

### Basic Usage

```python
from wlkatapython.simulator import MirobotSimulator
from wlkatapython.simulator.virtual_serial import MockSerial

# Create and start a Mirobot simulator
sim = MirobotSimulator()
port_path = sim.start()

# Connect to the simulator
serial = MockSerial(port_path, timeout=2.0)

# Send commands
serial.write(b"?\r\n")  # Status query
response = serial.readline()
print(response.decode())

# Clean up
serial.close()
sim.stop()
```

### Using Context Manager

```python
from wlkatapython.simulator import MirobotSimulator
from wlkatapython.simulator.virtual_serial import MockSerial

with MirobotSimulator() as sim:
    serial = MockSerial(sim.port_path)
    serial.write(b"o105=8\r\n")  # Homing
    print(serial.readline().decode())
    serial.close()
```

### With the Actual Library

```python
from wlkatapython.simulator import MirobotSimulator
from wlkatapython.simulator.virtual_serial import MockSerial
from wlkatapython import Mirobot_UART

# Create simulator
sim = MirobotSimulator()
port_path = sim.start()

# Use MockSerial instead of pyserial
mock_serial = MockSerial(port_path, timeout=2.0)

# Initialize the real Mirobot class
mirobot = Mirobot_UART()
mirobot.init(mock_serial, -1)

# Test commands
mirobot.homing()
mirobot.writeAngle(0, 45, 30, 0, 0, 0, 0)

# Check simulator state
print(f"Current angles: X={sim.state.angle_X}, Y={sim.state.angle_Y}")

mock_serial.close()
sim.stop()
```

## Creating Different Robot Simulators

### Factory Function

```python
from wlkatapython.simulator import create_simulator

# Create by model name
mirobot = create_simulator("mirobot")
e4 = create_simulator("e4")
mt4 = create_simulator("mt4")
ms4220 = create_simulator("ms4220", address=10)
```

### Direct Instantiation

```python
from wlkatapython.simulator import MirobotSimulator, E4Simulator, MT4Simulator, MS4220Simulator

# With RS485 addressing
sim = MirobotSimulator(address=5)  # RS485 address 5
port = sim.start()

# Commands must be prefixed with address
serial.write(b"@5?\r\n")  # Query status for address 5
```

## Customizing Responses

### Using JSON Configuration (Recommended)

The simulator supports JSON-based configuration for defining command responses. This separates 
the command patterns from the handler logic and makes it easy to add custom commands.

```python
from wlkatapython.simulator import MirobotSimulator

# Use JSON configuration from the default config file
sim = MirobotSimulator(use_json_config=True)
port = sim.start()

# The simulator will now respond to commands defined in:
# src/wlkatapython/simulator/config/mirobot_responses.json
```

#### Adding Custom Commands via JSON

Edit `src/wlkatapython/simulator/config/mirobot_responses.json` to add custom commands:

```json
{
  "custom_commands": [
    {
      "name": "my_command",
      "pattern": "^\\$M$",
      "handler": null,
      "response": "ok",
      "description": "My custom command"
    },
    {
      "name": "position_query",
      "pattern": "^\\$P$",
      "handler": "handle_get_position",
      "response": null,
      "description": "Query position"
    }
  ]
}
```

#### Creating Custom Handlers

Define handler functions in `src/wlkatapython/simulator/config/handlers.py`:

```python
def handle_my_custom_command(command: str, match: Match, state: Any, context: Dict) -> str:
    """
    Handle my custom command.
    
    Args:
        command: The full command string
        match: The regex match object
        state: The robot state (can be modified)
        context: Additional context (send_response callback, versions)
    
    Returns:
        Response string, or None to use default from JSON
    """
    state.pump_pwm = 999
    return "custom_ok"

# Register in HANDLER_REGISTRY
HANDLER_REGISTRY["handle_my_custom_command"] = handle_my_custom_command
```

#### Loading Custom Configuration

```python
from wlkatapython.simulator import MirobotSimulator

# Load from a custom JSON file
sim = MirobotSimulator()
sim.load_config_from_json("/path/to/my_config.json")

# Or load from a dictionary
config = {
    "commands": [
        {
            "name": "test",
            "pattern": "^TEST$",
            "handler": None,
            "response": "test_ok"
        }
    ],
    "custom_commands": [],
    "settings": {}
}
sim.load_config_from_dict(config)

# Or add commands programmatically
sim.add_json_command(
    name="dynamic",
    pattern="^DYNAMIC (\\w+)$",
    handler_name="handle_echo",
    response="dynamic_ok"
)
```

### Adding Custom Commands (Legacy)

```python
from wlkatapython.simulator import MirobotSimulator

sim = MirobotSimulator()

# Add a custom command response
sim.add_command_response(
    r"^CUSTOM_CMD$",  # Regex pattern
    "custom_response"  # Response to send
)

# Add with a handler function
def my_handler(cmd, match, state):
    state.pump_pwm = 999
    return "ok"

sim.add_command_response(r"^MY_CMD$", "", my_handler)
```

### Modifying Robot State

```python
sim = MirobotSimulator()
sim.start()

# Set individual state values
sim.set_state(
    angle_X=45.0,
    angle_Y=30.0,
    coordinate_X=200.0,
    state="Running"
)

# Or access directly
sim.state.pump_pwm = 500
```

### Using Presets

```python
from wlkatapython.simulator import MirobotSimulator, apply_preset, apply_state_scenario

sim = MirobotSimulator()

# Apply a firmware preset
apply_preset(sim, "mirobot_v2")

# Apply a state scenario
apply_state_scenario(sim, "extended_position")
```

## Heartbeat Messages

Configure periodic heartbeat messages:

```python
sim = MirobotSimulator()

# Send a heartbeat every 1 second
sim.set_heartbeat(1.0, "heartbeat:{state.state}")

sim.start()
```

## Debug Output

Enable debug message printing:

```python
sim = MirobotSimulator()
sim.message_print(True)  # Enable debug output
sim.start()
```

## Virtual Serial Port

On Linux, the simulator creates a real PTY (pseudo-terminal) pair at `/dev/pts/N`. 
This means you can use the standard `pyserial` library directly:

```python
import serial  # pyserial

sim = MirobotSimulator()
port_path = sim.start()

# Use pyserial directly on Linux
ser = serial.Serial(port_path, 115200, timeout=1.0)
ser.write(b"?\r\n")
print(ser.readline())
ser.close()

sim.stop()
```

On other platforms, use the provided `MockSerial` class for compatibility.

## Available Commands

### Mirobot Commands

| Command | Description | Example |
|---------|-------------|---------|
| `?` | Status query | `?` |
| `$V` | Version query | `$V` |
| `o105=N` | Homing (mode N) | `o105=8` |
| `o100` | Restart | `o100` |
| `o117` | Stop | `o117` |
| `M3 SN` | PWM control | `M3 S500` |
| `FN` | Speed control | `F80` |
| `M21G9xG0yX...` | Angle movement | `M21G90G00X45Y30Z0A0B0C0` |
| `M20G9xG0yX...` | Cartesian movement | `M20G90G01X100Y50Z150A0B0C0` |

### GPIO Commands (Mirobot)

| Command | Description |
|---------|-------------|
| `o130?` | Query GPIO mode |
| `o130=a,b,c,d` | Set GPIO mode |
| `o131?` | Query GPIO output |
| `o131=a,b,c,d` | Set GPIO output |
| `o132?` | Query GPIO enable |
| `o132=a,b,c,d` | Set GPIO enable |
| `o133?` | Query GPIO threshold |
| `o133=a,b,c,d` | Set GPIO threshold |
| `o134?` | Query GPIO trigger file |
| `o134=a,b,c,d` | Set GPIO trigger file |

## Running Tests

```bash
# From the project root (package on PYTHONPATH via pytest.ini)
python -m pytest tests/test_simulator.py -v
```

## File Structure

```
src/wlkatapython/simulator/
├── __init__.py           # Public API
├── simulated_hardware.py # Simulator implementations
├── virtual_serial.py     # Virtual serial port
├── response_config.py    # Response presets
├── config/               # JSON configuration
│   ├── __init__.py       # Config module init
│   ├── config_loader.py  # JSON config loader
│   ├── handlers.py       # Handler functions
│   ├── base_responses.json     # Base config (shared by all)
│   ├── mirobot_responses.json  # Mirobot config (6-axis)
│   ├── e4_responses.json       # E4 config (4-axis)
│   ├── mt4_responses.json      # MT4 config (4-axis)
│   └── ms4220_responses.json   # MS4220 config (stepper)
└── README.md             # This file
```

## JSON Configuration File Format

### Configuration Inheritance

The configuration system supports inheritance, allowing models to share common commands
while overriding specific handlers.

```
base_responses.json          <- Common commands for all robot arms
    ├── mirobot_responses.json   <- Extends base, adds GPIO, uses 6-axis handlers
    ├── e4_responses.json        <- Extends base, uses 4-axis handlers
    └── mt4_responses.json       <- Extends base, shares E4's handlers

ms4220_responses.json        <- Independent config (stepper motor, no inheritance)
```

To extend from base, set the `_extends` field:

```json
{
  "_extends": "base",
  "commands": [
    {
      "name": "status_query",
      "handler": "handle_e4_status_query"
    }
  ]
}
```

### Overriding Commands

When a model config has a command with the same name as the base, it overrides:

```json
{
  "_extends": "base",
  "commands": [
    {
      "name": "status_query",
      "handler": "handle_mirobot_status_query"
    }
  ]
}
```

### Disabling Commands

To mark a command as unsupported for a specific model, set `enabled` to `false`:

```json
{
  "_extends": "base",
  "commands": [
    {
      "name": "expand_axis",
      "pattern": "^G9[01]G0[01]D.*",
      "enabled": false,
      "description": "Not supported on this model"
    }
  ]
}
```

### commands

Standard commands for the robot model:

```json
{
  "commands": [
    {
      "name": "status_query",
      "pattern": "^\\?$",
      "handler": "handle_status_query",
      "response": null,
      "description": "Query robot status"
    }
  ]
}
```

### custom_commands

Custom/extended commands not in the original protocol:

```json
{
  "custom_commands": [
    {
      "name": "my_command",
      "pattern": "^\\$M$",
      "handler": null,
      "response": "ok",
      "description": "Custom command"
    }
  ]
}
```

### settings

Configuration settings:

```json
{
  "settings": {
    "unknown_command_response": "error",
    "command_delay_ms": 0,
    "case_sensitive": false
  }
}
```

**Note:** Commands are case-insensitive by default. Both `$V` and `$v` will match.

### Handler Function Signature

All handler functions must have this signature:

```python
def my_handler(
    command: str,      # Full command string
    match: re.Match,   # Regex match object
    state: RobotState, # Robot state (mutable)
    context: dict      # Context with 'send_response', 'firmware_version', etc.
) -> Optional[str]:
    """
    Returns:
        str: Response to send
        None: Use default response from JSON config
    """
    pass
```

### Available Model-Specific Handlers

| Handler Name | Model | Description |
|-------------|-------|-------------|
| `handle_mirobot_status_query` | Mirobot | 6-axis status response |
| `handle_e4_status_query` | E4/MT4 | 4-axis status response |
| `handle_e4_homing` | E4/MT4 | 4-axis homing |
| `handle_e4_angle_movement` | E4/MT4 | 4-axis angle movement |
| `handle_e4_cartesian_movement` | E4/MT4 | 4-axis Cartesian movement |
| `handle_ms4220_status_query` | MS4220 | Motor status response |
| `handle_ms4220_speed` | MS4220 | Set motor speed |
| `handle_ms4220_position` | MS4220 | Absolute position move |
| `handle_ms4220_relative` | MS4220 | Relative position move |
| `handle_ms4220_home` | MS4220 | Home motor |
