"""Base class for WLKATA robotic arm and controller communication.

This class provides the core functionality for communicating with WLKATA robotic
devices via UART or RS485 interfaces. It includes methods for sending commands,
receiving responses, and basic robot control operations.

All WLKATA robot classes inherit from this base class.
"""

import serial
import time
import re


class WLKATA_UART:
    def __init__(self):
        """Initialize the WLKATA UART communication interface.

        Sets up internal state variables for robot status tracking and GPIO control.
        """
        self.__message_flag = False
        self.mirobot_state_all = {
            "state": "-1",
            "angle_A": -1, "angle_B": -1, "angle_C": -1, "angle_D": -1,
            "angle_X": -1, "angle_Y": -1, "angle_Z": -1,
            "coordinate_X": -1, "coordinate_Y": -1, "coordinate_Z": -1,
            "coordinate_RX": -1, "coordinate_RY": -1, "coordinate_RZ": -1,
            "pump": -1, "valve": -1, "mooe": -1
        }
        self.gpio_state = [0, 0, 0, 0]
        

    def message_print(self, flag):
        """Enable or disable message printing for debugging.

        Args:
            flag (bool): True to enable printing of sent/received messages,
                        False to disable.
        """
        self.__message_flag = flag
    
    def read_message(self):
        """Read a message from the serial port.

        Returns:
            str: The received message, or "read error" if no data available.
        """
        self.line = " "
        if self.pSerial.in_waiting > 0:
            self.line = self.pSerial.readline().decode('utf-8').strip()
            if self.__message_flag:
                print("read:\t", end="")
                print(self.line)
            return self.line
        else:
            return "read error"

    def sendMsg(self, string):
        """Send a command string to the robot.

        Args:
            string (str): The command string to send (without \r\n).
        """
        if self.address != -1:
            self.string = "@" + str(self.address) + string + "\r\n"
        else:
            self.string = string + "\r\n"
        self.pSerial.write(self.string.encode("utf-8"))
        if self.__message_flag:
            print("write:\t", end="")
            print(self.string)
        time.sleep(0.1)
    

    def init(self, p, adr):
        """Initialize the serial communication.

        Args:
            p: Serial port object (e.g., serial.Serial instance).
            adr (int): Robot address for RS485 (-1 for UART mode, 0-255 for RS485).
        """
        self.pSerial = p
        self.address = adr


    def homing(self, mode=8):
        """Perform robot homing (return to home position).

        Args:
            mode (int): Homing mode (0-10). Defaults to 8.
                       Different modes may home different axes or use different procedures.
        """
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
            self.sendMsg("o105=8")
        # Note: Homing is asynchronous; the robot may still be moving after this call

    def runFile(self, fileName, num=False):
        """Execute an offline program file stored on the robot controller.

        Args:
            fileName (str or int): Name or number of the file to execute.
            num (bool): If True, use o112 command (with number), else o111.

        Returns:
            int: 1 on success.

        Raises:
            Exception: If file execution fails or returns error.
        """
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

        self.var_read_message = self.read_message()
        if self.var_read_message == "ok":
            return 1
        elif self.var_read_message == "error":
            self.__error_except(self.runFile, 4)
        else:
            self.__error_except(self.runFile, 1)

    def cancellation(self):
        """Stop the current robot movement or action immediately.

        Returns:
            int: 1 on success.

        Raises:
            Exception: If the stop command fails.
        """
        self.sendMsg("o117")
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.cancellation, 1)

    def gripper(self, num):
        """Control the gripper (if equipped).

        Args:
            num (int): Gripper command:
                      0 - Open/Release
                      1 - Close/Grip (medium force)
                      2 - Close/Grip (high force)

        Returns:
            int: 1 on success.

        Raises:
            Exception: If gripper control fails.
        """
        self.num = num
        if self.num == 0:
            self.sendMsg("M3 S0")
        elif self.num == 1:
            self.sendMsg("M3 S40")
        elif self.num == 2:
            self.sendMsg("M3 S60")
        else:
            self.sendMsg("M3 S0")
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.gripper, 1)

    #Pump control function
    # 气泵控制函数

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
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.pump, 1)

    #PWM control function, num range 0-1000
    # PWM控制函数，num取值范围0-1000

    def pwmWrite(self, num):
        self.num = "M3 S" + str(num)
        self.sendMsg(self.num)
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.pwmWrite, 1)

    def zero(self):
        """Move the robot to the zero position in angle mode.

        This moves all axes to their zero/reference positions.
        """
        self.sendMsg("M21 G90 G00 X0 Y0 Z0 A0 B0 C00")
        # Note: Zeroing is asynchronous; position may not be reached immediately

    def writecoordinate(self, motion, position, x, y, z, a, b, c):
        """Move the robot to specified Cartesian coordinates.

        Args:
            motion (int): Movement type:
                         0 - Fast (G00)
                         1 - Linear (G01)
                         2 - Joint (G05)
            position (int): Coordinate mode:
                           0 - Absolute (G90)
                           1 - Incremental (G91)
            x (float): X coordinate
            y (float): Y coordinate
            z (float): Z coordinate
            a (float): A rotation (RX)
            b (float): B rotation (RY)
            c (float): C rotation (RZ)
        """
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
        # if self.read_message() == "ok":
        #     return 1
        # else:
        #     self.__error_except(self.writecoordinate, 1)

    #Robot speed control, num:0-100
    # 机械臂速度控制，num:0-100

    def speed(self, num):
        self.num = "F" + str(num)
        self.sendMsg(self.num)
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.speed, 1)

    """Robot angle control function
    position: 0-absolute movement 1-incremental movement
     x/y/z/a/b/c: angles of 1-6 axes of the robot
    """
    # 机械臂角度控制函数
    # position: 0-绝对值运动 1-增量值运动
    # x/y/z/a/b/c: 机械臂1-6轴角度值

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
        # if self.read_message() == "ok":
        #     return 1
        # else:
        #     self.__error_except(self.writeangle, 1)

    """Robot 7th axis movement
    motion:0-fast movement 1-linear movement
    position: 0-absolute movement 1-incremental movement
    """
    # 机械臂第7轴运动
    # motion:0-快速运动 1-直线运动
    # position: 0-绝对值运动 1-增量值运动

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
        # if self.read_message() == "ok":
        #     return 1
        # else:
        #     self.__error_except(self.writeexpand, 1)

    #Robot restart
    # 机械臂重启

    def restart(self):
        self.sendMsg("o100")
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.restart, 1)

    def version(self):
        """Get the firmware version of the robot controller.

        Note: Currently only available in UART mode, not RS485.

        Returns:
            tuple: (controller_version, robot_version) or "Query failed" on timeout.

        Raises:
            UnicodeDecodeError: If response cannot be decoded.
        """
        self.lina = ""
        self.lina1 = ""

        self.pSerial.flushInput()
        self.pSerial.flushOutput()
        self.sendMsg("$V")

        timeout_cnt = 0

        while True:
            if timeout_cnt >= 5:
                return "Query failed"

            self.lina = self.pSerial.readline().decode('utf-8').strip()
            self.lina1 = self.pSerial.readline().decode('utf-8').strip()

            if self.lina.startswith('EXbox') and self.lina1.startswith(
                    'Mirobot'):
                break

            timeout_cnt += 1
            time.sleep(0.1)

        return self.lina, self.lina1

    #Error and exception, built-in function
    # 错误和异常，内置函数

    def __error_except(self, f, num):
        if num == 1:
            raise Exception(f"{f.__name__}: No reply - 'ok'")
        elif num == 2:
            raise Exception(f"{f.__name__}: parameter error")
        elif num == 3:
            raise Exception(f"{f.__name__}: regular expression error")
        elif num == 4:
            raise Exception(f"{f.__name__}: File run error")
        else:
            pass

    def getStatus(self):
        """Query and update the full status of the robot.

        Sends a '?' command to get current position, angles, and state.

        Returns:
            dict or str: Robot status dictionary or "error" if no response.
        """
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

    #Regular expression for the full status of the robot
    # 机械臂全部状态的正则表达式

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
            return "parse error"

    #Get robot state
    # 获取机械臂状态

    def getState(self):
        self.getStatus()
        return self.mirobot_state_all["state"]

    def getAngle(self, num):
        """Get the angle of a specific robot axis.

        Args:
            num (int): Axis number (1-7):
                      1=X, 2=Y, 3=Z, 4=A, 5=B, 6=C, 7=D

        Returns:
            float: Current angle of the specified axis.

        Raises:
            Exception: If axis number is invalid.
        """
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
            self.__error_except(self.getAngle, 2)

    def getcoordinate(self, num):
        """Get the Cartesian coordinate of the robot end effector.

        Args:
            num (int): Coordinate axis (1-6):
                      1=X, 2=Y, 3=Z, 4=RX, 5=RY, 6=RZ

        Returns:
            float: Current coordinate value.

        Raises:
            Exception: If coordinate number is invalid.
        """
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
            self.__error_except(self.getcoordinate, 2)

    #Get end state
    # 获取末端状态

    def getpump(self):
        self.getStatus()
        return self.mirobot_state_all["pump"]

    #Get robot motion mode
    # 获取机械臂运动模式

    def getmooe(self):
        self.getStatus()
        return self.mirobot_state_all["mooe"]

   

    def gpio_init(self):
        """Initialize GPIO pins (disable all enables).

        Sets all GPIO enable states to 0 (disabled).

        Returns:
            int: 1 on success.

        Raises:
            Exception: If GPIO initialization fails.
        """
        for i in range(0, 4):
            self.gpio_state[i] = 0
        self.var_gpio_state = "o132=" + str(self.gpio_state[0]) + "," + str(self.gpio_state[1]) + "," + str(
            self.gpio_state[2]) + "," + str(self.gpio_state[3])
        self.sendMsg(self.var_gpio_state)
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.gpio_init, 1)

    #Write GPIO mode
    # gpio模式写入

    def gpio_mode_write(self, name, num):
        self.var_name = name.capitalize()
        self.var_num = num
        if self.var_name == "A0":
            self.var_gpio_state = "o130=" + str(self.var_num) + ",,,"
        elif self.var_name == "A1":
            self.var_gpio_state = "o130=," + str(self.var_num) + ",,"
        elif self.var_name == "D0":
            self.var_gpio_state = "o130=,," + str(self.var_num) + ","
        elif self.var_name == "D1":
            self.var_gpio_state = "o130=,,," + str(self.var_num)
        else:
            self.__error_except(self.gpio_mode_write, 2)
        self.sendMsg(self.var_gpio_state)

        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.gpio_mode_write, 1)

    #Read GPIO mode
    # gpio模式读取

    def gpio_mode_read(self, name):
        self.var_name = name.capitalize()
        self.sendMsg("o130?")
        self.var_mode_num = self.read_message()
        self.var_mode_num1 = self.read_message()
        match = re.match('^([\d]+),([\d]+),([\d]+),([\d]+)$', self.var_mode_num)
        if match:
            if self.var_name == "A0":
                return match.group(1)
            elif self.var_name == "A1":
                return match.group(2)
            elif self.var_name == "D0":
                return match.group(3)
            elif self.var_name == "D1":
                return match.group(4)
            else:
                self.__error_except(self.gpio_mode_read, 2)
        else:
            self.__error_except(self.gpio_mode_read, 3)

    #Write GPIO digital/analog output
    # gpio数字、模拟输出写入

    def gpio_output_write(self, name, num):
        self.var_name = name.capitalize()
        self.var_num = num
        if self.var_name == "A0":
            self.var_gpio_num = "o131=" + str(self.var_num) + ",,,"
        elif self.var_name == "A1":
            self.var_gpio_num = "o131=," + str(self.var_num) + ",,"
        elif self.var_name == "D0":
            self.var_gpio_num = "o131=,," + str(self.var_num) + ","
        elif self.var_name == "D1":
            self.var_gpio_num = "o131=,,," + str(self.var_num)
        else:
            self.__error_except(self.gpio_output_write, 2)

        self.sendMsg(self.var_gpio_num)
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.gpio_output_write, 1)

    #Read GPIO input value
    # gpio输入值读取

    def gpio_input_read(self, name):
        self.var_name = name.capitalize()
        self.sendMsg("o131?")
        self.var_mode_num = self.read_message()
        self.var_mode_num1 = self.read_message()
        match = re.match('^([\d]+),([\d]+),([\d]+),([\d]+)$', self.var_mode_num)
        if match:
            if self.var_name == "A0":
                return match.group(1)
            elif self.var_name == "A1":
                return match.group(2)
            elif self.var_name == "D0":
                return match.group(3)
            elif self.var_name == "D1":
                return match.group(4)
            else:
                self.__error_except(self.gpio_input_read, 2)
        else:
            self.__error_except(self.gpio_input_read, 3)

    #Write GPIO enable
    # gpio使能写入

    def gpio_enable_write(self, name, num):
        self.var_name = name.capitalize()
        self.var_num = num
        if self.var_name == "A0":
            self.var_gpio_num = "o132=" + str(self.var_num) + ",,,"
        elif self.var_name == "A1":
            self.var_gpio_num = "o132=," + str(self.var_num) + ",,"
        elif self.var_name == "D0":
            self.var_gpio_num = "o132=,," + str(self.var_num) + ","
        elif self.var_name == "D1":
            self.var_gpio_num = "o132=,,," + str(self.var_num)
        else:
            self.__error_except(self.gpio_enable_write, 2)

        self.sendMsg(self.var_gpio_num)
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.gpio_enable_write, 1)

    #Read GPIO enable
    # gpio使能读取

    def gpio_enable_read(self, name):
        self.var_name = name.capitalize()
        self.sendMsg("o132?")
        self.var_mode_num = self.read_message()
        self.var_mode_num1 = self.read_message()
        match = re.match('^([\d]+),([\d]+),([\d]+),([\d]+)$', self.var_mode_num)
        if match:
            if self.var_name == "A0":
                return match.group(1)
            elif self.var_name == "A1":
                return match.group(2)
            elif self.var_name == "D0":
                return match.group(3)
            elif self.var_name == "D1":
                return match.group(4)
            else:
                self.__error_except(self.gpio_enable_read, 2)
        else:
            self.__error_except(self.gpio_enable_read, 3)

    #Write GPIO pin trigger threshold
    # gpio引脚触发阈值写入

    def gpio_threshold_write(self, name, num):
        self.var_name = name.capitalize()
        self.var_num = num
        if self.var_name == "A0":
            self.var_gpio_num = "o133=" + str(self.var_num) + ",,,"
        elif self.var_name == "A1":
            self.var_gpio_num = "o133=," + str(self.var_num) + ",,"
        elif self.var_name == "D0":
            self.var_gpio_num = "o133=,," + str(self.var_num) + ","
        elif self.var_name == "D1":
            self.var_gpio_num = "o133=,,," + str(self.var_num)
        else:
            self.__error_except(self.gpio_threshold_write, 2)
        self.sendMsg(self.var_gpio_num)
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.gpio_threshold_write, 1)

    #Read GPIO pin trigger threshold
    # gpio引脚触发阈值读取

    def gpio_threshold_read(self, name):
        self.var_name = name.capitalize()
        self.sendMsg("o133?")
        self.var_mode_num = self.read_message()
        self.var_mode_num1 = self.read_message()
        match = re.match('^([\d]+),([\d]+),([\d]+),([\d]+)$', self.var_mode_num)
        if match:
            if self.var_name == "A0":
                return match.group(1)
            elif self.var_name == "A1":
                return match.group(2)
            elif self.var_name == "D0":
                return match.group(3)
            elif self.var_name == "D1":
                return match.group(4)
            else:
                self.__error_except(self.gpio_threshold_read, 2)
        else:
            self.__error_except(self.gpio_threshold_read, 3)

    #Write GPIO pin trigger file
    # gpio引脚触发文件写入

    def gpio_enable_file_write(self, name, num):
        self.var_name = name.capitalize()
        self.var_num = num
        if self.var_name == "A0":
            self.var_gpio_num = "o134=" + str(self.var_num) + ",,,"
        elif self.var_name == "A1":
            self.var_gpio_num = "o134=," + str(self.var_num) + ",,"
        elif self.var_name == "D0":
            self.var_gpio_num = "o134=,," + str(self.var_num) + ","
        elif self.var_name == "D1":
            self.var_gpio_num = "o134=,,," + str(self.var_num)
        else:
            self.__error_except(self.gpio_enable_file_write, 2)
        self.sendMsg(self.var_gpio_num)
        if self.read_message() == "ok":
            return 1
        else:
            self.__error_except(self.gpio_enable_file_write, 1)

    #Read GPIO pin trigger file
    # gpio引脚触发文件读取

    def gpio_enable_file_read(self, name):
        self.var_name = name.capitalize()
        self.sendMsg("o134?")
        self.var_mode_num = self.read_message()
        self.var_mode_num1 = self.read_message()
        match = re.match('^(.*),(.*),(.*),(.*)$', self.var_mode_num)
        if match:
            if self.var_name == "A0":
                return match.group(1)
            elif self.var_name == "A1":
                return match.group(2)
            elif self.var_name == "D0":
                return match.group(3)
            elif self.var_name == "D1":
                return match.group(4)
            else:
                self.__error_except(self.gpio_enable_file_read, 2)
        else:
            self.__error_except(self.gpio_enable_file_read, 3)

    