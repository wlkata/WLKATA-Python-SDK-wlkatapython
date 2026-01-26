"""
Pytest configuration and shared fixtures.

This module provides fixtures for all tests, including simulated hardware
connections for Mirobot, E4, MT4, and MS4220 robots.

Note: The project root is automatically added to PYTHONPATH via pytest.ini's
pythonpath setting, so no sys.path manipulation is needed.
"""

import time
import pytest
import serial

from simulator import (
    MirobotSimulator,
    E4Simulator,
    MT4Simulator,
    MS4220Simulator,
    create_simulator,
)
from simulator.virtual_serial import MockSerial


# ============================================================================
# Mirobot Fixtures
# ============================================================================

@pytest.fixture
def mirobot_simulator():
    """Create and start a Mirobot simulator."""
    sim = MirobotSimulator()
    sim.start()
    time.sleep(0.1)  # Allow simulator to start
    yield sim
    sim.stop()


@pytest.fixture
def mirobot_serial(mirobot_simulator):
    """Create a serial connection to the Mirobot simulator."""
    ser = serial.Serial(mirobot_simulator.port_path, 115200, timeout=2.0)
    yield ser
    ser.close()


@pytest.fixture
def mirobot(mirobot_serial):
    """Create and initialize a Mirobot_UART instance."""
    from wlkatapython.robots import Mirobot_UART
    robot = Mirobot_UART()
    robot.init(mirobot_serial, -1)
    return robot


@pytest.fixture
def mirobot_with_sim(mirobot_simulator):
    """Create a Mirobot instance along with its simulator for state inspection."""
    from wlkatapython.robots import Mirobot_UART
    ser = serial.Serial(mirobot_simulator.port_path, 115200, timeout=2.0)
    robot = Mirobot_UART()
    robot.init(ser, -1)
    yield robot, mirobot_simulator
    ser.close()


# ============================================================================
# E4 Fixtures
# ============================================================================

@pytest.fixture
def e4_simulator():
    """Create and start an E4 simulator."""
    sim = E4Simulator()
    sim.start()
    time.sleep(0.1)
    yield sim
    sim.stop()


@pytest.fixture
def e4_serial(e4_simulator):
    """Create a serial connection to the E4 simulator."""
    ser = serial.Serial(e4_simulator.port_path, 115200, timeout=2.0)
    yield ser
    ser.close()


@pytest.fixture
def e4(e4_serial):
    """Create and initialize an E4_UART instance."""
    from wlkatapython.robots import E4_UART
    robot = E4_UART()
    robot.init(e4_serial, -1)
    return robot


@pytest.fixture
def e4_with_sim(e4_simulator):
    """Create an E4 instance along with its simulator for state inspection."""
    from wlkatapython.robots import E4_UART
    ser = serial.Serial(e4_simulator.port_path, 115200, timeout=2.0)
    robot = E4_UART()
    robot.init(ser, -1)
    yield robot, e4_simulator
    ser.close()


# ============================================================================
# MT4 Fixtures
# ============================================================================

@pytest.fixture
def mt4_simulator():
    """Create and start an MT4 simulator."""
    sim = MT4Simulator()
    sim.start()
    time.sleep(0.1)
    yield sim
    sim.stop()


@pytest.fixture
def mt4_serial(mt4_simulator):
    """Create a serial connection to the MT4 simulator."""
    ser = serial.Serial(mt4_simulator.port_path, 115200, timeout=2.0)
    yield ser
    ser.close()


@pytest.fixture
def mt4(mt4_serial):
    """Create and initialize an MT4_UART instance."""
    from wlkatapython.robots import MT4_UART
    robot = MT4_UART()
    robot.init(mt4_serial, -1)
    return robot


@pytest.fixture
def mt4_with_sim(mt4_simulator):
    """Create an MT4 instance along with its simulator for state inspection."""
    from wlkatapython.robots import MT4_UART
    ser = serial.Serial(mt4_simulator.port_path, 115200, timeout=2.0)
    robot = MT4_UART()
    robot.init(ser, -1)
    yield robot, mt4_simulator
    ser.close()


# ============================================================================
# MS4220 Fixtures
# ============================================================================

@pytest.fixture
def ms4220_simulator():
    """Create and start an MS4220 simulator."""
    sim = MS4220Simulator(address=10)
    sim.start()
    time.sleep(0.1)
    yield sim
    sim.stop()


@pytest.fixture
def ms4220_serial(ms4220_simulator):
    """Create a serial connection to the MS4220 simulator."""
    ser = serial.Serial(ms4220_simulator.port_path, 38400, timeout=2.0)
    yield ser
    ser.close()


@pytest.fixture
def ms4220(ms4220_serial):
    """Create and initialize an MS4220_UART instance."""
    from wlkatapython.robots import MS4220_UART
    robot = MS4220_UART()
    robot.init(ms4220_serial, 10)
    return robot


@pytest.fixture
def ms4220_with_sim(ms4220_simulator):
    """Create an MS4220 instance along with its simulator for state inspection."""
    from wlkatapython.robots import MS4220_UART
    ser = serial.Serial(ms4220_simulator.port_path, 38400, timeout=2.0)
    robot = MS4220_UART()
    robot.init(ms4220_serial, 10)
    yield robot, ms4220_simulator
    ser.close()


# ============================================================================
# RS485 Fixtures
# ============================================================================

@pytest.fixture
def mirobot_rs485_simulator():
    """Create and start a Mirobot simulator with RS485 addressing."""
    sim = MirobotSimulator(address=5)
    sim.start()
    time.sleep(0.1)
    yield sim
    sim.stop()


@pytest.fixture
def mirobot_rs485(mirobot_rs485_simulator):
    """Create a Mirobot instance with RS485 addressing."""
    from wlkatapython.robots import Mirobot_UART
    ser = serial.Serial(mirobot_rs485_simulator.port_path, 115200, timeout=2.0)
    robot = Mirobot_UART()
    robot.init(ser, 5)  # RS485 address 5
    yield robot, mirobot_rs485_simulator
    ser.close()


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def wait_for_idle():
    """Helper function to wait for robot to become idle."""
    def _wait_for_idle(simulator, timeout=2.0):
        start = time.time()
        while time.time() - start < timeout:
            if simulator.state.state == "Idle":
                return True
            time.sleep(0.1)
        return False
    return _wait_for_idle
