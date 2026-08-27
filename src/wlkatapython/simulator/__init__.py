"""
Simulated hardware module for WLKATA robot testing.

This module provides a simulated serial connection that can be used to test
the robot control library without requiring actual hardware.

Supported models:
- Mirobot: 6-axis robot arm
- E4: 4-axis robot arm  
- MT4: 4-axis robot arm
- MS4220: Stepper motor controller

Usage Example:
    
    from wlkatapython.simulator import MirobotSimulator
    from wlkatapython.simulator.virtual_serial import MockSerial
    
    # Create and start the simulator
    sim = MirobotSimulator()
    port_path = sim.start()
    
    # Connect using MockSerial (or real pyserial if on Linux)
    serial = MockSerial(port_path)
    
    # Send commands
    serial.write(b"?\\r\\n")
    response = serial.readline()
    print(response)
    
    # Clean up
    serial.close()
    sim.stop()

See tests/test_simulator.py for more examples.
"""

from .simulated_hardware import (
    SimulatedHardware,
    MirobotSimulator,
    E4Simulator,
    MT4Simulator,
    MS4220Simulator,
    RobotModel,
    RobotState,
    create_simulator,
)

from .virtual_serial import VirtualSerialPort, MockSerial

from .response_config import (
    ResponsePreset,
    RESPONSE_PRESETS,
    get_preset,
    list_presets,
    apply_preset,
    create_custom_preset,
    STATE_SCENARIOS,
    apply_state_scenario,
)

from .kinematics import (
    MirobotKinematics,
    apply_fk_to_state,
    apply_ik_to_state,
)

__all__ = [
    # Hardware simulators
    "SimulatedHardware",
    "MirobotSimulator",
    "E4Simulator", 
    "MT4Simulator",
    "MS4220Simulator",
    "RobotModel",
    "RobotState",
    "create_simulator",
    # Virtual serial
    "VirtualSerialPort",
    "MockSerial",
    # Response configuration
    "ResponsePreset",
    "RESPONSE_PRESETS",
    "get_preset",
    "list_presets",
    "apply_preset",
    "create_custom_preset",
    "STATE_SCENARIOS",
    "apply_state_scenario",
    # Kinematics
    "MirobotKinematics",
    "apply_fk_to_state",
    "apply_ik_to_state",
]
