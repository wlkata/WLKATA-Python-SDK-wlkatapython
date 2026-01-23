"""
Handler functions for simulated robot commands.

Each handler function takes the following parameters:
    - command: str - The full command string received
    - match: re.Match - The regex match object
    - state: RobotState - The current robot state (can be modified)
    - context: dict - Additional context (e.g., firmware version)
    
Returns:
    - str or None: Response message. If None, uses the default from JSON config.

Handler functions are registered by name in the JSON configuration file.
"""

import re
import time
import threading
from typing import Optional, Any, Dict
from re import Match


def handle_status_query(command: str, match: Match, state: Any, context: Dict) -> str:
    """
    Handle status query command (?).
    Returns full robot status in the expected format.
    """
    return (
        f"<{state.state},"
        f"Angle(ABCDXYZ):{state.angle_A:.1f},{state.angle_B:.1f},"
        f"{state.angle_C:.1f},{state.angle_D:.1f},{state.angle_X:.1f},"
        f"{state.angle_Y:.1f},{state.angle_Z:.1f},"
        f"Cartesian coordinate(XYZ RxRyRz):{state.coordinate_X:.1f},"
        f"{state.coordinate_Y:.1f},{state.coordinate_Z:.1f},"
        f"{state.coordinate_RX:.1f},{state.coordinate_RY:.1f},"
        f"{state.coordinate_RZ:.1f},"
        f"Pump PWM:{state.pump_pwm},Valve PWM:{state.valve_pwm},"
        f"Motion_MODE:{state.motion_mode}>"
    )


def handle_version_query(command: str, match: Match, state: Any, context: Dict) -> str:
    """
    Handle version query command ($V).
    Returns firmware version info (sends two lines).
    """
    send_response = context.get('send_response')
    exbox_version = context.get('exbox_version', 'EXbox V1.0.0')
    firmware_version = context.get('firmware_version', 'Mirobot V1.0.0')
    
    # Send EXbox version first
    if send_response:
        send_response(exbox_version)
    
    # Return firmware version as the main response
    return firmware_version


def handle_homing(command: str, match: Match, state: Any, context: Dict) -> Optional[str]:
    """
    Handle homing command (o105=N or $h).
    Resets all angles to zero and sets home position.
    """
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


def handle_pwm_control(command: str, match: Match, state: Any, context: Dict) -> Optional[str]:
    """
    Handle PWM control command (M3 SN).
    Sets the pump/gripper PWM value.
    """
    pwm_value = int(match.group(1))
    state.pump_pwm = pwm_value
    return "ok"


def handle_speed_control(command: str, match: Match, state: Any, context: Dict) -> Optional[str]:
    """
    Handle speed control command (FN).
    Sets the robot speed (0-100).
    """
    speed = int(match.group(1))
    state.speed = speed
    return "ok"


def handle_cartesian_movement(command: str, match: Match, state: Any, context: Dict) -> Optional[str]:
    """
    Handle Cartesian movement command (M20...).
    Supports both absolute (G90) and incremental (G91) modes.
    """
    state.state = "Run"
    
    # Check if incremental mode (G91) or absolute mode (G90)
    is_incremental = "G91" in command.upper()
    
    # Parse coordinates from command (case-insensitive)
    coords = re.findall(r"([XYZABC])([-\d.]+)", command, re.IGNORECASE)
    for axis, value in coords:
        val = float(value)
        axis = axis.upper()  # Normalize to uppercase
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
    
    # Schedule state change back to Idle
    def set_idle():
        time.sleep(0.2)
        state.state = "Idle"
    threading.Thread(target=set_idle, daemon=True).start()
    
    return "ok"


def handle_angle_movement(command: str, match: Match, state: Any, context: Dict) -> Optional[str]:
    """
    Handle angle/joint movement command (M21...).
    Supports both absolute (G90) and incremental (G91) modes.
    """
    state.state = "Run"
    
    # Check if incremental mode (G91) or absolute mode (G90)
    is_incremental = "G91" in command.upper()
    
    # Parse angles from command (case-insensitive)
    coords = re.findall(r"([XYZABC])([-\d.]+)", command, re.IGNORECASE)
    for axis, value in coords:
        val = float(value)
        axis = axis.upper()  # Normalize to uppercase
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
    
    # Schedule state change back to Idle
    def set_idle():
        time.sleep(0.2)
        state.state = "Idle"
    threading.Thread(target=set_idle, daemon=True).start()
    
    return "ok"


