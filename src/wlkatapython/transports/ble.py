"""Bluetooth LE transport via bleak.

Implements the same method names ``WLKATA_UART`` uses on ``pSerial``.

Bleak requires a single long-lived asyncio event loop for a connected
client (especially on CoreBluetooth). This transport keeps that loop on a
dedicated background thread and runs all BLE operations on it.
"""

import asyncio
import threading
import time
import warnings
from typing import Any, Coroutine, List, Optional, Tuple, TypeVar

from .base import Transport

try:
    from bleak import BleakClient
except ImportError:  # pragma: no cover - optional dependency
    BleakClient = None

# Default GATT UUIDs for the WLKATA Extender Box BLE serial bridge
# (service 0000ffe0-..., write 0000ffe2-..., notify 0000ffe3-...).
DEFAULT_WRITE_UUID = "0000ffe2-0000-1000-8000-00805f9b34fb"
DEFAULT_NOTIFY_UUID = "0000ffe3-0000-1000-8000-00805f9b34fb"

_T = TypeVar("_T")


def resolve_ble_address_by_name(
    name: str,
    scan_timeout: float = 10.0,
) -> str:
    """Scan for a BLE device by advertised name and return its address.

    Args:
        name: Exact Bluetooth advertised name (e.g. ``"ExBox-E510"``).
        scan_timeout: How long to scan, in seconds.

    Returns:
        The unique matching device address.

    Raises:
        ImportError: If ``bleak`` is not installed.
        RuntimeError: If no device matches, or more than one device shares
            the same name (connection must not proceed in that case).
    """
    try:
        from bleak import BleakScanner  # noqa: F401
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "BLE name lookup requires the 'bleak' package. "
            "Install it with: pip install bleak"
        ) from exc

    matches = asyncio.run(_scan_ble_devices_by_name(name, scan_timeout))

    if not matches:
        raise RuntimeError(
            f"No BLE device found with name {name!r}. "
            "Make sure it is powered on, in range, and advertising."
        )

    if len(matches) > 1:
        addresses = ", ".join(address for _, address in matches)
        message = (
            f"Multiple BLE devices found with name {name!r} "
            f"({len(matches)} matches: {addresses}). "
            "Connection aborted; rename or power off extras so the name is unique."
        )
        warnings.warn(message, UserWarning, stacklevel=2)
        raise RuntimeError(message)

    return matches[0][1]


async def _scan_ble_devices_by_name(
    name: str,
    scan_timeout: float = 2.0,
) -> List[Tuple[str, str]]:
    """Return ``(name, address)`` pairs whose advertised name equals ``name``."""
    from bleak import BleakScanner

    devices = await BleakScanner.discover(timeout=scan_timeout)
    return [(d.name, d.address) for d in devices if d.name == name]


