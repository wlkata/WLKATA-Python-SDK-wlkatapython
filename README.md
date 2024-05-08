# wlkatapython

#### Python version 3.9.0
#### wlkatapython version 0.0.9

License: MIT


## IMPORTANT!!!

This is a package that uses Python to control products such as Mirobot robotic arms, E4 robotic arms, slides, conveyor belts, etc. This package mainly communicates through pyserial and G code protocols. Currently, it supports RS485 or UART communication. It should be noted that when using this package, a multi-functional controller is required, as some functions of the modified package use multi-functional controllers. If the mechanical arm is directly connected, some functions may not be effective


## Description

Wlkatapython is a Python package used to control products such as Mirabot robotic arms, E4 robotic arms, slides, conveyor belts, etc.



This component uses the G code protocol to communicate with the Mirobot over a serial connection. The official **G code instruction set** and **driver download** can be found at the [WLkata Download Page](https://www.wlkata.com/pages/download-center)

## RS485 wiring diagram
Add RS485 driver dual device image

<div style="text-align: center;">
  <img src="./img/img1.png" style="width: 50%;">
</div>

## Example Usage

```python
import wlkatapython
import serial
import time

"Robot arm returns to zero"
Serial1=serial Serial ("COM3", 38400) # Set serial port and baud rate
Mirobot1=wlkatapython Wlkata_UART() # Create a new mirobot1 object
Mirobot1. init (serial1, 1) # Set the address of the robotic arm
Mirobot1.homeing() # Robot arm zeroing
Serial1. close() # Close serial port
```
```python
import wlkatapython
import serial
import time

"Execute offline files"
Serial1=serial Serial ("COM3", 38400) # Set serial port and baud rate
Mirobot1=wlkatapython Wlkata_UART() # Create a new mirobot1 object
Mirobot1. init (serial1, 1) # Set the address of the robotic arm
Mirobot1.runFile ("ceshi", False) # Execute a file in a loop. True is the loop execution file, and False is the single execution file
Serial1. close() # Close serial port
```
```python
import wlkatapython
import serial
import time

"Stop the current program"
Serial1=serial Serial ("COM3", 38400) # Set serial port and baud rate
Mirobot1=wlkatapython Wlkata_UART() # Create a new mirobot1 object
Mirobot1. init (serial1, 1) # Set the address of the robotic arm
Mirobot1.runFile ("ceshi", True) # Loop execution of a file, True is the loop execution file, False is the single execution file
Time. sleep (5) # Wait for 5 seconds
Mirobot1. cancelation() # Stop the currently running program
Serial1. close() # Close serial port
```
```python
import wlkatapython

"Mirobot_Serial_GUI"
Mirobot_GUI=wlkatapython.Mirobot_Serial_GUI()
Mirobot_GUI..Mirobot_GUI()
```

## Communication Methods

Please contact wlkata personnel for further instructions.[WLkata Download Page](https://www.wlkata.com/pages/download-center)