def handle_expand_axis(command: str, match: Match, state: Any, context: Dict) -> Optional[str]:
    """
    Handle 7th axis (expand/rail) movement.
    Supports both absolute (G90) and incremental (G91) modes.
    """
    # Check if incremental mode (G91) or absolute mode (G90)
    is_incremental = "G91" in command.upper()
    
    # Case-insensitive matching for D axis
    coords = re.findall(r"D([-\d.]+)", command, re.IGNORECASE)
    if coords:
        val = float(coords[0])
        state.angle_D = state.angle_D + val if is_incremental else val
    
    return "ok"


# ============================================================================
# GPIO Handlers
# ============================================================================

def handle_gpio_mode_query(command: str, match: Match, state: Any, context: Dict) -> str:
    """Handle GPIO mode query (o130?)."""
    send_response = context.get('send_response')
    modes = ",".join(str(m) for m in state.gpio_mode)
    if send_response:
        send_response(modes)
    return "ok"


def handle_gpio_mode_set(command: str, match: Match, state: Any, context: Dict) -> Optional[str]:
    """Handle GPIO mode set (o130=a,b,c,d)."""
    values = match.group(1).split(",")
    for i, val in enumerate(values):
        if val and i < 4:
            state.gpio_mode[i] = int(val)
    return "ok"


def handle_gpio_output_query(command: str, match: Match, state: Any, context: Dict) -> str:
    """Handle GPIO output query (o131?)."""
    send_response = context.get('send_response')
    outputs = ",".join(str(o) for o in state.gpio_output)
    if send_response:
        send_response(outputs)
    return "ok"


def handle_gpio_output_set(command: str, match: Match, state: Any, context: Dict) -> Optional[str]:
    """Handle GPIO output set (o131=a,b,c,d)."""
    values = match.group(1).split(",")
    for i, val in enumerate(values):
        if val and i < 4:
            state.gpio_output[i] = int(val)
    return "ok"


def handle_gpio_enable_query(command: str, match: Match, state: Any, context: Dict) -> str:
    """Handle GPIO enable query (o132?)."""
    send_response = context.get('send_response')
    enables = ",".join(str(e) for e in state.gpio_enable)
    if send_response:
        send_response(enables)
    return "ok"


def handle_gpio_enable_set(command: str, match: Match, state: Any, context: Dict) -> Optional[str]:
    """Handle GPIO enable set (o132=a,b,c,d)."""
    values = match.group(1).split(",")
    for i, val in enumerate(values):
        if val and i < 4:
            state.gpio_enable[i] = int(val)
    return "ok"


def handle_gpio_threshold_query(command: str, match: Match, state: Any, context: Dict) -> str:
    """Handle GPIO threshold query (o133?)."""
    send_response = context.get('send_response')
    thresholds = ",".join(str(t) for t in state.gpio_threshold)
    if send_response:
        send_response(thresholds)
    return "ok"


def handle_gpio_threshold_set(command: str, match: Match, state: Any, context: Dict) -> Optional[str]:
    """Handle GPIO threshold set (o133=a,b,c,d)."""
    values = match.group(1).split(",")
    for i, val in enumerate(values):
        if val and i < 4:
            state.gpio_threshold[i] = int(val)
    return "ok"


def handle_gpio_file_query(command: str, match: Match, state: Any, context: Dict) -> str:
    """Handle GPIO file query (o134?)."""
    send_response = context.get('send_response')
    files = ",".join(state.gpio_files)
    if send_response:
        send_response(files)
    return "ok"


def handle_gpio_file_set(command: str, match: Match, state: Any, context: Dict) -> Optional[str]:
    """Handle GPIO file set (o134=a,b,c,d)."""
    values = match.group(1).split(",")
    for i, val in enumerate(values):
        if i < 4:
            state.gpio_files[i] = val
    return "ok"


# ============================================================================
# Mirobot-Specific Handlers (6-axis)
# ============================================================================

def handle_mirobot_status_query(command: str, match: Match, state: Any, context: Dict) -> str:
    """
    Mirobot-specific status query handler (6-axis).
    Returns full robot status with all 6 axes.
    """
    return (
        f"<{state.state},"
        f"Angle(ABCDXYZ):{state.angle_A:.1f},{state.angle_B:.1f},"
        f"{state.angle_C:.1f},{state.angle_D:.1f},{state.angle_X:.1f},"
        f"{state.angle_Y:.1f},{state.angle_Z:.1f},"
        f"Cartesian coordinate(XYZ RxRyRz):{state.coordinate_X:.1f},"
        f"{state.coordinate_Y:.1f},{state.coordinate_Z:.1f},"
        f"{state.coordinate_RX:.1f},{state.coordinate_RY:.1f},"
        f"{state.coordinate_RZ:.1f},"
        f"Pump PWM:{state.pump_pwm},Valve PWM:{state.valve_pwm},"
        f"Motion_MODE:{state.motion_mode}>"
    )