class BleTransport(Transport):
    """BLE transport for Bluetooth-connected robots using bleak.

    Requires the optional ``bleak`` package.

    A background asyncio loop is started on ``connect()`` and kept alive for
    the whole session so writes and notifications stay on the same loop as
    the Bleak client (required by CoreBluetooth / bleak).

    Args:
        address: BLE device address (e.g. ``"AA:BB:CC:DD:EE:FF"``).
        write_uuid: GATT characteristic UUID for writing (robot RX).
            Defaults to the WLKATA Extender Box write characteristic.
        notify_uuid: GATT characteristic UUID for notifications (robot TX).
            Defaults to the WLKATA Extender Box notify characteristic.
        timeout: Read timeout in seconds. Defaults to 5. ``None`` waits forever.
    """

    def __init__(
        self,
        address: str,
        write_uuid: str = DEFAULT_WRITE_UUID,
        notify_uuid: str = DEFAULT_NOTIFY_UUID,
        timeout: Optional[float] = 5,
    ):
        if BleakClient is None:
            raise ImportError(
                "BleTransport requires the 'bleak' package. "
                "Install it with: pip install bleak"
            )
        self.address = address
        self.write_uuid = write_uuid
        self.notify_uuid = notify_uuid
        self._timeout = timeout
        self._client: Optional[BleakClient] = None
        self._buffer = b""
        self._buffer_lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None

    def _start_background_loop(self) -> None:
        if self._loop is not None and self._loop.is_running():
            return

        ready = threading.Event()
        errors = []  # type: List[BaseException]

        def runner() -> None:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._loop = loop
            except BaseException as exc:  # pragma: no cover - startup failure
                errors.append(exc)
                ready.set()
                return
            ready.set()
            loop.run_forever()
            try:
                loop.close()
            finally:
                if self._loop is loop:
                    self._loop = None

        self._loop_thread = threading.Thread(
            target=runner,
            name=f"BleTransport-{self.address}",
            daemon=True,
        )
        self._loop_thread.start()
        if not ready.wait(timeout=5.0):
            raise RuntimeError("Timed out starting BLE event loop thread")
        if errors:
            raise RuntimeError("Failed to start BLE event loop") from errors[0]

    def _stop_background_loop(self) -> None:
        loop = self._loop
        thread = self._loop_thread
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(loop.stop)
        if thread is not None and thread.is_alive():
            thread.join(timeout=5.0)
        self._loop = None
        self._loop_thread = None

    def _run(self, coro: Coroutine[Any, Any, _T], timeout: Optional[float] = None) -> _T:
        """Run a coroutine on the transport's background event loop."""
        self._start_background_loop()
        loop = self._loop
        if loop is None or not loop.is_running():
            raise RuntimeError("BLE event loop is not running")
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        try:
            return future.result(timeout=timeout)
        except Exception:
            future.cancel()
            raise

    def connect(self):
        if self.is_connected:
            return
        self._run(self._connect(), timeout=30.0)

    async def _connect(self):
        self._client = BleakClient(self.address)
        await self._client.connect()
        await self._client.start_notify(self.notify_uuid, self._on_notify)

    def disconnect(self):
        if self._client is None and self._loop is None:
            return
        try:
            if self._client is not None and self._loop is not None and self._loop.is_running():
                self._run(self._disconnect(), timeout=10.0)
        finally:
            self._client = None
            with self._buffer_lock:
                self._buffer = b""
            self._stop_background_loop()

    async def _disconnect(self):
        if self._client is None:
            return
        try:
            await self._client.stop_notify(self.notify_uuid)
        except Exception:
            pass
        try:
            await self._client.disconnect()
        except Exception:
            pass
        self._client = None

    @property
    def is_connected(self) -> bool:
        if self._client is None:
            return False
        return bool(getattr(self._client, "is_connected", True))

    def write(self, data: bytes):
        if not self.is_connected:
            raise RuntimeError("BleTransport is not connected; call connect() first")
        self._run(self._write(data), timeout=10.0)

    async def _write(self, data: bytes):
        # Extender Box write char is Write-with-response (see GATT properties).
        await self._client.write_gatt_char(self.write_uuid, data, response=True)

    def readline(self) -> bytes:
        """Wait for a full line from the notify buffer, honoring ``timeout``."""
        if self._timeout is None:
            while True:
                with self._buffer_lock:
                    if b"\n" in self._buffer:
                        break
                time.sleep(0.01)
        else:
            deadline = time.monotonic() + self._timeout
            while time.monotonic() < deadline:
                with self._buffer_lock:
                    if b"\n" in self._buffer:
                        break
                time.sleep(0.01)

        with self._buffer_lock:
            if b"\n" in self._buffer:
                line, _, self._buffer = self._buffer.partition(b"\n")
                return line + b"\n"
            line = self._buffer
            self._buffer = b""
            return line

    def flushInput(self):
        """Discard any bytes received via notifications but not yet read."""
        with self._buffer_lock:
            self._buffer = b""

    def flushOutput(self):
        """No-op: BLE writes are issued immediately to the stack."""
        return

    @property
    def in_waiting(self) -> int:
        """Bytes already received via notifications into the local buffer."""
        with self._buffer_lock:
            return len(self._buffer)

    @property
    def timeout(self) -> Optional[float]:
        return self._timeout

    @timeout.setter
    def timeout(self, value: Optional[float]):
        self._timeout = value

    def _on_notify(self, sender, data: bytearray):
        # Called from the BLE event-loop thread; keep this non-blocking.
        with self._buffer_lock:
            self._buffer += bytes(data)


if __name__ == "__main__":
    # --- config ---
    DEVICE_NAME = "ExBox-E510"
    DEVICE_PIN = "1234"  # pairing PIN (handled at OS level — pair the device first)
    MESSAGE = "?\r\n"  # status query
    # --------------

    print(f"Scanning for '{DEVICE_NAME}'...")
    try:
        address = resolve_ble_address_by_name(DEVICE_NAME, scan_timeout=10)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    print(f"Found: {DEVICE_NAME}  [{address}]")
    print(
        f"Note: if the device requires PIN '{DEVICE_PIN}', "
        "pair it via OS Bluetooth settings first."
    )

    transport = BleTransport(address, timeout=5)
    transport.connect()
    print("Connected.")

    print(f"Sending: {MESSAGE!r}")
    transport.write(MESSAGE.encode())

    response = transport.readline().decode("utf-8", errors="replace").strip()
    print(f"Received: {response!r}")

    transport.disconnect()
    print("Disconnected.")
