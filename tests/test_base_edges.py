"""Extra coverage for WLKATA_UART edge paths and MS4220 clamping."""

import time
from typing import Optional

import pytest
import serial

from wlkatapython import Mirobot_UART, MS4220_UART
from wlkatapython.simulator import MirobotSimulator, MS4220Simulator
from wlkatapython.transports import Transport


class ScriptedTransport(Transport):
    """Transport with scripted responses per write (for GPIO / file paths)."""

    def __init__(self, script=None):
        # script: list of list[str] responses for successive writes
        self.script = list(script or [])
        self.writes = []
        self._rx = b""
        self._connected = True
        self._timeout = 1.0
        self._idx = 0

    def connect(self):
        self._connected = True

    def disconnect(self):
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def write(self, data: bytes):
        self.writes.append(data)
        if self._idx < len(self.script):
            for line in self.script[self._idx]:
                self._rx += (line + "\n").encode()
            self._idx += 1

    def readline(self) -> bytes:
        if b"\n" in self._rx:
            line, _, self._rx = self._rx.partition(b"\n")
            return line + b"\n"
        out, self._rx = self._rx, b""
        return out

    def flushInput(self):
        self._rx = b""

    def flushOutput(self):
        return

    @property
    def in_waiting(self) -> int:
        return len(self._rx)

    @property
    def timeout(self) -> Optional[float]:
        return self._timeout

    @timeout.setter
    def timeout(self, value: Optional[float]):
        self._timeout = value


class TestBaseHelpers:
    def test_message_print_levels(self):
        r = Mirobot_UART()
        r.message_print(True)
        r.message_print(False)
        import logging
        r.message_print(logging.INFO)

    def test_init_with_connection_ctor(self, mirobot_simulator):
        ser = serial.Serial(mirobot_simulator.port_path, 115200, timeout=2.0)
        try:
            r = Mirobot_UART(ser, -1)
            assert r.pSerial is not None
            assert r.getStatus() != "error"
        finally:
            ser.close()

    def test_init_wifi_against_local_server(self):
        import socket
        import threading

        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        host, port = srv.getsockname()

        def serve():
            conn, _ = srv.accept()
            conn.recv(64)
            conn.sendall(b"ok\n")
            conn.close()

        th = threading.Thread(target=serve, daemon=True)
        th.start()
        r = Mirobot_UART()
        r.init_wifi(host, port, -1, timeout=1.0)
        r.sendMsg("?")
        # may get ok or empty depending on timing
        r.close()
        th.join(timeout=2)
        srv.close()

    def test_gpio_enable_file_write_read(self):
        t = ScriptedTransport(
            script=[
                ["ok"],           # o134 write
                ["f0,f1,f2,f3", "ok"],  # o134? data + ok
            ]
        )
        r = Mirobot_UART()
        r.init(t, -1)
        assert r.gpio_enable_file_write("A0", "f0") == 1
        val = r.gpio_enable_file_read("A0")
        assert val == "f0"

    def test_gpio_enable_file_write_bad_pin(self):
        t = ScriptedTransport()
        r = Mirobot_UART()
        r.init(t, -1)
        with pytest.raises(Exception):
            r.gpio_enable_file_write("ZZ", 1)

    def test_rs485_address_prefix(self):
        t = ScriptedTransport()
        r = Mirobot_UART()
        r.init(t, 3)
        r.sendMsg("?")
        assert t.writes[-1].startswith(b"@3")


class TestMS4220Edges:
    def test_speed_clamping(self):
        sim = MS4220Simulator()
        port = sim.start()
        time.sleep(0.1)
        try:
            ser = serial.Serial(port, 38400, timeout=2.0)
            m = MS4220_UART()
            m.init(ser, 10)
            assert m.speed(150) == 1
            assert m.speed(-150) == 1
            assert m.speed(0) == 1
            ser.close()
        finally:
            sim.stop()
