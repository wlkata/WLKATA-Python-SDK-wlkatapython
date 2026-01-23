"""
    WLKATA_UART and Mirobot-UART are the base classes for serial communication of all robotic arms, including UART and RS485 communication.
    Mirobot-UART inherits from wlkata_UART,
    Mirobot_SeriAL-GUI is the GUI for the Mirobot robotic arm,
    E4-UART is a class of E4 robotic arms that inherits from wlkata_ UART,
    MT4-UART is a class of the MT4 robotic arm, inherited from wlkata_UART.

    wlkata_UART与Mirobot_UART是所有机械臂的基于串口通信的基类，包括UART和RS485通信。
    Mirobot_UART是继承自wlkata_UART，
    Mirobot_Serial_GUI是Mirobot机械臂的GUI，
    E4_UART是E4机械臂的类，继承自Mirobot_UART， 
    MT4_UART是MT4机械臂的类， 继承自Mirobot_UART，
    MS4220_UART是MS4220步进电机控制器的类， 继承自wlkata_UART。

"""
import sys
sys.path.append('Mirobot_robot')
sys.path.append('E4_robot')
sys.path.append('MT4_robot')
sys.path.append('MS4220_robot')

from Mirobot_robot.Mirobot_UART import Mirobot_UART
from E4_robot.E4_UART import E4_UART  
from MT4_robot.MT4_UART import MT4_UART
from MS4220_robot.MS4220_UART import MS4220_UART

from Mirobot_robot.Mirobot_GUI import Mirobot_Serial_GUI 
import serial

class Wlkata_UART(Mirobot_UART):
    def __init__(self):
        super().__init__()

class Mirobot_UART(Wlkata_UART):
    def __init__(self):
        super().__init__()

class Mirobot_Serial_GUI(Mirobot_Serial_GUI):
    def __init__(self):
        super().__init__()

class E4_UART(E4_UART):
    def __init__(self):
        super().__init__()

class MT4_UART(MT4_UART):
    def __init__(self):
        super().__init__()

class MS4220_UART(MS4220_UART):
    def __init__(self):
        super().__init__()  


