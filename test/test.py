import wlkatapython
import serial



# gui = wlkatapython.Mirobot_Serial_GUI()
# gui.Mirobot_GUI()

mirobot = wlkatapython.Mirobot_UART()
mirobot.init(serial.Serial('COM13', 115200), 1)
mirobot.homing()

# e4 = wlkatapython.E4_UART()
# e4.init(serial.Serial('COM13', 115200), -1)
# e4.homing()

# mt4 = wlkatapython.MT4_UART()
# mt4.init(serial.Serial('COM13', 115200), -1)
# mt4.homing()

# ms4220 = wlkatapython.MS4220_UART()
# ms4220.init(serial.Serial('COM13', 38400), 10)
# ms4220.speed(100)

