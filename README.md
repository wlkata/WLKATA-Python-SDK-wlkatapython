# wlkatapython

#### Python version 3.9.0

License: MIT


## IMPORTANT!!!

This is a package that uses Python to control products such as Mirobot robotic arms, E4 robotic arms, slides, conveyor belts, etc. This package mainly communicates through pyserial and G code protocols. Currently, it supports RS485 or UART communication. It should be noted that when using this package, a multi-functional controller is required, as some functions of the modified package use multi-functional controllers. If the mechanical arm is directly connected, some functions may not be effective


## Description

Wlkatapython is a Python package used to control products such as Mirabot robotic arms, E4 robotic arms, slides, conveyor belts, etc.

![Mirobot](/images/Mirobot_Solo_256.jpg)

This component uses the G code protocol to communicate with the Mirobot over a serial connection. The official **G code instruction set** and **driver download** can be found at the [WLkata Download Page](https://www.wlkata.com/pages/download-center)

## Example Usage

```python
import wlkatapython
import serial
import time

'''机械臂回零'''
serial1 = serial.Serial("COM3", 38400)#设置串口及波特率
mirobot1 =wlkatapython.Wlkata_UART()#新建mirobot1对象
mirobot1.init(serial1, 1)#设置机械臂地址
mirobot1.homing()#机械臂回零
serial1.close()#关闭串口
```
```python
import wlkatapython
import serial
import time

'''执行离线文件'''
serial1 = serial.Serial("COM3", 38400)#设置串口及波特率
mirobot1 =wlkatapython.Wlkata_UART()#新建mirobot1对象
mirobot1.init(serial1, 1)#设置机械臂地址
mirobot1.runFile("ceshi", False)#循环执行某一文件，True为循环执行文件，False为单次执行文件
serial1.close()#关闭串口
```
```python
import wlkatapython
import serial
import time

'''停止当前程序'''
serial1 = serial.Serial("COM3", 38400)#设置串口及波特率
mirobot1 =wlkatapython.Wlkata_UART()#新建mirobot1对象
mirobot1.init(serial1, 1)#设置机械臂地址
mirobot1.runFile("ceshi",True)#循环执行某一文件，True为循环执行文件，False为单次执行文件
time.sleep(5)#等待5秒钟
mirobot1.cancellation()#停止当前运行的程序
serial1.close()#关闭串口
```


## Communication Methods

Please contact wlkata personnel for further instructions.[WLkata Download Page](https://www.wlkata.com/pages/download-center)