# ============================================================================
# E4/MT4-Specific Handlers (4-axis)
# ============================================================================

def handle_e4_status_query(command: str, match: Match, state: Any, context: Dict) -> str:
    """
    E4/MT4-specific status query handler (4-axis).
    Returns status with only 4 axes (X, Y, Z, A).
    """
    return (
        f"<{state.state},"
        f"Angle(XYZA):{state.angle_X:.1f},{state.angle_Y:.1f},"
        f"{state.angle_Z:.1f},{state.angle_A:.1f},"
        f"Cartesian coordinate(XYZ Rx):{state.coordinate_X:.1f},"
        f"{state.coordinate_Y:.1f},{state.coordinate_Z:.1f},"
        f"{state.coordinate_RX:.1f},"
        f"Pump PWM:{state.pump_pwm},Valve PWM:{state.valve_pwm},"
        f"Motion_MODE:{state.motion_mode}>"
    )


def handle_e4_homing(command: str, match: Match, state: Any, context: Dict) -> Optional[str]:
    """
    E4/MT4-specific homing handler (4-axis).
    Resets only the 4 axes to zero.
    """
    state.state = "Home"
    
    # Reset only 4 axes
    state.angle_X = state.angle_Y = state.angle_Z = state.angle_A = 0.0
    
    # Set default home position
    state.coordinate_X = 150.0
    state.coordinate_Y = 0.0
    state.coordinate_Z = 200.0
    state.coordinate_RX = 0.0
    
    # Schedule state change back to Idle
    def set_idle():
        time.sleep(0.5)
        state.state = "Idle"
    threading.Thread(target=set_idle, daemon=True).start()
    
    return "ok"


def handle_e4_angle_movement(command: str, match: Match, state: Any, context: Dict) -> Optional[str]:
    """
    E4/MT4-specific angle movement handler (4-axis).
    Only handles X, Y, Z, A axes.
    """
    state.state = "Run"
    
    # Check if incremental mode (G91) or absolute mode (G90)
    is_incremental = "G91" in command.upper()
    
    # Parse angles from command (only X, Y, Z, A for 4-axis)
    coords = re.findall(r"([XYZA])([-\d.]+)", command, re.IGNORECASE)
    for axis, value in coords:
        val = float(value)
        axis = axis.upper()
        if axis == "X":
            state.angle_X = state.angle_X + val if is_incremental else val
        elif axis == "Y":
            state.angle_Y = state.angle_Y + val if is_incremental else val
        elif axis == "Z":
            state.angle_Z = state.angle_Z + val if is_incremental else val
        elif axis == "A":
            state.angle_A = state.angle_A + val if is_incremental else val
    
    # Schedule state change back to Idle
    def set_idle():
        time.sleep(0.2)
        state.state = "Idle"
    threading.Thread(target=set_idle, daemon=True).start()
    
    return "ok"


def handle_e4_cartesian_movement(command: str, match: Match, state: Any, context: Dict) -> Optional[str]:
    """
    E4/MT4-specific Cartesian movement handler (4-axis).
    Only handles X, Y, Z, A (as RX) axes.
    """
    state.state = "Run"
    
    # Check if incremental mode (G91) or absolute mode (G90)
    is_incremental = "G91" in command.upper()
    
    # Parse coordinates from command
    coords = re.findall(r"([XYZA])([-\d.]+)", command, re.IGNORECASE)
    for axis, value in coords:
        val = float(value)
        axis = axis.upper()
        if axis == "X":
            state.coordinate_X = state.coordinate_X + val if is_incremental else val
        elif axis == "Y":
            state.coordinate_Y = state.coordinate_Y + val if is_incremental else val
        elif axis == "Z":
            state.coordinate_Z = state.coordinate_Z + val if is_incremental else val
        elif axis == "A":
            state.coordinate_RX = state.coordinate_RX + val if is_incremental else val
    
    # Schedule state change back to Idle
    def set_idle():
        time.sleep(0.2)
        state.state = "Idle"
    threading.Thread(target=set_idle, daemon=True).start()
    
    return "ok"


# ============================================================================
# MS4220-Specific Handlers (Stepper Motor)
# ============================================================================

def handle_ms4220_status_query(command: str, match: Match, state: Any, context: Dict) -> str:
    """
    MS4220-specific status query handler.
    Returns motor status with position and speed.
    """
    # MS4220 uses different state attributes
    position = getattr(state, 'motor_position', 0)
    speed = getattr(state, 'motor_speed', 0)
    motor_state = getattr(state, 'motor_state', 'Idle')
    
    return f"<{motor_state},Position:{position},Speed:{speed}>"


