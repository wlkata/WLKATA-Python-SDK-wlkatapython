# WLKATA Python SDK

Control WLKATA robotic arms and motion controllers from Python.

**Package version:** 1.0.1.post1

Python 3.8 or newer. MIT License.

The SDK speaks the WLKATA G-code protocol over UART, RS485, Wi-Fi, and Bluetooth LE. Use it to home a robot, move in joint or Cartesian space, run programs stored on the controller, and read status. A simulator is included so you can develop and test without hardware.

The official G-code set and controller drivers are on the [WLKATA download page](https://www.wlkata.com/pages/download-center).

## Install

From TestPyPI:

```bash
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ wlkatapython-dev
```

Bluetooth LE needs the optional extra:

```bash
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ "wlkatapython-dev[ble]"
```

From a checkout:

```bash
python -m pip install -e ".[dev]"
```

## Requirements

- Python 3.8 or newer
- A WLKATA controller on a serial port, Wi-Fi, or Bluetooth LE
- A multifunctional controller for the full command set. An arm connected without that controller will not support every function in this SDK.

| Link | Typical baud | Address |
| --- | --- | --- |
| UART | 115200 | `-1` |
| RS485 | 38400 | Device address, `0`–`255` |

## Quick start

```python
from wlkatapython import Mirobot_UART

robot = Mirobot_UART()
robot.init_uart("COM3", -1)          # Linux/macOS: "/dev/ttyUSB0"
robot.homing()
robot.writeAngle(0, 45.0, 30.0, 15.0, 10.0, 5.0, 0.0)
status = robot.getStatus()
robot.close()
```

`writeAngle` and `writeCoordinate` take a mode first. `0` is absolute, `1` is incremental. For Cartesian moves, the first argument is the motion type: `0` fast, `1` linear, `2` joint.

```python
robot.writeCoordinate(1, 0, x=200.0, y=0.0, z=150.0)
```

RS485 uses the device address and 38400 baud:

```python
from wlkatapython import MT4_UART

arm = MT4_UART()
arm.init_uart("COM3", 1, baudrate=38400)
arm.homing()
arm.close()
```

## Supported products

| Class | Product |
| --- | --- |
| `Mirobot_UART` | Mirobot 6-axis desktop arm |
| `E4_UART` | E4 4-axis SCARA arm |
| `MT4_UART` | MT4 4-axis arm |
| `Harobot_UART` | Harobot 7-axis arm |
| `Miromax_UART` | Miromax (Harobot protocol) |
| `MS4220_UART` | MS4220 stepper controller (slide or conveyor) |

Every class shares homing, speed, status, offline programs, and end-effector helpers. Axis counts differ, so pass only the axes that product uses.

MS4220 speed is signed, from `-100` to `100`:

```python
from wlkatapython import MS4220_UART

slide = MS4220_UART()
slide.init_uart("COM3", 10, baudrate=38400)
slide.speed(100)
slide.speed(0)
slide.close()
```

## Programs on the controller

`runFile` starts a file already stored on the controller. `cancellation` stops the current motion.

```python
robot.runFile("ceshi", False)
robot.cancellation()
```

## Other transports

Wi-Fi:

```python
robot = Mirobot_UART()
robot.init_wifi("192.168.1.10", 23)
robot.homing()
robot.close()
```

Bluetooth LE, after installing the `ble` extra. The name must match the advertised name exactly:

```python
robot = Mirobot_UART()
robot.init_ble("ExBox-E510")
robot.homing()
robot.close()
```

An existing `serial.Serial` port still works. Pass `-1` for UART or the RS485 address:

```python
import serial
from wlkatapython import Mirobot_UART

port = serial.Serial("COM3", 115200)
robot = Mirobot_UART()
robot.init(port, -1)
robot.homing()
port.close()
```

## Develop without hardware

```python
import serial
from wlkatapython import Mirobot_UART
from wlkatapython.simulator import MirobotSimulator

sim = MirobotSimulator()
port_path = sim.start()
try:
    robot = Mirobot_UART()
    robot.init(serial.Serial(port_path, 115200, timeout=2), -1)
    robot.homing()
    robot.writeAngle(0, 20.0, 10.0, 0.0, 0.0, 0.0, 0.0)
finally:
    sim.stop()
```

The same pattern is available for E4, MT4, and MS4220. A longer walkthrough is in `example/example.py`.

## Desktop utility

`Mirobot_Serial_GUI` is a small Tkinter window for Cartesian moves when WLKATA Studio is not installed on the machine.

```python
from wlkatapython import Mirobot_Serial_GUI

Mirobot_Serial_GUI().Mirobot_GUI()
```

## Documentation

Build the Sphinx API reference from the repository:

```bash
python scripts/build_docs.py
```

## License

MIT. See [LICENSE](LICENSE).
