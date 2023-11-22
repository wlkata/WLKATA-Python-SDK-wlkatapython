'''
VERSION:0.0.7
'''
import serial
import time
import re


class Wlkata_UART:
    def __init__(self):

        self.mirobot_state_all = {"state": "-1",
                                  "angle_A": -1, "angle_B": -1, "angle_C": -1, "angle_D": -1, "angle_X": -1,
                                  "angle_Y": -1,
                                  "angle_Z": -1,
                                  "coordinate_X": -1, "coordinate_Y": -1, "coordinate_Z": -1, "coordinate_RX": -1,
                                  "coordinate_RY": -1, "coordinate_RZ": -1,
                                  "pump": -1,
                                  "valve": -1,
                                  "mooe": -1}

    # 串口对象+地址
    def init(self, p, adr):
        self.pSerial = p
        self.address = adr

    # 穿透指令
    def sendMsg(self, string):
        if self.address != -1:
            self.string = "@" + str(self.address) + string + "\r\n"
        else:
            self.string = string + "\r\n"
        self.pSerial.write(self.string.encode("utf-8"))
        time.sleep(0.1)

    # 复位指令
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
        elif self.mode == 5:
            self.sendMsg("o105=5")
        elif self.mode == 6:
            self.sendMsg("o105=6")
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

    # 离线文件指令，可设置是否循环执行
    def runFile(self, fileName, num=False):
        self.num = num
        if self.num == True:
            self.fileName = "o112" + str(fileName)
            self.sendMsg(self.fileName)
        elif self.num == False:
            self.fileName = "o111" + str(fileName)
            self.sendMsg(self.fileName)
        else:
            self.fileName = "o111" + str(fileName)
            self.sendMsg(self.fileName)

    # 停止当前程序
    def cancellation(self):
        self.sendMsg("o117")

    # 舵机夹爪指令
    def gripper(self, num):
        self.num = num
        if self.num == True:
            self.sendMsg("M3 S40")
        else:
            self.sendMsg("M3 S60")

    # 气泵控制
    def pump(self, num):
        self.num = num
        if self.num == 0:
            self.sendMsg("M3 S0")
        elif self.num == 1:
            self.sendMsg("M3 S1000")
        elif self.num == 2:
            self.sendMsg("M3 S500")
        else:
            self.sendMsg("M3 S0")

    # PWM控制
    def pwmWrite(self, num):
        self.num = "M3 S" + str(num)
        self.sendMsg(self.num)

    # 初始位置
    def zero(self):
        self.sendMsg("M21 G90 G00 X0 Y0 Z0 A0 B0 C00")

    # 笛卡尔坐标控制
    def writecoordinate(self, motion, position, x, y, z, a, b, c):
        self.motion = motion
        self.position = position
        self.coordinate = "X" + str(x) + "Y" + str(y) + "Z" + str(z) + "A" + str(a) + "B" + str(b) + "C" + str(c)
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

    # 速度设置
    def speed(self, num):
        self.num = "F" + str(num)
        self.sendMsg(self.num)

    # 角度设置
    def writeangle(self, position, x, y, z, a, b, c):
        self.position = position
        self.coordinate = "X" + str(x) + "Y" + str(y) + "Z" + str(z) + "A" + str(a) + "B" + str(b) + "C" + str(c)
        if self.position == 0:
            self.position = "G90"
        elif self.position == 1:
            self.position = "G91"
        else:
            self.position = "G90"
        self.coordinate = "M21" + str(self.position) + "G00" + self.coordinate
        self.sendMsg(self.coordinate)

    # 拓展轴控制
    def writeexpand(self, motion, position, d):
        self.motion = motion
        self.position = position
        self.coordinate = "D" + str(d)
        if self.motion == 0:
            self.motion = "G00"
        elif self.motion == 1:
            self.motion = "G01"
        else:
            self.motion = "G00"

        if self.position == 0:
            self.position = "G90"
        elif self.position == 1:
            self.position = "G91"
        else:
            self.position = "G90"
        self.coordinate = str(self.position) + str(self.motion) + self.coordinate
        self.sendMsg(self.coordinate)

    # 重启设备
    def restart(self):
        self.sendMsg("o100")

    # 查询版本信息
    def version(self):
        self.lina = ""  # 初始化为字符串
        self.lina1 = ""  # 初始化为字符串

        self.pSerial.flushInput()
        self.pSerial.flushOutput()
        self.sendMsg("$V")

        timeout_cnt = 0  # 计数器，用于记录超时次数

        while True:
            if timeout_cnt >= 5:  # 如果超时次数超过5次，返回失败消息
                return "Query failed//查询失败"

            self.lina = self.pSerial.readline().decode('utf-8').strip()
            self.lina1 = self.pSerial.readline().decode('utf-8').strip()

            if self.lina.startswith('EXbox') and self.lina1.startswith(
                    'Mirobot'):  # 如果两行数据分别以 'EXbox' 和 'Mirobot' 开头，跳出循环并返回结果
                break

            timeout_cnt += 1
            time.sleep(0.1)

        return self.lina, self.lina1

    # 获取机械臂所有信息，输出字典形式
    def getStatus(self):
        self.line = " "
        self.pSerial.flushInput()
        self.pSerial.flushOutput()
        self.sendMsg("?")
        if self.pSerial.in_waiting > 0:
            self.line = self.pSerial.readline().decode('utf-8').strip()
            if self.line[0] == "<" and self.line[-1] == ">":
                self.data = self.parse_response(self.line)
            else:
                self.data = -1
        else:
            return "error"

        time.sleep(0.1)
        return self.data

    # 正则表达式
    def parse_response(self, line):
        self.pattern = r'<(\w+),Angle\(ABCDXYZ\):([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),Cartesian coordinate\(XYZ RxRyRz\):([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),([\d.-]+),Pump PWM:([\d.-]+),Valve PWM:([\d.-]+),Motion_MODE:([\d.-]+)>'
        match = re.match(self.pattern, line)
        if match:

            self.mirobot_state_all = {"state": " ",
                                      "angle_A": 0, "angle_B": 0, "angle_C": 0, "angle_D": 0, "angle_X": 0,
                                      "angle_Y": 0, "angle_Z": 0,
                                      "coordinate_X": 0, "coordinate_Y": 0, "coordinate_Z": 0, "coordinate_RX": 0,
                                      "coordinate_RY": 0, "coordinate_RZ": 0,
                                      "pump": 0,
                                      "valve": 0,
                                      "mooe": 0}

            self.mirobot_state_all["state"] = match.group(1)
            self.mirobot_state_all["angle_A"] = match.group(2)
            self.mirobot_state_all["angle_B"] = match.group(3)
            self.mirobot_state_all["angle_C"] = match.group(4)
            self.mirobot_state_all["angle_D"] = match.group(5)
            self.mirobot_state_all["angle_X"] = match.group(6)
            self.mirobot_state_all["angle_Y"] = match.group(7)
            self.mirobot_state_all["angle_Z"] = match.group(8)
            self.mirobot_state_all["coordinate_X"] = match.group(9)
            self.mirobot_state_all["coordinate_Y"] = match.group(10)
            self.mirobot_state_all["coordinate_Z"] = match.group(11)
            self.mirobot_state_all["coordinate_RX"] = match.group(12)
            self.mirobot_state_all["coordinate_RY"] = match.group(13)
            self.mirobot_state_all["coordinate_RZ"] = match.group(14)
            self.mirobot_state_all["pump"] = match.group(15)
            self.mirobot_state_all["valve"] = match.group(16)
            self.mirobot_state_all["mooe"] = match.group(17)
            return self.mirobot_state_all
        else:
            return "parse error/解析错误"

    # 机械臂状态查询
    def getState(self):
        self.getStatus()
        return self.mirobot_state_all["state"]

    # 机械臂角度获取
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
        elif num == 5:
            return self.mirobot_state_all["angle_B"]
        elif num == 6:
            return self.mirobot_state_all["angle_C"]
        elif num == 7:
            return self.mirobot_state_all["angle_D"]
        else:
            return "parameter error/参数错误"

    # 机械臂坐标获取
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
        elif num == 5:
            return self.mirobot_state_all["coordinate_RY"]
        elif num == 6:
            return self.mirobot_state_all["coordinate_RZ"]
        else:
            return "parameter error/参数错误"

    # 气泵状态查询
    def getpump(self):
        self.getStatus()
        return self.mirobot_state_all["pump"]

    # 夹爪状态查询
    def getvalve(self):
        self.getStatus()
        return self.mirobot_state_all["valve"]

    # 运动模式查询
    def getmooe(self):
        self.getStatus()
        return self.mirobot_state_all["mooe"]


