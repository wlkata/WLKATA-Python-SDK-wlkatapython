"""
Response configuration for different robot models.

This module provides predefined response configurations that can be loaded
into simulators to customize their behavior for different firmware versions
or testing scenarios.
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ResponsePreset:
    """A preset configuration for simulator responses."""
    name: str
    description: str
    model: str
    firmware_version: str
    exbox_version: str
    commands: Dict[str, str]  # pattern -> response
    initial_state: Dict[str, Any]  # state field -> value


# Predefined response presets
RESPONSE_PRESETS: Dict[str, ResponsePreset] = {
    # Mirobot presets
    "mirobot_v1": ResponsePreset(
        name="mirobot_v1",
        description="Standard Mirobot V1.x firmware responses",
        model="mirobot",
        firmware_version="Mirobot V1.0.0",
        exbox_version="EXbox V1.0.0",
        commands={},
        initial_state={
            "coordinate_X": 150.0,
            "coordinate_Y": 0.0,
            "coordinate_Z": 200.0,
        }
    ),
    
    "mirobot_v2": ResponsePreset(
        name="mirobot_v2",
        description="Mirobot V2.x firmware responses",
        model="mirobot",
        firmware_version="Mirobot V2.0.0",
        exbox_version="EXbox V2.0.0",
        commands={},
        initial_state={
            "coordinate_X": 150.0,
            "coordinate_Y": 0.0,
            "coordinate_Z": 200.0,
        }
    ),
    
    # E4 presets
    "e4_standard": ResponsePreset(
        name="e4_standard",
        description="Standard E4 robot firmware responses",
        model="e4",
        firmware_version="E4 V1.0.0",
        exbox_version="EXbox V1.0.0",
        commands={},
        initial_state={
            "coordinate_X": 150.0,
            "coordinate_Y": 0.0,
            "coordinate_Z": 200.0,
            "coordinate_RX": 0.0,
        }
    ),
    
    # MT4 presets
    "mt4_standard": ResponsePreset(
        name="mt4_standard",
        description="Standard MT4 robot firmware responses",
        model="mt4",
        firmware_version="MT4 V1.0.0",
        exbox_version="EXbox V1.0.0",
        commands={},
        initial_state={
            "coordinate_X": 150.0,
            "coordinate_Y": 0.0,
            "coordinate_Z": 200.0,
        }
    ),
    
    # MS4220 presets
    "ms4220_standard": ResponsePreset(
        name="ms4220_standard",
        description="Standard MS4220 stepper controller responses",
        model="ms4220",
        firmware_version="MS4220 V1.0.0",
        exbox_version="",
        commands={},
        initial_state={}
    ),
    
    # Error simulation presets
    "mirobot_slow": ResponsePreset(
        name="mirobot_slow",
        description="Mirobot with slow responses for timeout testing",
        model="mirobot",
        firmware_version="Mirobot V1.0.0",
        exbox_version="EXbox V1.0.0",
        commands={},
        initial_state={}
    ),
    
    "mirobot_error_prone": ResponsePreset(
        name="mirobot_error_prone",
        description="Mirobot that sometimes returns errors",
        model="mirobot",
        firmware_version="Mirobot V1.0.0",
        exbox_version="EXbox V1.0.0",
        commands={
            r"^o111.*$": "error",  # File run always fails
        },
        initial_state={}
    ),
}


def get_preset(name: str) -> ResponsePreset:
    """
    Get a response preset by name.
    
    Args:
        name: Preset name
        
    Returns:
        The ResponsePreset configuration
        
    Raises:
        KeyError: If preset not found
    """
    if name not in RESPONSE_PRESETS:
        raise KeyError(f"Preset '{name}' not found. Available: {list(RESPONSE_PRESETS.keys())}")
    return RESPONSE_PRESETS[name]


def list_presets() -> List[str]:
    """Get list of available preset names."""
    return list(RESPONSE_PRESETS.keys())


def apply_preset(simulator, preset_name: str):
    """
    Apply a response preset to a simulator.
    
    Args:
        simulator: The simulator instance to configure
        preset_name: Name of the preset to apply
    """
    preset = get_preset(preset_name)
    
    # Set firmware version if applicable
    if hasattr(simulator, 'set_firmware_version'):
        simulator.set_firmware_version(preset.firmware_version, preset.exbox_version)
    
    # Apply custom commands
    for pattern, response in preset.commands.items():
        simulator.set_command_response(pattern, response)
    
    # Apply initial state
    for field, value in preset.initial_state.items():
        if hasattr(simulator.state, field):
            setattr(simulator.state, field, value)


def create_custom_preset(
    name: str,
    base_preset: str = "mirobot_v1",
    **overrides
) -> ResponsePreset:
    """
    Create a custom preset based on an existing one.
    
    Args:
        name: Name for the new preset
        base_preset: Name of preset to use as base
        **overrides: Fields to override (description, firmware_version, commands, etc.)
        
    Returns:
        A new ResponsePreset instance
    """
    base = get_preset(base_preset)
    
    return ResponsePreset(
        name=name,
        description=overrides.get('description', base.description),
        model=overrides.get('model', base.model),
        firmware_version=overrides.get('firmware_version', base.firmware_version),
        exbox_version=overrides.get('exbox_version', base.exbox_version),
        commands={**base.commands, **overrides.get('commands', {})},
        initial_state={**base.initial_state, **overrides.get('initial_state', {})}
    )


# Robot state scenarios for testing
STATE_SCENARIOS = {
    "home_position": {
        "state": "Idle",
        "angle_A": 0.0, "angle_B": 0.0, "angle_C": 0.0,
        "angle_D": 0.0, "angle_X": 0.0, "angle_Y": 0.0, "angle_Z": 0.0,
        "coordinate_X": 150.0, "coordinate_Y": 0.0, "coordinate_Z": 200.0,
        "coordinate_RX": 0.0, "coordinate_RY": 0.0, "coordinate_RZ": 0.0,
    },
    
    "extended_position": {
        "state": "Idle",
        "angle_A": 45.0, "angle_B": 30.0, "angle_C": -15.0,
        "angle_D": 0.0, "angle_X": 45.0, "angle_Y": 30.0, "angle_Z": -15.0,
        "coordinate_X": 200.0, "coordinate_Y": 100.0, "coordinate_Z": 150.0,
        "coordinate_RX": 45.0, "coordinate_RY": 0.0, "coordinate_RZ": 30.0,
    },
    
    "pump_active": {
        "state": "Idle",
        "pump_pwm": 1000,
        "valve_pwm": 0,
    },
    
    "gripper_active": {
        "state": "Idle",
        "pump_pwm": 40,
        "valve_pwm": 0,
    },
    
    "running": {
        "state": "Run",
    },
    
    "homing": {
        "state": "Home",
    },
    
    "alarm": {
        "state": "Alarm",
    },
}


def apply_state_scenario(simulator, scenario_name: str):
    """
    Apply a predefined state scenario to a simulator.
    
    Args:
        simulator: The simulator instance
        scenario_name: Name of the scenario to apply
    """
    if scenario_name not in STATE_SCENARIOS:
        raise KeyError(f"Scenario '{scenario_name}' not found. Available: {list(STATE_SCENARIOS.keys())}")
    
    scenario = STATE_SCENARIOS[scenario_name]
    simulator.set_state(**scenario)
