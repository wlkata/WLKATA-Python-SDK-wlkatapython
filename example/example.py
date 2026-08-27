#!/usr/bin/env python
"""
Example usage of the WLKATA Python SDK.

This file demonstrates how to use the SDK with both real hardware
and the simulator for testing.

For comprehensive tests, see the tests/ directory and run:
    python -m pytest tests/ -v

Note: Run this script from the project root directory, or install the package
with `pip install -e .` for the imports to work correctly.
"""


def example_with_real_hardware():
    """
    Example: Using the SDK with real hardware.
    
    Uncomment and modify the serial port to match your setup.
    """
    import wlkatapython
    import serial
    
    # Mirobot example
    # mirobot = wlkatapython.Mirobot_UART()
    # mirobot.init(serial.Serial('COM13', 115200), -1)  # -1 for UART, 0-255 for RS485
    # mirobot.homing()
    # mirobot.writeangle(0, 45, 30, 15, 0, 0, 0)
    # status = mirobot.getStatus()
    # print(f"Robot status: {status}")
    
    # E4 example
    # e4 = wlkatapython.E4_UART()
    # e4.init(serial.Serial('COM13', 115200), -1)
    # e4.homing()
    
    # MT4 example
    # mt4 = wlkatapython.MT4_UART()
    # mt4.init(serial.Serial('COM13', 115200), -1)
    # mt4.homing()
    
    # MS4220 example
    # ms4220 = wlkatapython.MS4220_UART()
    # ms4220.init(serial.Serial('COM13', 38400), 10)  # Address 10
    # ms4220.speed(100)
    
    print("Uncomment the code above to use with real hardware.")


def example_with_simulator():
    """
    Example: Using the SDK with the simulator for testing.
    
    This demonstrates the full workflow without needing real hardware.
    """
    import wlkatapython
    import serial
    import time
    from wlkatapython.simulator import MirobotSimulator, E4Simulator, MS4220Simulator
    
    print("=== Mirobot Simulator Example ===\n")
    
    # Create and start the simulator
    sim = MirobotSimulator()
    port_path = sim.start()
    print(f"Simulator started on: {port_path}")
    time.sleep(0.1)
    
    try:
        # Option A — legacy pyserial (still supported; wrapped silently)
        ser = serial.Serial(port_path, 115200, timeout=2.0)
        
        # Initialize the Mirobot
        mirobot = wlkatapython.Mirobot_UART()
        mirobot.init(ser, -1)

        # Option B — equivalent using the UART transport helper:
        # mirobot = wlkatapython.Mirobot_UART()
        # mirobot.init_uart(port_path, -1, baudrate=115200, timeout=2.0)
        # ...
        # mirobot.close()
        
        # Perform operations
        print("\n1. Homing...")
        mirobot.homing()
        time.sleep(0.7)
        print(f"   State: {sim.state.state}")
        
        print("\n2. Moving to angle position...")
        mirobot.writeangle(0, 45.0, 30.0, 15.0, 0.0, 0.0, 0.0)
        time.sleep(0.3)
        print(f"   Angles: X={sim.state.angle_X}, Y={sim.state.angle_Y}, Z={sim.state.angle_Z}")
        
        print("\n3. Setting PWM...")
        mirobot.pwmWrite(500)
        time.sleep(0.2)
        print(f"   Pump PWM: {sim.state.pump_pwm}")
        
        print("\n4. Querying status...")
        status = mirobot.getStatus()
        print(f"   Robot state: {status['state']}")
        print(f"   Angle X: {status['angle_X']}")
        print(f"   Coordinate X: {status['coordinate_X']}")
        
        print("\n5. Setting speed...")
        mirobot.speed(80)
        time.sleep(0.2)
        print(f"   Speed: {sim.state.speed}")
        
        ser.close()
        
    finally:
        sim.stop()
        print("\nSimulator stopped.")
    
    print("\n" + "="*50 + "\n")
    print("=== E4 Simulator Example ===\n")
    
    # E4 example
    e4_sim = E4Simulator()
    port_path = e4_sim.start()
    print(f"E4 Simulator started on: {port_path}")
    time.sleep(0.1)
    
    try:
        ser = serial.Serial(port_path, 115200, timeout=2.0)
        e4 = wlkatapython.E4_UART()
        e4.init(ser, -1)
        
        print("\n1. Homing E4...")
        e4.homing()
        time.sleep(0.7)
        print(f"   State: {e4_sim.state.state}")
        
        print("\n2. Moving E4 (4-axis)...")
        e4.writeangle(0, 25.0, 35.0, 45.0, 55.0)
        time.sleep(0.3)
        print(f"   Angles: X={e4_sim.state.angle_X}, Y={e4_sim.state.angle_Y}, Z={e4_sim.state.angle_Z}, A={e4_sim.state.angle_A}")
        
        ser.close()
        
    finally:
        e4_sim.stop()
        print("\nE4 Simulator stopped.")
    
    print("\n" + "="*50 + "\n")
    print("=== MS4220 Simulator Example ===\n")
    
    # MS4220 example
    ms_sim = MS4220Simulator(address=10)
    port_path = ms_sim.start()
    print(f"MS4220 Simulator started on: {port_path}")
    time.sleep(0.1)
    
    try:
        ser = serial.Serial(port_path, 38400, timeout=2.0)
        ms4220 = wlkatapython.MS4220_UART()
        ms4220.init(ser, 10)
        
        print("\n1. Setting motor speed...")
        ms4220.speed(75)
        time.sleep(0.2)
        print(f"   Motor speed: {ms_sim.motor_speed}")
        
        print("\n2. Stopping motor...")
        ms4220.speed(0)
        time.sleep(0.2)
        print(f"   Motor speed: {ms_sim.motor_speed}")
        
        ser.close()
        
    finally:
        ms_sim.stop()
        print("\nMS4220 Simulator stopped.")
    
    print("\n" + "="*50)
    print("All examples completed successfully!")


def run_tests():
    """Run the test suite."""
    import sys
    import subprocess
    from pathlib import Path
    
    # Find project root (parent of test/ directory)
    project_root = Path(__file__).parent.parent
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v"],
        cwd=project_root
    )
    return result.returncode


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="WLKATA SDK Examples")
    parser.add_argument("--simulator", "-s", action="store_true",
                        help="Run simulator example")
    parser.add_argument("--hardware", "-hw", action="store_true",
                        help="Run hardware example (requires real hardware)")
    parser.add_argument("--test", "-t", action="store_true",
                        help="Run the test suite")
    
    args = parser.parse_args()
    
    if args.test:
        sys.exit(run_tests())
    elif args.hardware:
        example_with_real_hardware()
    else:
        # Default to simulator example
        example_with_simulator()
