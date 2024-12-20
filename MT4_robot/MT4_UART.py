import sys
import os
sys.path.append(os.path.abspath('Mirobot_robot'))

from Mirobot_robot.Mirobot_UART import Mirobot_UART
import serial
import time

#E4串口控制类
#E4 serial port control class

class MT4_UART(Mirobot_UART):
    # E4复位指令
    # E4 homing command
    def homing(self, mode=8):
        self.mode = mode
        if self.mode == 0:
            self.sendMsg("o105=0")
        elif self.mode == 1:
            self.sendMsg("o105=1")
        elif self.mode == 2:
            self.sendMsg("o105=2")
        elif self.mode == 3:
            self.sendMsg("o105=3")
        elif self.mode == 4:
            self.sendMsg("o105=4")
        elif self.mode == 7:
            self.sendMsg("o105=7")
        elif self.mode == 8:
            self.sendMsg("o105=8")
        elif self.mode == 9:
            self.sendMsg("o105=9")
        elif self.mode == 10:
            self.sendMsg("o105=10")
        else:
            self.sendMsg("$h")

    # E4初始位置
    # E4 initial position
    def zero(self):
        self.sendMsg("M21 G90 G00 X0 Y0 Z0 A0 ")

    # E4笛卡尔坐标控制
    # E4 Cartesian coordinate control
    def writecoordinate(self, motion, position, x, y, z, a):
        self.motion = motion
        self.position = position
        self.coordinate = "X" + str(x) + "Y" + str(y) + "Z" + str(z) + "A" + str(a)
        if self.motion == 0:
            self.motion = "G00"
        elif self.motion == 1:
            self.motion = "G01"
        elif self.motion == 2:
            self.motion = "G05"
        else:
            self.motion = "G00"

        if self.position == 0:
            self.position = "G90"
        elif self.position == 1:
            self.position = "G91"
        else:
            self.position = "G90"
        self.coordinate = "M20" + str(self.position) + str(self.motion) + self.coordinate
        self.sendMsg(self.coordinate)

    # E4角度设置
    # E4 angle setting
    def writeangle(self, position, x, y, z, a):
        self.position = position
        self.coordinate = "X" + str(x) + "Y" + str(y) + "Z" + str(z) + "A" + str(a)
        if self.position == 0:
            self.position = "G90"
        elif self.position == 1:
            self.position = "G91"
        else:
            self.position = "G90"
        self.coordinate = "M21" + str(self.position) + "G00" + self.coordinate
        self.sendMsg(self.coordinate)

    # E4机械臂角度获取
    # E4 robotic arm angle acquisition
    def getAngle(self, num):
        self.num = num
        self.getStatus()
        if num == 1:
            return self.mirobot_state_all["angle_X"]
        elif num == 2:
            return self.mirobot_state_all["angle_Y"]
        elif num == 3:
            return self.mirobot_state_all["angle_Z"]
        elif num == 4:
            return self.mirobot_state_all["angle_A"]
        elif num == 7:
            return self.mirobot_state_all["angle_D"]
        else:
            return "parameter error/参数错误"

    # E4机械臂坐标获取
    # E4 robotic arm coordinate acquisition 
    def getcoordinate(self, num):
        self.num = num
        self.getStatus()
        if num == 1:
            return self.mirobot_state_all["coordinate_X"]
        elif num == 2:
            return self.mirobot_state_all["coordinate_Y"]
        elif num == 3:
            return self.mirobot_state_all["coordinate_Z"]
        elif num == 4:
            return self.mirobot_state_all["coordinate_RX"]
        else:
            return "parameter error/参数错误"

    # E4查询版本信息
    # E4 query version information  
    def version(self):
        self.lina = ""  # 初始化为字符串 #Initialized as a string
        self.lina1 = ""  # 初始化为字符串 #Initialized as a string   

        self.pSerial.flushInput()
        self.pSerial.flushOutput()
        self.sendMsg("$V")

        timeout_cnt = 0  # 计数器，用于记录超时次数 #Counter, used to record the number of times the timeout occurs


        while True:
            if timeout_cnt >= 5:  # 如果超时次数超过5次，返回失败消息 #If the number of times the timeout occurs exceeds 5 times, return the failure message
                return "查询失败"

            self.lina = self.pSerial.readline().decode('utf-8').strip()
            self.lina1 = self.pSerial.readline().decode('utf-8').strip()

            if self.lina.startswith('EXbox') and self.lina1.startswith(
                    'E4'):  # 如果两行数据分别以 'EXbox' 和 'e4' 开头，跳出循环并返回结果 #If the two lines of data start with 'EXbox' and 'e4', jump out of the loop and return the result  
                break

            timeout_cnt += 1
            time.sleep(0.1)

        return self.lina, self.lina1

if __name__ == "__main__":
    mt4 = MT4_UART()
    mt4.init(serial.Serial('COM13', 115200), -1)
    mt4.homing()