class E4(Wlkata_UART):
    # E4复位指令
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
    def zero(self):
        self.sendMsg("M21 G90 G00 X0 Y0 Z0 A0 ")

    # E4笛卡尔坐标控制
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
    def version(self):
        self.lina = ""  # 初始化为字符串
        self.lina1 = ""  # 初始化为字符串

        self.pSerial.flushInput()
        self.pSerial.flushOutput()
        self.sendMsg("$V")

        timeout_cnt = 0  # 计数器，用于记录超时次数

        while True:
            if timeout_cnt >= 5:  # 如果超时次数超过5次，返回失败消息
                return "查询失败"

            self.lina = self.pSerial.readline().decode('utf-8').strip()
            self.lina1 = self.pSerial.readline().decode('utf-8').strip()

            if self.lina.startswith('EXbox') and self.lina1.startswith(
                    'E4'):  # 如果两行数据分别以 'EXbox' 和 'e4' 开头，跳出循环并返回结果
                break

            timeout_cnt += 1
            time.sleep(0.1)

        return self.lina, self.lina1


class MS4220_UART:
    def __init__(self):
        self.num = None
        self.string = None
        self.address = None
        self.pSerial = None

    # 串口对象+地址
    def init(self, p, adr):
        self.pSerial = p
        self.address = adr

    # 穿透指令
    def sendMsg(self, string):
        if self.address != -1:
            self.string = "@" + str(self.address) + string + "\r\n"
        else:
            self.string = string + "\r\n"
        self.pSerial.write(self.string.encode("utf-8"))
        time.sleep(0.1)

    # 运动设置
    def speed(self, num):
        self.num = num
        if self.num > 100:
            self.num == 100
        elif self.num < -100:
            self.num == -100
        self.num = "G6 F" + str(self.num)
        self.sendMsg(self.num)



