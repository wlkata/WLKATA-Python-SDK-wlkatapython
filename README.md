# WLKATA Python SDK: wlkatapython

#### Python version 3.9.0

#### Date of latest update: Jan 04 2024

License: MIT


## IMPORTANT!!!

This is a package that uses Python to control products such as Mirobot robotic arms, E4 robotic arms, slides, conveyor belts, etc. This package mainly communicates through pyserial and G code protocols. Currently, it supports RS485 or UART communication. It should be noted that when using this package, a multi-functional controller is required, as some functions of the modified package use multi-functional controllers. If the mechanical arm is directly connected, some functions may not be effective


## Description

Wlkatapython is a Python package used to control products such as Mirabot robotic arms, E4 robotic arms, slides, conveyor belts, etc.

The installation command is: pip install wlkatapython

If pyserial is not installed on your device, please use the command: pip install pyserial

This component uses the G code protocol to communicate with the Mirobot over a serial connection. The official **G code instruction set** and **driver download** can be found at the [WLkata Download Page](https://www.wlkata.com/pages/download-center)

## Example Usage

```python
import wlkatapython
import serial
import time

'''Robot arm return to zero'''
serial1 = serial.Serial("COM3", 38400)#Set serial port and baud rate
mirobot1 =wlkatapython.Wlkata_UART()#Create a new mirobot1 object
mirobot1.init(serial1, 1)#Set the address of the robotic arm
mirobot1.homing()#Robot arm return to zero
serial1.close()#close port
```
```python
import wlkatapython
import serial
import time

'''Execute offline files'''
serial1 = serial.Serial("COM3", 38400)#Set serial port and baud rate
mirobot1 =wlkatapython.Wlkata_UART()#Create a new mirobot1 object
mirobot1.init(serial1, 1)#Set the address of the robotic arm
mirobot1.runFile("ceshi", False)#Circular execution of a file, True for circular execution of the file, False for single execution of the file
serial1.close()#close port
```
```python
import wlkatapython
import serial
import time

'''Stop the current program'''
serial1 = serial.Serial("COM3", 38400)#Set serial port and baud rate
mirobot1 =wlkatapython.Wlkata_UART()#Create a new mirobot1 object
mirobot1.init(serial1, 1)#Set the address of the robotic arm
mirobot1.runFile("ceshi",True)#Circular execution of a file, True for circular execution of the file, False for single execution of the file
time.sleep(5)#Wait for 5 seconds
mirobot1.cancellation()#Stop the currently running program
serial1.close()#close port
```


## Communication Methods

Please contact wlkata personnel for further instructions.[WLkata Download Page](https://www.wlkata.com/pages/download-center)
