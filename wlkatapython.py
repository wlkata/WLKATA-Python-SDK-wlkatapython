'''
VERSION:0.0.9
'''
import serial
import time
import re
import tkinter as tk
from tkinter import ttk
from serial.tools import list_ports
import threading as th
import os


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
        if self.num == 0:
            self.sendMsg("M3 S0")
        elif self.num == 1:
            self.sendMsg("M3 S40")
        elif self.num == 2:
            self.sendMsg("M3 S60")
        else:
            self.sendMsg("M3 S0")

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
                self.data = self.__parse_response(self.line)
            else:
                self.data = -1
        else:
            return "error"

        time.sleep(0.1)
        return self.data

    # 正则表达式
    def __parse_response(self, line):
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

    # 末端状态查询
    def getpump(self):
        self.getStatus()
        return self.mirobot_state_all["pump"]

    # 状态查询/暂时没有用到
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

#1.0初版
#1.1根据wlkata_uart库进行更新，主要是舵机控制
class Mirobot_Serial_GUI:
    def __init__(self):
        self.line = 1.0
        self.Descartes_name=["X","Y","Z","A","B","C","D",]
        self. angle_name=["J1","J2","J3","J4","J5","J6"]
        self.label_lab=["label1","label2","label3","label4","label5","label6","label7"]
        self.coordinate_tk=["coordinate_tk1","coordinate_tk2","coordinate_tk3","coordinate_tk4","coordinate_tk5","coordinate_tk6","coordinate_tk7"]
        self.add_tk_button=["add_tk_button1","add_tk_button2","add_tk_button3","add_tk_button4","add_tk_button5","add_tk_button6","add_tk_button7"]
        self.cut_tk_button=["cut_tk_button1","cut_tk_button2","cut_tk_button3","cut_tk_button4","cut_tk_button5","cut_tk_button6","cut_tk_button7"]
        self.coordinate_X_list=["coordinate_X","coordinate_Y","coordinate_Z","coordinate_RX","coordinate_RY","coordinate_RZ"]

    def __State_binding_off(self):
        for i in range(7):
            self.coordinate_tk[i]['state'] = 'disabled'#X/Y/Z/A/B/C输入框禁用
            self. add_tk_button[i]['state'] = 'disabled'#加号按钮禁用
            self.cut_tk_button[i]['state'] = 'disabled'#减号按钮禁用
            self.add_tk_button[i].unbind("<Button-1>")#加号按钮取消绑定事件
            self.cut_tk_button[i].unbind("<Button-1>")#减号按钮取消绑定事件
        self.descartes_copy_button['state'] = 'disabled'#记录坐标按键
        self.getpump_copy_button['state'] = 'disabled'#记录末端按键
        self.restart_button['state'] = 'disabled'#重启按键
        self.homing_button['state'] = 'disabled'#回零按键
        self.zero_button['state'] = 'disabled'#初始位置按键
        self.serial_tk_button2['state'] = 'disabled'#连接/断开按键
        self.senmsg_tk_button['state'] = 'disabled'#发送按键
        self.descartes_OFF['state'] = 'disabled'#舵机关闭按键
        self.descartes_ON['state'] = 'disabled'#舵机打开按键
        self.descartes_close['state'] = 'disabled'#舵机断开按键
        self.gripper_close['state'] = 'disabled'#气泵关闭按键
        self.gripper_ON['state'] = 'disabled'#气泵开启按键
        self.gripper_OFF['state'] = 'disabled'#气泵关闭按键
        self.senmsg_tk_entry['state'] = 'disabled'#透传输入框
        self.coordinate_tk8['state'] = 'disabled'#步长输入框
        self.add_tk_button8['state'] = 'disabled'#加号按钮
        self.cut_tk_button8['state'] = 'disabled'#减号按钮
        self.axis7_copy_button['state'] = 'disabled'

        self.axis7_copy_button.unbind("<Button-1>")
        self.add_tk_button8.unbind("<Button-1>")#加号按钮取消绑定事件
        self.cut_tk_button8.unbind("<Button-1>")#减号按钮取消绑定事件
        self.descartes_copy_button.unbind("<Button-1>")
        self.root.unbind("<F1>")
        self.root.unbind("<F2>")
        self.root.unbind("<F3>")
        self.getpump_copy_button.unbind("<Button-1>")
        self.restart_button.unbind("<Button-1>")
        self.homing_button.unbind("<Button-1>")
        self.zero_button.unbind("<Button-1>")
        self.serial_tk_button2.unbind("<Button-1>")
        self.senmsg_tk_button.unbind("<Button-1>")
        self.descartes_OFF.unbind("<Button-1>")
        self.descartes_ON.unbind("<Button-1>")
        self.descartes_close.unbind("<Button-1>")
        self.gripper_close.unbind("<Button-1>")
        self.gripper_ON.unbind("<Button-1>")
        self.gripper_OFF.unbind("<Button-1>")

    def __State_binding_on(self):
        for i in range(7):
            self.coordinate_tk[i]['state'] = 'normal'#X/Y/Z/A/B/C输入框
            self.add_tk_button[i]['state'] = 'normal'#加号按钮
            self.cut_tk_button[i]['state'] = 'normal'#减号按钮
            self.add_tk_button[i].bind("<Button-1>", self.__coordinate_add_def)
            self.cut_tk_button[i].bind("<Button-1>", self.__coordinate_cut_def)

        self.descartes_copy_button['state'] = 'normal'#记录坐标按键
        self.getpump_copy_button['state'] = 'normal'
        self.restart_button['state'] = 'normal'#重启按键
        self.homing_button['state'] = 'normal'#回零按键
        self.zero_button['state'] = 'normal'#初始位置按键
        self.serial_tk_button2['state'] = 'normal'#连接/断开按键
        self.senmsg_tk_button['state'] = 'normal'#发送按键
        self.descartes_OFF['state'] = 'normal'#舵机关闭按键
        self.descartes_ON['state'] = 'normal'#舵机打开按键
        self.descartes_close['state'] = 'normal'#舵机断开按键
        self.gripper_close['state'] = 'normal'#气泵关闭按键
        self.gripper_ON['state'] = 'normal'#气泵开启按键
        self.gripper_OFF['state'] = 'normal'#气泵关闭按键
        self.senmsg_tk_entry['state'] = 'normal'#透传输入框
        self.coordinate_tk8['state'] = 'normal'
        self.add_tk_button8['state'] = 'normal'
        self.cut_tk_button8['state'] = 'normal'
        self.axis7_copy_button['state'] = 'normal'

        self.axis7_copy_button.bind("<Button-1>", self.__axis7_copy_button_def)
        self.serial_tk_button2.bind("<Button-1>", self.__serial_connect_def)
        self.senmsg_tk_button.bind("<Button-1>", self.__wlkatapython_sendmsg)
        self.descartes_copy_button.bind("<Button-1>", self.__descartes_copy_button_def)
        self.root.bind("<F1>",self.__descartes_copy_button_def)
        self.root.bind("<F2>",self.__getpump_copy_button_def)
        self.root.bind("<F3>",self.__axis7_copy_button_def)
        self.getpump_copy_button.bind("<Button-1>", self.__getpump_copy_button_def)
        self.restart_button.bind("<Button-1>", self.__restart_button_def)
        self.homing_button.bind("<Button-1>", self.__homing_def)
        self.zero_button.bind("<Button-1>", self.__zero_def)
        self.descartes_OFF.bind("<Button-1>", self.__descartes_OFF_def)
        self.descartes_ON.bind("<Button-1>", self.__descartes_ON_def)
        self.descartes_close.bind("<Button-1>", self.__descartes_close_def)
        self.gripper_close.bind("<Button-1>", self.__gripper_close_def)
        self.gripper_ON.bind("<Button-1>", self.__gripper_ON_def)
        self.gripper_OFF.bind("<Button-1>", self.__gripper_OFF_def)
        self.add_tk_button8.bind("<Button-1>", self.__coordinate_add_def8)
        self.cut_tk_button8.bind("<Button-1>", self.__coordinate_cut_def8)

    def __serial_numbers_def(self ,event):
        self.available_ports = []
        self.ports = list_ports.comports()
        if len(self.ports) == 0:
            print("No serial ports found.")
        else:
            for self.port in self.ports:
                self.available_ports.append(self.port.device)
                # print(port.device)
            self.serial_tk_entry['values']=self.available_ports
            # print(self.available_ports)
    #用于点击连接后，串口号自动填充到下拉列表中且切换刷新波特率等状态
    def __serial_connect_def(self,event):
        global ser,robot
        try:
            if self.serial_tk_button2['text'] == "Connect":
                # print(serial_tk_entry.get())
                self.ser = serial.Serial(self.serial_tk_entry.get(), self.serial_tk_bote_com.get())
                self.serial_tk_entry['state'] = 'disabled'
                self.serial_tk_bote_com['state'] = 'disabled'
                self.rs485_tk_entry['state'] = 'disabled'
                self.robot=Wlkata_UART()
                self.robot.init(self.ser,int(self.rs485_tk_entry.get()))
                self.serial_tk_button2.config(text="Break")
                try:
                    self.date_tk=self.robot.getStatus()
                    for i in range(6):
                        self.coordinate_tk[i].delete(0, tk.END)
                        self.coordinate_tk[i].insert(0, str(round(float(self.date_tk[self.coordinate_X_list[i]]),2)))
                except:
                    print("Error")
            else:
                self.ser.close()
                self.serial_tk_button2.config(text="Connect")
                self.serial_tk_entry['state'] = 'normal'
                self.serial_tk_bote_com['state'] = 'normal'
                self.rs485_tk_entry['state'] = 'normal'
        except serial.serialutil.SerialException as e:
            print(f"An error occurred: {e}")

    def __wlkatapython_sendmsg(self,event):
        global robot
        self.robot.sendMsg(str(self.senmsg_tk_entry.get()))

    def __root_getStater(self):
        global robot
        time_1=time.time()
        # print(time_1)
        try:
            while self.robot.getState()!="Idle":
                time_2=time.time()
                # print(time_2-time_1)
                if time_2-time_1>17:
                    break
            self.date_tk=self.robot.getStatus()
        except:
            self.ser.close()
            self.serial_tk_button2.config(text="Connect")
            self.serial_tk_entry['state'] = 'normal'
            self.serial_tk_bote_com['state'] = 'normal'
            self. rs485_tk_entry['state'] = 'normal'
            
            print("Error")
        else:
            for i in range(6):
                self.coordinate_tk[i].delete(0, tk.END)
                self.coordinate_tk[i].insert(0, str(round(float(self.date_tk[self.coordinate_X_list[i]]),2)))  
        finally:
            self.__State_binding_on()

    def __root_getStater2(self):
        global robot
        time.sleep(3)
        try:
            self.date_tk=self.robot.getStatus()
        except:
            self.ser.close()
            self.serial_tk_button2.config(text="Connect")
            self.serial_tk_entry['state'] = 'normal'
            self.serial_tk_bote_com['state'] = 'normal'
            self.rs485_tk_entry['state'] = 'normal'
            
            print("Error")
        else: 
            self.__State_binding_on()
            # print(date_tk)
            for i in range(6):
                self.coordinate_tk[i].delete(0, tk.END)
                self.coordinate_tk[i].insert(0, str(round(float(self.date_tk[self.coordinate_X_list[i]]),2)))

    def __homing_def(self,event):
        self.robot.homing()
        self.__State_binding_off()
        self.th_1=th.Thread(target=self.__root_getStater)
        self.th_1.start()

    def __zero_def(self,event):
        self.robot.zero()
        # print(robot.getState())
        if self.robot.getState()=="Idle" or self.robot.getState()=="Run":
            while self.robot.getState()!="Idle":
                # print(robot.getState())
                pass
            self.date_tk=self.robot.getStatus()
            for i in range(6):
                self.coordinate_tk[i].delete(0, tk.END)
                self.coordinate_tk[i].insert(0, str(round(float(self.date_tk[self.coordinate_X_list[i]]),2)))
        else:
            print("Error")

    def __descartes_OFF_def(self,event):
        self.robot.gripper(1)

    def __descartes_ON_def(self,event):
        self.robot.gripper(2)

    def __descartes_close_def(self,event):
        self.robot.gripper(0)

    def __gripper_close_def(self,event):
        self.robot.pump(0)

    def __gripper_ON_def(self,event):
        self.robot.pump(1)

    def __gripper_OFF_def(self,event):
        self.robot.pump(2)

    def __restart_button_def(self,event):
        global robot
        self.robot.restart()
        self.__State_binding_off()
        th_2=th.Thread(target=self.__root_getStater2)
        th_2.start()

    def __coordinate_add_def(self,event):
        i = event.widget.grid_info()["row"]
        self.value = round(float(self.coordinate_tk[i].get()), 2)
        self.coordinate_tk[i].delete(0, tk.END)
        self.coordinate_tk[i].insert(0, self.value + round(float(self.coordinate_tk8.get()), 2))
        #获取X/Y/X/RX/RY/RZ的值并加到一起
        self.coordinate_X=round(float(self.coordinate_tk[0].get()), 2)
        self.coordinate_Y=round(float(self.coordinate_tk[1].get()), 2)
        self.coordinate_Z=round(float(self.coordinate_tk[2].get()), 2)
        self.coordinate_RX=round(float(self.coordinate_tk[3].get()), 2)
        self.coordinate_RY=round(float(self.coordinate_tk[4].get()), 2)
        self.coordinate_RZ=round(float(self.coordinate_tk[5].get()), 2)
        self.coordinate_D=round(float(self.coordinate_tk[6].get()), 2)
        if i==6:
            self.coordinate_D="G91 G01 D"+str(round(float(self.coordinate_tk8.get()), 2))+" F2000"
            # print(coordinate_D)
            self.robot.sendMsg(self.coordinate_D)
        else:
            self.coordinate_XYZRXYZ="M20 G90 G00 X"+str(self.coordinate_X)+" Y"+str(self.coordinate_Y)+" Z"+str(self.coordinate_Z)+" A"+str(self.coordinate_RX)+" B"+str(self.coordinate_RY)+" C"+str(self.coordinate_RZ)
            # print(coordinate_XYZRXYZ)
            self.robot.sendMsg(self.coordinate_XYZRXYZ)

    def __coordinate_cut_def(self,event):
        i = event.widget.grid_info()["row"]
        self.value = round(float(self.coordinate_tk[i].get()), 2)
        self.coordinate_tk[i].delete(0, tk.END)
        self.coordinate_tk[i].insert(0, self.value - round(float(self.coordinate_tk8.get()), 2))
        #获取X/Y/X/RX/RY/RZ的值并加到一起
        self.coordinate_X=round(float(self.coordinate_tk[0].get()), 2)
        self.coordinate_Y=round(float(self.coordinate_tk[1].get()), 2)
        self.coordinate_Z=round(float(self.coordinate_tk[2].get()), 2)
        self.coordinate_RX=round(float(self.coordinate_tk[3].get()), 2)
        self.coordinate_RY=round(float(self.coordinate_tk[4].get()), 2)
        self.coordinate_RZ=round(float(self.coordinate_tk[5].get()), 2)
        self.coordinate_D=round(float(self.coordinate_tk[6].get()), 2)
        if i==6:
            self.coordinate_D="G91 G01 D-"+str(round(float(self.coordinate_tk8.get()), 2))+" F2000"
            # print(coordinate_D)
            self.robot.sendMsg(self.coordinate_D)
        else:
            self.coordinate_XYZRXYZ="M20 G90 G00 X"+str(self.coordinate_X)+" Y"+str(self.coordinate_Y)+" Z"+str(self.coordinate_Z)+" A"+str(self.coordinate_RX)+" B"+str(self.coordinate_RY)+" C"+str(self.coordinate_RZ)
            # print(coordinate_XYZRXYZ)
            self.robot.sendMsg(self.coordinate_XYZRXYZ)

    def __coordinate_add_def8(self,event):
        self.value = round(float(self.coordinate_tk8.get()), 2)
        self.coordinate_tk8.delete(0, tk.END)
        self.coordinate_tk8.insert(0, self.value + 1)

    def __coordinate_cut_def8(self,event):
        self.value = round(float(self.coordinate_tk8.get()), 2)
        self.coordinate_tk8.delete(0, tk.END)
        self.coordinate_tk8.insert(0, self.value - 1)

    def __descartes_copy_button_def(self,event):
        self.coordinate_X=round(float(self.coordinate_tk[0].get()), 2)
        self.coordinate_Y=round(float(self.coordinate_tk[1].get()), 2)
        self.coordinate_Z=round(float(self.coordinate_tk[2].get()), 2)
        self.coordinate_RX=round(float(self.coordinate_tk[3].get()), 2)
        self.coordinate_RY=round(float(self.coordinate_tk[4].get()), 2)
        self.coordinate_RZ=round(float(self.coordinate_tk[5].get()), 2)
        self.coordinate_XYZRXYZ="M20 G90 G00 X"+str(self.coordinate_X)+" Y"+str(self.coordinate_Y)+" Z"+str(self.coordinate_Z)+" A"+str(self.coordinate_RX)+" B"+str(self.coordinate_RY)+" C"+str(self.coordinate_RZ)+"\r\n"
        self.txt_copy.insert(self.line, self.coordinate_XYZRXYZ)
        self.line=self.line+1

    def __getpump_copy_button_def(self,event):
        try:
            self.getpump_copy="G3 S"+str(self.robot.getpump())+"\r\n"
        except:
            self.getpump_copy=None
        self.txt_copy.insert(self.line, self.getpump_copy)
        self.line=self.line+1

    def __axis7_copy_button_def(self,event):

        try:
            self.axis7_copy="G90 G01 D"+str(self.coordinate_tk[6].get())+" F1500\r\n"
        except:
            self.axis7_copy=None
        self.txt_copy.insert(self.line, self.axis7_copy)
        self.line=self.line+1

    def __angle_copy_button_def(self,event):
        for i in range(6):
            self.coordinate_tk[i]['state'] = 'normal'
    #写入txt_copy的值到txt_save目录下
    def __txt_preserve_def(self,event):
        with open(str(self.txt_save.get()), 'w') as f:
            f.write(self.txt_copy.get("1.0",tk.END))

    def Mirobot_GUI(self):
        self.root = tk.Tk()
        self.root.bind("<F1>",self.__descartes_copy_button_def)
        self.root.bind("<F2>",self.__getpump_copy_button_def)
        self.root.bind("<F3>",self.__axis7_copy_button_def)
        self.root.resizable(False, False)
        self.root.wm_attributes('-topmost', 1)#界面置于顶层
        #########共分为5个区域###########################################################
        # frame1: 显示串口号，刷新按钮，RS485地址
        # frame2: 机械臂笛卡尔加减界面
        # frame3: 气泵及夹爪的开关
        # frame4: 笛卡尔坐标的保存
        # frame5: Gcode文件的保存地址
        self.root.title("Mirobot_Robot_Serial1.1")
        self.frame1=tk.Frame(self.root,width=350,height=100)
        self.frame1.pack(side="top",fill="both",expand="yes")

        self.frame2=tk.Frame(self.root,width=350,height=300)
        self.frame2.pack(side="top",fill="both",expand="yes")

        self.frame3=tk.Frame(self.root,width=350,height=100)
        self.frame3.pack(side="top",fill="both",expand="yes")

        self.frame4=tk.Frame(self.root,width=350,height=100)
        self. frame4.pack(side="top",fill="both",expand="yes")

        self.frame5=tk.Frame(self.root,width=350,height=100)
        self.frame5.pack(side="top",fill="both",expand="yes")
        ###########################################################################frame1区域
        self.serial_tk_lable = ttk.Label(self.frame1, text="Serial:")
        self.serial_tk_lable.pack(side="left", padx=2, pady=2)


        self.serial_tk_entry =ttk.Combobox(self.frame1, width=7)
        self.serial_tk_entry.pack(side="left", padx=2, pady=2)
        self.serial_tk_entry.bind("<Button-1>", self.__serial_numbers_def)


        self.rs485_tk_lable=ttk.Label(self.frame1,text="  RS485\nAddress:", font=('Arial', 9))
        self.rs485_tk_lable.pack(side="left", padx=2, pady=2)

        self.rs485_tk_entry = ttk.Entry(self.frame1, width=8)
        self.rs485_tk_entry.pack(side="left", padx=2, pady=2)

        self.rs485_tk_entry.insert(0,-1)

        self.rs485_tk_bote_txt=ttk.Label(self.frame1, text="Baud rate:")
        self.rs485_tk_bote_txt.pack(side="left", padx=2, pady=2)


        self.serial_tk_bote_com =ttk.Combobox(self.frame1, width=7,values=["9600", "38400","115200"])
        self.serial_tk_bote_com.pack(side="left", padx=2, pady=2)

        self.serial_tk_bote_com.insert(0,"115200")


        self.serial_tk_button2 = ttk.Button(self.frame1, text="Connect",width=8)
        self.serial_tk_button2.pack(side="left", padx=2, pady=2)

        self.serial_tk_button2.bind("<Button-1>", self.__serial_connect_def)

        #####################################################################frame2区域
        self.frame2_1=tk.Frame(self.frame2,width=100,height=200)
        self.frame2_1.pack(side="left",fill="both",expand="yes")

        self.frame2_2=tk.Frame(self.frame2,width=100,height=200)
        self.frame2_2.pack(side="left",fill="both",expand="yes")

        self.frame2_3=tk.Frame(self.frame2,width=100,height=200)
        self.frame2_3.pack(side="left",fill="both",expand="yes")


        for i in range(7):
            self.label_lab[i] = ttk.Label(self.frame2_1, text=self.Descartes_name[i]+":", width=5, anchor="center")
            self.label_lab[i].grid(row=i, column=0,sticky="ew")
            self.coordinate_tk[i]=ttk.Entry(self.frame2_1, width=10)
            self.coordinate_tk[i].grid(row=i, column=1,sticky="ew")
            self.coordinate_tk[i].insert(0,0)
            self.add_tk_button[i]=ttk.Button(self.frame2_1, text="+",width=4)
            self.add_tk_button[i].grid(row=i, column=2,sticky="ew")
            self.add_tk_button[i].bind("<Button-1>", self.__coordinate_add_def)
            self.cut_tk_button[i]=ttk.Button(self.frame2_1, text="-",width=4)
            self.cut_tk_button[i].grid(row=i, column=3,sticky="ew")
            self.cut_tk_button[i].bind("<Button-1>", self.__coordinate_cut_def)

        self.label_lab8 = ttk.Label(self.frame2_1, text="Step:", width=5, anchor="center")
        self.label_lab8.grid(row=7, column=0,sticky="ew")
        self.coordinate_tk8=ttk.Entry(self.frame2_1, width=10)
        self.coordinate_tk8.grid(row=7, column=1,sticky="ew")
        self.coordinate_tk8.insert(0,5)
        self.add_tk_button8=ttk.Button(self.frame2_1, text="+",width=4)
        self.add_tk_button8.grid(row=7, column=2,sticky="ew")
        self.add_tk_button8.bind("<Button-1>", self.__coordinate_add_def8)
        self.cut_tk_button8=ttk.Button(self.frame2_1, text="-",width=4)
        self.cut_tk_button8.grid(row=7, column=3,sticky="ew")
        self.cut_tk_button8.bind("<Button-1>", self.__coordinate_cut_def8)

        self.senmsg_tk_txt=ttk.Label(self.frame2_1, text="G code:", width=8, anchor="center")
        self.senmsg_tk_txt.grid(row=8,column=0,sticky="ew")
        self.senmsg_tk_entry = ttk.Entry(self.frame2_1, width=15)
        self.senmsg_tk_entry.grid(row=8, column=1,columnspan=2,sticky="w")
        self.senmsg_tk_entry.insert(0,"o100")    
        self.senmsg_tk_button=ttk.Button(self.frame2_1, text="Send",width=4)
        self.senmsg_tk_button.grid(row=8, column=3,sticky="w")
        self.senmsg_tk_button.bind("<Button-1>", self.__wlkatapython_sendmsg)


        self.descartes_copy_button=ttk.Button(self.frame2_2, text="Coordinate\n  Copy(F1)",width=12)
        self.descartes_copy_button.grid(row=0, column=0)
        self.descartes_copy_button.bind("<Button-1>", self.__descartes_copy_button_def)

        self.getpump_copy_button=ttk.Button(self.frame2_2, text="Terminal\nCopy(F2)",width=12)
        self.getpump_copy_button.grid(row=1, column=0)
        self.getpump_copy_button.bind("<Button-1>", self.__getpump_copy_button_def)

        self.axis7_copy_button=ttk.Button(self.frame2_2, text="  7-axis\nCopy(F3)",width=12)
        self.axis7_copy_button.grid(row=2, column=0)
        self.axis7_copy_button.bind("<Button-1>", self.__axis7_copy_button_def)

        self.restart_button=ttk.Button(self.frame2_3, text="Restart",width=10)
        self.restart_button.grid(row=0, column=0)
        self.restart_button.bind("<Button-1>", self.__restart_button_def)
        self.homing_button=ttk.Button(self.frame2_3, text="Homing",width=10)
        self.homing_button.grid(row=1, column=0)
        self.homing_button.bind("<Button-1>", self.__homing_def)


        self.zero_button=ttk.Button(self.frame2_3, text="Zero",width=10)
        self.zero_button.grid(row=2, column=0)
        self.zero_button.bind("<Button-1>", self.__zero_def)
        ########################################Frame3
        self.descartes_lable=ttk.Label(self.frame3,text="Servo:",width=6)  
        self.descartes_lable.pack(side="left", padx=5, pady=5)  

        self.descartes_OFF=ttk.Button(self.frame3,text="Open",width=5)  
        self.descartes_OFF.pack(side="left", padx=1, pady=1)
        self.descartes_OFF.bind("<Button-1>", self.__descartes_OFF_def)
        self.descartes_ON=ttk.Button(self.frame3,text="Close",width=5)
        self.descartes_ON.pack(side="left", padx=1, pady=1)
        self.descartes_ON.bind("<Button-1>", self.__descartes_ON_def)
        self.descartes_close=ttk.Button(self.frame3,text="Break",width=5)
        self.descartes_close.pack(side="left", padx=1, pady=1)
        self.descartes_close.bind("<Button-1>", self.__descartes_close_def)

        self.gripper_close=ttk.Button(self.frame3,text="Break",width=5)
        self.gripper_close.pack(side="right", padx=1, pady=1)
        self.gripper_close.bind("<Button-1>", self.__gripper_close_def)
        self.gripper_ON=ttk.Button(self.frame3,text="Inhale",width=5)
        self.gripper_ON.pack(side="right", padx=1, pady=1)
        self.gripper_ON.bind("<Button-1>", self.__gripper_ON_def)
        self.gripper_OFF=ttk.Button(self.frame3,text="Blow",width=5)  
        self.gripper_OFF.pack(side="right", padx=1, pady=1)
        self.gripper_OFF.bind("<Button-1>", self.__gripper_OFF_def)
        self.gripper_lable=ttk.Label(self.frame3,text="Air pump:")  
        self.gripper_lable.pack(side="right", padx=5, pady=5)  

        #############################fram4
        self.txt_copy=tk.Text(self.frame4,height=10,width=62)
        self.txt_copy.pack(side="left")
        # 创建一个 Scrollbar 部件，并将其放在 Text 部件的右侧
        self.scrollbar = tk.Scrollbar(self.frame4, orient="vertical", command=self.txt_copy.yview)
        self.scrollbar.pack(side="left", fill="y")
        # 将 Scrollbar 与 Text 部件关联
        self.txt_copy.configure(yscrollcommand=self.scrollbar.set)
        # 将 Text 部件添加到 frame4
        self.txt_copy.pack(side="left")

        ########################frame5
        self.txt_save=tk.Entry(self.frame5,width=50)
        # self.txt_save.insert(0, "C:\\Users\\Public\\Documents\\main.txt")  # 插入默认值
        if os.name == 'nt':  # Windows系统
            self.default_path = os.path.expanduser('~\Documents')
        else:  # Linux或macOS系统
            self.default_path = "/opt"
        self.txt_save.insert(0, os.path.join(self.default_path, 'main.txt'))  # 插入默认值
        self.txt_save.pack(side="left", padx=5, pady=5)
        self.txt_preserve=ttk.Button(self.frame5,text="Save",width=5)
        self.txt_preserve.pack(side="left", padx=5, pady=5)
        self.txt_preserve.bind("<Button-1>", self.__txt_preserve_def)


        self.root.mainloop()


if __name__ == '__main__':
    Mirobot_GUI = Mirobot_Serial_GUI()
    Mirobot_GUI.Mirobot_GUI()
    # serial1=serial.Serial("COM3",115200)
    # mirobot = Wlkata_UART()
    # mirobot.init(serial1,-1)
    # mirobot.restart()
    # time.sleep(3)
    # mirobot.homing()
    # while mirobot.getState()!="Idle":
    #     pass
    # print(mirobot.getState())