from Mirobot_robot.Mirobot_UART import Mirobot_UART

import serial
import time
import tkinter as tk
from tkinter import ttk
from serial.tools import list_ports
import threading as th
import os

# Mirobot GUI界面
# Mirobot GUI interface

class Mirobot_Serial_GUI:
    def __init__(self):
        self.line = 1.0
        self.Descartes_name = ["X", "Y", "Z", "A", "B", "C", "D", ]
        self.angle_name = ["J1", "J2", "J3", "J4", "J5", "J6"]
        self.label_lab = ["label1", "label2", "label3", "label4", "label5", "label6", "label7"]
        self.coordinate_tk = ["coordinate_tk1", "coordinate_tk2", "coordinate_tk3", "coordinate_tk4", "coordinate_tk5",
                              "coordinate_tk6", "coordinate_tk7"]
        self.add_tk_button = ["add_tk_button1", "add_tk_button2", "add_tk_button3", "add_tk_button4", "add_tk_button5",
                              "add_tk_button6", "add_tk_button7"]
        self.cut_tk_button = ["cut_tk_button1", "cut_tk_button2", "cut_tk_button3", "cut_tk_button4", "cut_tk_button5",
                              "cut_tk_button6", "cut_tk_button7"]
        self.coordinate_X_list = ["coordinate_X", "coordinate_Y", "coordinate_Z", "coordinate_RX", "coordinate_RY",
                                  "coordinate_RZ"]
        self.angle_list = ["angle_X", "angle_Y", "angle_Z", "angle_A", "angle_B", "angle_C", "angle_D"]

    def __State_binding_off(self):
        for i in range(7):
            self.coordinate_tk[i]['state'] = 'disabled'
            self.add_tk_button[i]['state'] = 'disabled'
            self.cut_tk_button[i]['state'] = 'disabled'
            self.add_tk_button[i].unbind("<Button-1>")
            self.cut_tk_button[i].unbind("<Button-1>")
        self.descartes_copy_button['state'] = 'disabled'
        self.getpump_copy_button['state'] = 'disabled'
        self.restart_button['state'] = 'disabled'
        self.homing_button['state'] = 'disabled'
        self.zero_button['state'] = 'disabled'
        self.serial_tk_button2['state'] = 'disabled'
        self.senmsg_tk_button['state'] = 'disabled'
        self.descartes_OFF['state'] = 'disabled'
        self.descartes_ON['state'] = 'disabled'
        self.descartes_close['state'] = 'disabled'
        self.gripper_close['state'] = 'disabled'
        self.gripper_ON['state'] = 'disabled'
        self.gripper_OFF['state'] = 'disabled'
        self.senmsg_tk_entry['state'] = 'disabled'
        self.coordinate_tk8['state'] = 'disabled'
        self.add_tk_button8['state'] = 'disabled'
        self.cut_tk_button8['state'] = 'disabled'
        self.axis7_copy_button['state'] = 'disabled'

        self.axis7_copy_button.unbind("<Button-1>")
        self.add_tk_button8.unbind("<Button-1>")
        self.cut_tk_button8.unbind("<Button-1>")
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
            self.coordinate_tk[i]['state'] = 'normal'
            self.add_tk_button[i]['state'] = 'normal'
            self.cut_tk_button[i]['state'] = 'normal'
            self.add_tk_button[i].bind("<Button-1>", self.__coordinate_add_def)
            self.cut_tk_button[i].bind("<Button-1>", self.__coordinate_cut_def)

        self.descartes_copy_button['state'] = 'normal'
        self.getpump_copy_button['state'] = 'normal'
        self.restart_button['state'] = 'normal'
        self.homing_button['state'] = 'normal'
        self.zero_button['state'] = 'normal'
        self.serial_tk_button2['state'] = 'normal'
        self.senmsg_tk_button['state'] = 'normal'
        self.descartes_OFF['state'] = 'normal'
        self.descartes_ON['state'] = 'normal'
        self.descartes_close['state'] = 'normal'
        self.gripper_close['state'] = 'normal'
        self.gripper_ON['state'] = 'normal'
        self.gripper_OFF['state'] = 'normal'
        self.senmsg_tk_entry['state'] = 'normal'
        self.coordinate_tk8['state'] = 'normal'
        self.add_tk_button8['state'] = 'normal'
        self.cut_tk_button8['state'] = 'normal'
        self.axis7_copy_button['state'] = 'normal'

        self.axis7_copy_button.bind("<Button-1>", self.__axis7_copy_button_def)
        self.serial_tk_button2.bind("<Button-1>", self.__serial_connect_def)
        self.senmsg_tk_button.bind("<Button-1>", self.__wlkatapython_sendmsg)
        self.descartes_copy_button.bind("<Button-1>", self.__descartes_copy_button_def)
        self.root.bind("<F1>", self.__descartes_copy_button_def)
        self.root.bind("<F2>", self.__getpump_copy_button_def)
        self.root.bind("<F3>", self.__axis7_copy_button_def)
        self.getpump_copy_button.bind("<Button-1>", self.__getpump_copy_button_def)
        self.restart_button.bind("<Button-1>", self.__restart_button_def)
        self.homing_button.bind("<Button-1>", self.__homing_def)
        self.zero_button.bind("<Button-1>", self.__zero_def)
        self.descartes_OFF.bind("<Button-1>", self.__descartes_ON_def)
        self.descartes_ON.bind("<Button-1>", self.__descartes_OFF_def)
        self.descartes_close.bind("<Button-1>", self.__descartes_close_def)
        self.gripper_close.bind("<Button-1>", self.__gripper_close_def)
        self.gripper_ON.bind("<Button-1>", self.__gripper_ON_def)
        self.gripper_OFF.bind("<Button-1>", self.__gripper_OFF_def)
        self.add_tk_button8.bind("<Button-1>", self.__coordinate_add_def8)
        self.cut_tk_button8.bind("<Button-1>", self.__coordinate_cut_def8)

    def __serial_numbers_def(self, event):
        self.available_ports = []
        self.ports = list_ports.comports()
        if len(self.ports) == 0:
            print("No serial ports found.")
        else:
            for self.port in self.ports:
                self.available_ports.append(self.port.device)
                # print(port.device)
            self.serial_tk_entry['values'] = self.available_ports
            # print(self.available_ports)

    def __serial_connect_def(self, event):
        global ser, robot
        try:
            if self.serial_tk_button2['text'] == "Connect":
                # print(serial_tk_entry.get())
                self.ser = serial.Serial(self.serial_tk_entry.get(), self.serial_tk_bote_com.get())
                self.serial_tk_entry['state'] = 'disabled'
                self.serial_tk_bote_com['state'] = 'disabled'
                self.rs485_tk_entry['state'] = 'disabled'
                self.robot = Mirobot_UART()
                self.robot.init(self.ser, int(self.rs485_tk_entry.get()))
                self.serial_tk_button2.config(text="Break")
                try:
                    self.date_tk = self.robot.getStatus()
                    for i in range(6):
                        self.coordinate_tk[i].delete(0, tk.END)
                        self.coordinate_tk[i].insert(0, str(round(float(self.date_tk[self.coordinate_X_list[i]]), 2)))
                    self.coordinate_tk[6].delete(0, tk.END)
                    self.coordinate_tk[6].insert(0, str(round(float(self.date_tk[self.angle_list[6]]), 2)))
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

    def __wlkatapython_sendmsg(self, event):
        global robot
        self.robot.sendMsg(str(self.senmsg_tk_entry.get()))

    def __root_getStater(self):
        global robot
        time_1 = time.time()
        # print(time_1)
        try:
            while self.robot.getState() != "Idle":
                time_2 = time.time()
                # print(time_2-time_1)
                if time_2 - time_1 > 17:
                    break
            self.date_tk = self.robot.getStatus()
        except:
            self.ser.close()
            self.serial_tk_button2.config(text="Connect")
            self.serial_tk_entry['state'] = 'normal'
            self.serial_tk_bote_com['state'] = 'normal'
            self.rs485_tk_entry['state'] = 'normal'

            print("Error")
        else:
            pass
            # for i in range(6):
            #     self.coordinate_tk[i].delete(0, tk.END)
            #     self.coordinate_tk[i].insert(0, str(round(float(self.date_tk[self.coordinate_X_list[i]]), 2)))
            # self.coordinate_tk[6].delete(0, tk.END)
            # self.coordinate_tk[6].insert(0, str(round(float(self.date_tk[self.angle_list[6]]), 2)))
        finally:
            self.__State_binding_on()

    def __root_getStater2(self):
        global robot
        time.sleep(3)
        try:
            self.date_tk = self.robot.getStatus()
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
                self.coordinate_tk[i].insert(0, str(round(float(self.date_tk[self.coordinate_X_list[i]]), 2)))
            self.coordinate_tk[6].delete(0, tk.END)
            self.coordinate_tk[6].insert(0, str(round(float(self.date_tk[self.angle_list[6]]), 2)))

    def __homing_def(self, event):
        self.robot.homing()
        self.__State_binding_off()
        self.th_1 = th.Thread(target=self.__root_getStater)
        self.th_1.start()

    def __zero_def(self, event):
        self.robot.zero()
        # print(robot.getState())
        if self.robot.getState() == "Idle" or self.robot.getState() == "Run":
            while self.robot.getState() != "Idle":
                # print(self.robot.getState())
                pass
            self.date_tk = self.robot.getStatus()
            # print(self.date_tk)
            for i in range(6):
                self.coordinate_tk[i].delete(0, tk.END)
                self.coordinate_tk[i].insert(0, str(round(float(self.date_tk[self.coordinate_X_list[i]]), 2)))

            self.coordinate_tk[6].delete(0, tk.END)
            self.coordinate_tk[6].insert(0, str(round(float(self.date_tk[self.angle_list[6]]), 2)))
        else:
            print("Error")

    def __descartes_OFF_def(self, event):
        self.robot.gripper(2)

    def __descartes_ON_def(self, event):
        self.robot.gripper(1)

    def __descartes_close_def(self, event):
        self.robot.gripper(0)

    def __gripper_close_def(self, event):
        self.robot.pump(0)

    def __gripper_ON_def(self, event):
        self.robot.pump(1)

    def __gripper_OFF_def(self, event):
        self.robot.pump(2)

    def __restart_button_def(self, event):
        global robot
        self.robot.restart()
        self.__State_binding_off()
        th_2 = th.Thread(target=self.__root_getStater2)
        th_2.start()

    def __coordinate_add_def(self, event):
        i = event.widget.grid_info()["row"]
        self.value = round(float(self.coordinate_tk[i].get()), 2)
        self.coordinate_tk[i].delete(0, tk.END)
        self.coordinate_tk[i].insert(0, self.value + round(float(self.coordinate_tk8.get()), 2))
        # 获取X/Y/X/RX/RY/RZ的值并加到一起
        self.coordinate_X = round(float(self.coordinate_tk[0].get()), 2)
        self.coordinate_Y = round(float(self.coordinate_tk[1].get()), 2)
        self.coordinate_Z = round(float(self.coordinate_tk[2].get()), 2)
        self.coordinate_RX = round(float(self.coordinate_tk[3].get()), 2)
        self.coordinate_RY = round(float(self.coordinate_tk[4].get()), 2)
        self.coordinate_RZ = round(float(self.coordinate_tk[5].get()), 2)
        self.coordinate_D = round(float(self.coordinate_tk[6].get()), 2)
        if i == 6:
            self.coordinate_D = "G91 G01 D" + str(round(float(self.coordinate_tk8.get()), 2)) + " F2000"
            # print(coordinate_D)
            self.robot.sendMsg(self.coordinate_D)
        else:
            self.coordinate_XYZRXYZ = "M20 G90 G00 X" + str(self.coordinate_X) + " Y" + str(
                self.coordinate_Y) + " Z" + str(self.coordinate_Z) + " A" + str(self.coordinate_RX) + " B" + str(
                self.coordinate_RY) + " C" + str(self.coordinate_RZ)
            # print(self.coordinate_XYZRXYZ)
            self.robot.sendMsg(self.coordinate_XYZRXYZ)

    def __coordinate_cut_def(self, event):
        i = event.widget.grid_info()["row"]
        self.value = round(float(self.coordinate_tk[i].get()), 2)
        self.coordinate_tk[i].delete(0, tk.END)
        self.coordinate_tk[i].insert(0, self.value - round(float(self.coordinate_tk8.get()), 2))
        # 获取X/Y/X/RX/RY/RZ的值并加到一起
        self.coordinate_X = round(float(self.coordinate_tk[0].get()), 2)
        self.coordinate_Y = round(float(self.coordinate_tk[1].get()), 2)
        self.coordinate_Z = round(float(self.coordinate_tk[2].get()), 2)
        self.coordinate_RX = round(float(self.coordinate_tk[3].get()), 2)
        self.coordinate_RY = round(float(self.coordinate_tk[4].get()), 2)
        self.coordinate_RZ = round(float(self.coordinate_tk[5].get()), 2)
        self.coordinate_D = round(float(self.coordinate_tk[6].get()), 2)
        if i == 6:
            self.coordinate_D = "G91 G01 D-" + str(round(float(self.coordinate_tk8.get()), 2)) + " F2000"
            # print(coordinate_D)
            self.robot.sendMsg(self.coordinate_D)
        else:
            self.coordinate_XYZRXYZ = "M20 G90 G00 X" + str(self.coordinate_X) + " Y" + str(
                self.coordinate_Y) + " Z" + str(self.coordinate_Z) + " A" + str(self.coordinate_RX) + " B" + str(
                self.coordinate_RY) + " C" + str(self.coordinate_RZ)
            # print(coordinate_XYZRXYZ)
            self.robot.sendMsg(self.coordinate_XYZRXYZ)

    def __coordinate_add_def8(self, event):
        self.value = round(float(self.coordinate_tk8.get()), 2)
        self.coordinate_tk8.delete(0, tk.END)
        self.coordinate_tk8.insert(0, self.value + 1)

    def __coordinate_cut_def8(self, event):
        self.value = round(float(self.coordinate_tk8.get()), 2)
        self.coordinate_tk8.delete(0, tk.END)
        self.coordinate_tk8.insert(0, self.value - 1)

    def __descartes_copy_button_def(self, event):
        self.coordinate_X = round(float(self.coordinate_tk[0].get()), 2)
        self.coordinate_Y = round(float(self.coordinate_tk[1].get()), 2)
        self.coordinate_Z = round(float(self.coordinate_tk[2].get()), 2)
        self.coordinate_RX = round(float(self.coordinate_tk[3].get()), 2)
        self.coordinate_RY = round(float(self.coordinate_tk[4].get()), 2)
        self.coordinate_RZ = round(float(self.coordinate_tk[5].get()), 2)
        self.coordinate_XYZRXYZ = "M20 G90 G00 X" + str(self.coordinate_X) + " Y" + str(self.coordinate_Y) + " Z" + str(
            self.coordinate_Z) + " A" + str(self.coordinate_RX) + " B" + str(self.coordinate_RY) + " C" + str(
            self.coordinate_RZ) + "\r\n"
        self.txt_copy.insert(self.line, self.coordinate_XYZRXYZ)
        self.line = self.line + 1

    def __getpump_copy_button_def(self, event):
        try:
            self.getpump_copy = "G3 S" + str(self.robot.getpump()) + "\r\n"
        except:
            self.getpump_copy = None
        self.txt_copy.insert(self.line, self.getpump_copy)
        self.line = self.line + 1

    def __axis7_copy_button_def(self, event):

        try:
            self.axis7_copy = "G90 G01 D" + str(self.coordinate_tk[6].get()) + " F1500\r\n"
        except:
            self.axis7_copy = None
        self.txt_copy.insert(self.line, self.axis7_copy)
        self.line = self.line + 1

    def __angle_copy_button_def(self, event):
        for i in range(6):
            self.coordinate_tk[i]['state'] = 'normal'

    def __txt_preserve_def(self, event):
        with open(str(self.txt_save.get()), 'w') as f:
            f.write(self.txt_copy.get("1.0", tk.END))

    def Mirobot_GUI(self):
        self.root = tk.Tk()
        self.root.bind("<F1>", self.__descartes_copy_button_def)
        self.root.bind("<F2>", self.__getpump_copy_button_def)
        self.root.bind("<F3>", self.__axis7_copy_button_def)
        self.root.resizable(False, False)
        self.root.wm_attributes('-topmost', 1)
        ####################################################################
        self.root.title("Mirobot_Robot_Serial1.1")
        self.frame1 = tk.Frame(self.root, width=350, height=100)
        self.frame1.pack(side="top", fill="both", expand="yes")

        self.frame2 = tk.Frame(self.root, width=350, height=300)
        self.frame2.pack(side="top", fill="both", expand="yes")

        self.frame3 = tk.Frame(self.root, width=350, height=100)
        self.frame3.pack(side="top", fill="both", expand="yes")

        self.frame4 = tk.Frame(self.root, width=350, height=100)
        self.frame4.pack(side="top", fill="both", expand="yes")

        self.frame5 = tk.Frame(self.root, width=350, height=100)
        self.frame5.pack(side="top", fill="both", expand="yes")
        ###########################################################################frame1
        self.serial_tk_lable = ttk.Label(self.frame1, text="Serial:")
        self.serial_tk_lable.pack(side="left", padx=2, pady=2)

        self.serial_tk_entry = ttk.Combobox(self.frame1, width=7)
        self.serial_tk_entry.pack(side="left", padx=2, pady=2)
        self.serial_tk_entry.bind("<Button-1>", self.__serial_numbers_def)

        self.rs485_tk_lable = ttk.Label(self.frame1, text="  RS485\nAddress:", font=('Arial', 9))
        self.rs485_tk_lable.pack(side="left", padx=2, pady=2)

        self.rs485_tk_entry = ttk.Entry(self.frame1, width=8)
        self.rs485_tk_entry.pack(side="left", padx=2, pady=2)

        self.rs485_tk_entry.insert(0, -1)

        self.rs485_tk_bote_txt = ttk.Label(self.frame1, text="Baud rate:")
        self.rs485_tk_bote_txt.pack(side="left", padx=2, pady=2)

        self.serial_tk_bote_com = ttk.Combobox(self.frame1, width=7, values=["9600", "38400", "115200"])
        self.serial_tk_bote_com.pack(side="left", padx=2, pady=2)

        self.serial_tk_bote_com.insert(0, "115200")

        self.serial_tk_button2 = ttk.Button(self.frame1, text="Connect", width=8)
        self.serial_tk_button2.pack(side="left", padx=2, pady=2)

        self.serial_tk_button2.bind("<Button-1>", self.__serial_connect_def)

        #####################################################################frame2
        self.frame2_1 = tk.Frame(self.frame2, width=100, height=200)
        self.frame2_1.pack(side="left", fill="both", expand="yes")

        self.frame2_2 = tk.Frame(self.frame2, width=100, height=200)
        self.frame2_2.pack(side="left", fill="both", expand="yes")

        self.frame2_3 = tk.Frame(self.frame2, width=100, height=200)
        self.frame2_3.pack(side="left", fill="both", expand="yes")

        for i in range(7):
            self.label_lab[i] = ttk.Label(self.frame2_1, text=self.Descartes_name[i] + ":", width=5, anchor="center")
            self.label_lab[i].grid(row=i, column=0, sticky="ew")
            self.coordinate_tk[i] = ttk.Entry(self.frame2_1, width=10)
            self.coordinate_tk[i].grid(row=i, column=1, sticky="ew")
            self.coordinate_tk[i].insert(0, 0)
            self.add_tk_button[i] = ttk.Button(self.frame2_1, text="+", width=4)
            self.add_tk_button[i].grid(row=i, column=2, sticky="ew")
            self.add_tk_button[i].bind("<Button-1>", self.__coordinate_add_def)
            self.cut_tk_button[i] = ttk.Button(self.frame2_1, text="-", width=4)
            self.cut_tk_button[i].grid(row=i, column=3, sticky="ew")
            self.cut_tk_button[i].bind("<Button-1>", self.__coordinate_cut_def)

        self.label_lab8 = ttk.Label(self.frame2_1, text="Step:", width=5, anchor="center")
        self.label_lab8.grid(row=7, column=0, sticky="ew")
        self.coordinate_tk8 = ttk.Entry(self.frame2_1, width=10)
        self.coordinate_tk8.grid(row=7, column=1, sticky="ew")
        self.coordinate_tk8.insert(0, 5)
        self.add_tk_button8 = ttk.Button(self.frame2_1, text="+", width=4)
        self.add_tk_button8.grid(row=7, column=2, sticky="ew")
        self.add_tk_button8.bind("<Button-1>", self.__coordinate_add_def8)
        self.cut_tk_button8 = ttk.Button(self.frame2_1, text="-", width=4)
        self.cut_tk_button8.grid(row=7, column=3, sticky="ew")
        self.cut_tk_button8.bind("<Button-1>", self.__coordinate_cut_def8)

        self.senmsg_tk_txt = ttk.Label(self.frame2_1, text="G code:", width=8, anchor="center")
        self.senmsg_tk_txt.grid(row=8, column=0, sticky="ew")
        self.senmsg_tk_entry = ttk.Entry(self.frame2_1, width=15)
        self.senmsg_tk_entry.grid(row=8, column=1, columnspan=2, sticky="w")
        self.senmsg_tk_entry.insert(0, "o100")
        self.senmsg_tk_button = ttk.Button(self.frame2_1, text="Send", width=4)
        self.senmsg_tk_button.grid(row=8, column=3, sticky="w")
        self.senmsg_tk_button.bind("<Button-1>", self.__wlkatapython_sendmsg)

        self.descartes_copy_button = ttk.Button(self.frame2_2, text="Coordinate\n  Copy(F1)", width=12)
        self.descartes_copy_button.grid(row=0, column=0)
        self.descartes_copy_button.bind("<Button-1>", self.__descartes_copy_button_def)

        self.getpump_copy_button = ttk.Button(self.frame2_2, text="Terminal\nCopy(F2)", width=12)
        self.getpump_copy_button.grid(row=1, column=0)
        self.getpump_copy_button.bind("<Button-1>", self.__getpump_copy_button_def)

        self.axis7_copy_button = ttk.Button(self.frame2_2, text="  7-axis\nCopy(F3)", width=12)
        self.axis7_copy_button.grid(row=2, column=0)
        self.axis7_copy_button.bind("<Button-1>", self.__axis7_copy_button_def)

        self.restart_button = ttk.Button(self.frame2_3, text="Restart", width=10)
        self.restart_button.grid(row=0, column=0)
        self.restart_button.bind("<Button-1>", self.__restart_button_def)
        self.homing_button = ttk.Button(self.frame2_3, text="Homing", width=10)
        self.homing_button.grid(row=1, column=0)
        self.homing_button.bind("<Button-1>", self.__homing_def)

        self.zero_button = ttk.Button(self.frame2_3, text="Zero", width=10)
        self.zero_button.grid(row=2, column=0)
        self.zero_button.bind("<Button-1>", self.__zero_def)
        ########################################Frame3
        self.descartes_lable = ttk.Label(self.frame3, text="Servo:", width=6)
        self.descartes_lable.pack(side="left", padx=5, pady=5)

        self.descartes_OFF = ttk.Button(self.frame3, text="Open", width=5)
        self.descartes_OFF.pack(side="left", padx=1, pady=1)
        self.descartes_OFF.bind("<Button-1>", self.__descartes_ON_def)
        self.descartes_ON = ttk.Button(self.frame3, text="Close", width=5)
        self.descartes_ON.pack(side="left", padx=1, pady=1)
        self.descartes_ON.bind("<Button-1>", self.__descartes_OFF_def)
        self.descartes_close = ttk.Button(self.frame3, text="Break", width=5)
        self.descartes_close.pack(side="left", padx=1, pady=1)
        self.descartes_close.bind("<Button-1>", self.__descartes_close_def)

        self.gripper_close = ttk.Button(self.frame3, text="Break", width=5)
        self.gripper_close.pack(side="right", padx=1, pady=1)
        self.gripper_close.bind("<Button-1>", self.__gripper_close_def)
        self.gripper_ON = ttk.Button(self.frame3, text="Inhale", width=5)
        self.gripper_ON.pack(side="right", padx=1, pady=1)
        self.gripper_ON.bind("<Button-1>", self.__gripper_ON_def)
        self.gripper_OFF = ttk.Button(self.frame3, text="Blow", width=5)
        self.gripper_OFF.pack(side="right", padx=1, pady=1)
        self.gripper_OFF.bind("<Button-1>", self.__gripper_OFF_def)
        self.gripper_lable = ttk.Label(self.frame3, text="Air pump:")
        self.gripper_lable.pack(side="right", padx=5, pady=5)

        #############################fram4
        self.txt_copy = tk.Text(self.frame4, height=10, width=62)
        self.txt_copy.pack(side="left")

        self.scrollbar = tk.Scrollbar(self.frame4, orient="vertical", command=self.txt_copy.yview)
        self.scrollbar.pack(side="left", fill="y")

        self.txt_copy.configure(yscrollcommand=self.scrollbar.set)

        self.txt_copy.pack(side="left")

        ########################frame5
        self.txt_save = tk.Entry(self.frame5, width=50)

        if os.name == 'nt':  # Windows
            self.default_path = os.path.expanduser('~\Documents')
        else:  # Linux && macOS
            self.default_path = "/opt"
        self.txt_save.insert(0, os.path.join(self.default_path, 'main.txt'))
        self.txt_save.pack(side="left", padx=5, pady=5)
        self.txt_preserve = ttk.Button(self.frame5, text="Save", width=5)
        self.txt_preserve.pack(side="left", padx=5, pady=5)
        self.txt_preserve.bind("<Button-1>", self.__txt_preserve_def)

        self.root.mainloop()

if __name__ == "__main__":
    gui = Mirobot_Serial_GUI()
    gui.Mirobot_GUI()

