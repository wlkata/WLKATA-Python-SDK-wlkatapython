import sys
import os
sys.path.append(os.path.abspath('Mirobot_robot'))

from Mirobot_robot.Mirobot_UART import WLKATA_UART

import time
import serial

#MS4220步进电机
#MS4220 stepper motor

class MS4220_UART(WLKATA_UART):
    def __init__(self):
        super().__init__()
        self.num = None
        self.string = None
        self.address = None
        self.pSerial = None
        

    #Save serial object and MS4220 address (RS458 address range: 0-255)
    # 保存串口对象和MS4220地址（RS458地址范围：0-255）

    def init(self, p, adr):
        self.pSerial = p
        self.address = adr

    #Pass-through command, with \r\n included
    # 透传命令，包含\r\n

    def sendMsg(self, string):
        if self.address != -1:
            self.string = "@" + str(self.address) + string + "\r\n"
        else:
            self.string = string + "\r\n"
        self.pSerial.write(self.string.encode("utf-8"))
        time.sleep(0.1)

    #Step motor speed setting, value range: 0-100
    # 步进电机速度设置，范围：0-100

    def speed(self, num):
        self.num = num
        if self.num > 100:
            self.num == 100
        elif self.num < -100:
            self.num == -100
        self.num = "G6 F" + str(self.num)
        self.sendMsg(self.num)

        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.speed, 1)
    


if __name__ == "__main__":
    ms4220 = MS4220_UART()
    ms4220.init(serial.Serial('COM13', 38400), 10)
    ms4220.speed(100)