def handle_ms4220_speed(command: str, match: Match, state: Any, context: Dict) -> Optional[str]:
    """
    MS4220-specific speed setting handler.
    Sets the motor speed.
    """
    speed = int(match.group(1))
    state.motor_speed = speed
    return "ok"


def handle_ms4220_position(command: str, match: Match, state: Any, context: Dict) -> Optional[str]:
    """
    MS4220-specific absolute position movement.
    Moves motor to absolute position.
    """
    position = int(match.group(1))
    state.motor_position = position
    return "ok"


def handle_ms4220_relative(command: str, match: Match, state: Any, context: Dict) -> Optional[str]:
    """
    MS4220-specific relative position movement.
    Moves motor by relative distance.
    """
    distance = int(match.group(1))
    current = getattr(state, 'motor_position', 0)
    state.motor_position = current + distance
    return "ok"


def handle_ms4220_home(command: str, match: Match, state: Any, context: Dict) -> Optional[str]:
    """
    MS4220-specific homing handler.
    Homes the motor to zero position.
    """
    state.motor_position = 0
    state.motor_state = "Home"
    
    def set_idle():
        time.sleep(0.3)
        state.motor_state = "Idle"
    threading.Thread(target=set_idle, daemon=True).start()
    
    return "ok"


# ============================================================================
# Custom Command Handlers (Examples)
# ============================================================================

def handle_get_position(command: str, match: Match, state: Any, context: Dict) -> str:
    """
    Custom handler for $P command.
    Returns current position in a simple format.
    """
    return f"X:{state.coordinate_X:.2f},Y:{state.coordinate_Y:.2f},Z:{state.coordinate_Z:.2f}"


def handle_echo(command: str, match: Match, state: Any, context: Dict) -> str:
    """
    Custom handler for ECHO command.
    Returns the echoed message.
    """
    message = match.group(1) if match.groups() else ""
    return f"ECHO: {message}"


def handle_led(command: str, match: Match, state: Any, context: Dict) -> Optional[str]:
    """
    Custom handler for LED command.
    Simulates LED control.
    """
    led_state = match.group(1).upper() if match.groups() else "OFF"
    # Store in context or state if needed
    # For now, just acknowledge
    return "ok"


# ============================================================================
# Handler Registry
# ============================================================================

# All available handlers - maps handler name to function
HANDLER_REGISTRY = {
    # Base/Generic handlers
    "handle_status_query": handle_status_query,
    "handle_version_query": handle_version_query,
    "handle_homing": handle_homing,
    "handle_cartesian_movement": handle_cartesian_movement,
    "handle_angle_movement": handle_angle_movement,
    "handle_expand_axis": handle_expand_axis,
    "handle_pwm_control": handle_pwm_control,
    "handle_speed_control": handle_speed_control,
    
    # Mirobot-specific handlers (6-axis)
    "handle_mirobot_status_query": handle_mirobot_status_query,
    
    # E4/MT4-specific handlers (4-axis)
    "handle_e4_status_query": handle_e4_status_query,
    "handle_e4_homing": handle_e4_homing,
    "handle_e4_angle_movement": handle_e4_angle_movement,
    "handle_e4_cartesian_movement": handle_e4_cartesian_movement,
    
    # MS4220-specific handlers (stepper motor)
    "handle_ms4220_status_query": handle_ms4220_status_query,
    "handle_ms4220_speed": handle_ms4220_speed,
    "handle_ms4220_position": handle_ms4220_position,
    "handle_ms4220_relative": handle_ms4220_relative,
    "handle_ms4220_home": handle_ms4220_home,
    
    # GPIO handlers
    "handle_gpio_mode_query": handle_gpio_mode_query,
    "handle_gpio_mode_set": handle_gpio_mode_set,
    "handle_gpio_output_query": handle_gpio_output_query,
    "handle_gpio_output_set": handle_gpio_output_set,
    "handle_gpio_enable_query": handle_gpio_enable_query,
    "handle_gpio_enable_set": handle_gpio_enable_set,
    "handle_gpio_threshold_query": handle_gpio_threshold_query,
    "handle_gpio_threshold_set": handle_gpio_threshold_set,
    "handle_gpio_file_query": handle_gpio_file_query,
    "handle_gpio_file_set": handle_gpio_file_set,
    
    # Custom/Example handlers
    "handle_get_position": handle_get_position,
    "handle_echo": handle_echo,
    "handle_led": handle_led,
}


def get_handler(name: str):
    """
    Get a handler function by name.
    
    Args:
        name: Handler function name
        
    Returns:
        The handler function or None if not found
    """
    return HANDLER_REGISTRY.get(name)


def register_handler(name: str, handler):
    """
    Register a custom handler function.
    
    Args:
        name: Name to register the handler under
        handler: The handler function
    """
    HANDLER_REGISTRY[name] = handler
