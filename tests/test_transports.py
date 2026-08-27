"""Tests for multi-protocol transports and robot connection normalization."""

import socket
import threading
import time
from unittest import mock

import pytest
import serial

from wlkatapython import Mirobot_UART, SerialAdapter, Transport, UartTransport
from wlkatapython.simulator import MirobotSimulator
from wlkatapython.transports import WifiTransport
from wlkatapython.transports import ble as ble_mod


pytestmark = pytest.mark.simulator


class TestSerialAdapter:
    """SerialAdapter wraps user-owned ports without taking ownership."""

    def test_wraps_and_delegates(self, mirobot_simulator):
        ser = serial.Serial(mirobot_simulator.port_path, 115200, timeout=2.0)
        try:
            adapter = SerialAdapter(ser)
            assert isinstance(adapter, Transport)
            assert adapter.is_connected
            assert adapter.raw is ser
            adapter.write(b"?\r\n")
            time.sleep(0.15)
            # Response may or may not be immediate; surface must work
            _ = adapter.in_waiting
            adapter.flushInput()
            adapter.flushOutput()
            adapter.timeout = 1.5
            assert adapter.timeout == 1.5
        finally:
            ser.close()

    def test_disconnect_does_not_close_user_port(self, mirobot_simulator):
        ser = serial.Serial(mirobot_simulator.port_path, 115200, timeout=2.0)
        try:
            adapter = SerialAdapter(ser)
            adapter.disconnect()
            assert ser.is_open
            assert adapter.is_connected
        finally:
            ser.close()

    def test_rejects_invalid_object(self):
        with pytest.raises(TypeError, match="serial.Serial"):
            SerialAdapter(object())  # type: ignore[arg-type]

    def test_robot_init_rejects_invalid_connection(self):
        robot = Mirobot_UART()
        with pytest.raises(TypeError, match="serial.Serial or a Transport"):
            robot.init(object(), -1)  # type: ignore[arg-type]


class TestUartTransportSurface:
    def test_is_connected_lifecycle(self, mirobot_simulator):
        t = UartTransport(mirobot_simulator.port_path, baudrate=115200, timeout=2.0)
        assert not t.is_connected
        t.connect()
        assert t.is_connected
        t.disconnect()
        assert not t.is_connected

    def test_write_without_connect_raises(self):
        t = UartTransport("/dev/null", timeout=0.1)
        with pytest.raises(RuntimeError, match="not connected"):
            t.write(b"x")


class TestWifiTransportSurface:
    def test_is_connected_default(self):
        t = WifiTransport("127.0.0.1", 9, timeout=0.1)
        assert not t.is_connected

    def test_write_without_connect_raises(self):
        t = WifiTransport("127.0.0.1", 9, timeout=0.1)
        with pytest.raises(RuntimeError, match="not connected"):
            t.write(b"x")

    def test_tcp_echo_roundtrip(self):
        """Local TCP server exercises connect/write/readline/flush/timeout."""
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        host, port = srv.getsockname()
        received = []

        def serve():
            conn, _ = srv.accept()
            data = conn.recv(1024)
            received.append(data)
            conn.sendall(b"ok\n")
            # leave some trailing data for flushInput drain
            try:
                conn.sendall(b"extra")
            except OSError:
                pass
            time.sleep(0.05)
            conn.close()

        th = threading.Thread(target=serve, daemon=True)
        th.start()

        t = WifiTransport(host, port, protocol="tcp", timeout=1.0)
        assert not t.is_connected
        t.connect()
        assert t.is_connected
        t.connect()  # idempotent
        t.write(b"?\r\n")
        line = t.readline()
        assert line == b"ok\n"
        t.timeout = 0.2
        assert t.timeout == 0.2
        t.flushOutput()
        t.flushInput()
        assert t.in_waiting == 0
        # timeout path: no more lines
        empty = t.readline()
        assert empty == b"" or isinstance(empty, (bytes, bytearray))
        t.disconnect()
        assert not t.is_connected
        t.disconnect()
        th.join(timeout=2)
        srv.close()
        assert received and b"?" in received[0]

    def test_udp_connect_write(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        srv.bind(("127.0.0.1", 0))
        host, port = srv.getsockname()
        t = WifiTransport(host, port, protocol="udp", timeout=0.3)
        t.connect()
        t.write(b"ping\n")
        # may or may not receive depending on peer; surface should not crash
        _ = t.readline()
        t.disconnect()
        srv.close()


class TestBleTransportSurface:
    def test_import_error_without_bleak(self):
        with mock.patch.object(ble_mod, "BleakClient", None):
            with pytest.raises(ImportError, match="bleak"):
                ble_mod.BleTransport("AA:BB")

    def test_resolve_name_import_error(self):
        import builtins

        real_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "bleak" or (isinstance(name, str) and name.startswith("bleak.")):
                raise ImportError("no bleak")
            return real_import(name, globals, locals, fromlist, level)

        with mock.patch("builtins.__import__", side_effect=fake_import):
            with pytest.raises(ImportError, match="bleak"):
                ble_mod.resolve_ble_address_by_name("dev")

    def test_resolve_name_no_match_and_multi(self):
        async def fake_scan_empty(name, timeout=2.0):
            return []

        async def fake_scan_multi(name, timeout=2.0):
            return [("dev", "AA"), ("dev", "BB")]

        with mock.patch.object(ble_mod, "_scan_ble_devices_by_name", fake_scan_empty):
            with pytest.raises(RuntimeError, match="No BLE device"):
                ble_mod.resolve_ble_address_by_name("dev", scan_timeout=0.1)

        with mock.patch.object(ble_mod, "_scan_ble_devices_by_name", fake_scan_multi):
            with pytest.warns(UserWarning, match="Multiple"):
                with pytest.raises(RuntimeError, match="Multiple BLE"):
                    ble_mod.resolve_ble_address_by_name("dev", scan_timeout=0.1)

    def test_resolve_name_unique(self):
        async def fake_scan(name, timeout=2.0):
            return [("ExBox", "11:22:33:44:55:66")]

        with mock.patch.object(ble_mod, "_scan_ble_devices_by_name", fake_scan):
            addr = ble_mod.resolve_ble_address_by_name("ExBox", scan_timeout=0.1)
        assert addr == "11:22:33:44:55:66"

    def test_ble_transport_with_mock_client(self):
        if ble_mod.BleakClient is None:
            pytest.skip("bleak not installed")

        class FakeClient:
            def __init__(self, address):
                self.address = address
                self.is_connected = False
                self.written = []
                self._notify_cb = None

            async def connect(self):
                self.is_connected = True

            async def disconnect(self):
                self.is_connected = False

            async def start_notify(self, uuid, cb):
                self._notify_cb = cb

            async def stop_notify(self, uuid):
                return

            async def write_gatt_char(self, uuid, data, response=True):
                self.written.append(bytes(data))
                if self._notify_cb:
                    self._notify_cb(None, bytearray(b"ok\n"))

        with mock.patch.object(ble_mod, "BleakClient", FakeClient):
            t = ble_mod.BleTransport("AA:BB:CC:DD:EE:FF", timeout=1.0)
            assert not t.is_connected
            t.connect()
            assert t.is_connected
            t.connect()  # idempotent
            t.write(b"?\r\n")
            line = t.readline()
            assert line == b"ok\n"
            assert t.in_waiting == 0
            t.flushInput()
            t.flushOutput()
            t.timeout = 2.0
            assert t.timeout == 2.0
            # timeout empty readline
            t._timeout = 0.05
            empty = t.readline()
            assert empty == b""
            t.disconnect()
            assert not t.is_connected
            t.disconnect()

    def test_ble_write_requires_connect(self):
        if ble_mod.BleakClient is None:
            pytest.skip("bleak not installed")

        class FakeClient:
            def __init__(self, address):
                self.is_connected = False

        with mock.patch.object(ble_mod, "BleakClient", FakeClient):
            t = ble_mod.BleTransport("AA:BB")
            with pytest.raises(RuntimeError, match="not connected"):
                t.write(b"x")


class TestRobotInitNormalization:
    """WLKATA_UART.init silently normalizes connections into pSerial."""

    def test_init_with_serial_wraps_adapter(self, mirobot_simulator):
        ser = serial.Serial(mirobot_simulator.port_path, 115200, timeout=2.0)
        try:
            robot = Mirobot_UART()
            robot.init(ser, -1)
            assert isinstance(robot.pSerial, SerialAdapter)
            assert robot.pSerial.raw is ser
            robot.homing()
            status = robot.getStatus()
            assert status != "error"
        finally:
            ser.close()

    def test_close_does_not_close_user_serial(self, mirobot_simulator):
        ser = serial.Serial(mirobot_simulator.port_path, 115200, timeout=2.0)
        try:
            robot = Mirobot_UART()
            robot.init(ser, -1)
            robot.close()
            assert ser.is_open
        finally:
            ser.close()

    def test_init_with_uart_transport_auto_connects(self, mirobot_simulator):
        transport = UartTransport(
            mirobot_simulator.port_path, baudrate=115200, timeout=2.0
        )
        assert not transport.is_connected
        robot = Mirobot_UART()
        robot.init(transport, -1)
        assert transport.is_connected
        assert robot.pSerial is transport
        robot.homing()
        status = robot.getStatus()
        assert status != "error"
        robot.close()
        assert not transport.is_connected

    def test_init_uart_helper(self, mirobot_simulator):
        robot = Mirobot_UART()
        robot.init_uart(mirobot_simulator.port_path, -1, baudrate=115200, timeout=2.0)
        assert isinstance(robot.pSerial, UartTransport)
        assert robot.pSerial.is_connected
        robot.homing()
        status = robot.getStatus()
        assert status != "error"
        robot.close()
        assert not robot.pSerial.is_connected

    def test_preconnected_transport(self, mirobot_simulator):
        transport = UartTransport(
            mirobot_simulator.port_path, baudrate=115200, timeout=2.0
        )
        transport.connect()
        robot = Mirobot_UART()
        robot.init(transport, -1)
        assert robot.pSerial is transport
        assert robot.getStatus() != "error"
        transport.disconnect()
