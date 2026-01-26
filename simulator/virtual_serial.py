"""
Virtual serial port implementation for testing.

This module provides a virtual serial port that can be used to test
serial communication without requiring actual hardware.

On Linux, this uses PTY (pseudo-terminal) pairs.
On other platforms, it uses a socket-based approach or file-based simulation.
"""

import os
import sys
import io
import threading
import queue
import time
from typing import Optional, Callable


class VirtualSerialPort:
    """
    A virtual serial port that simulates a serial connection.
    
    On Linux, this creates a PTY pair where:
    - The master side is used internally by the simulator
    - The slave side (a path like /dev/pts/N) can be used by the client
    
    On other platforms, it uses an in-memory buffer approach.
    """
    
    def __init__(self, baudrate: int = 115200, timeout: float = 1.0):
        """
        Initialize the virtual serial port.
        
        Args:
            baudrate: Simulated baud rate (for compatibility)
            timeout: Read timeout in seconds
        """
        self.baudrate = baudrate
        self.timeout = timeout
        self._is_open = False
        self._master_fd: Optional[int] = None
        self._slave_fd: Optional[int] = None
        self._slave_path: Optional[str] = None
        self._lock = threading.Lock()
        
        # For non-PTY platforms
        self._read_buffer = queue.Queue()
        self._write_buffer = queue.Queue()
        
        # Platform detection
        self._use_pty = sys.platform.startswith('linux') or sys.platform == 'darwin'
        
    def open(self) -> str:
        """
        Open the virtual serial port.
        
        Returns:
            The path to the slave side of the virtual serial port.
            On Linux: /dev/pts/N
            On other platforms: Returns a special identifier
        """
        if self._is_open:
            return self._slave_path or "virtual://serial"
            
        if self._use_pty:
            return self._open_pty()
        else:
            return self._open_virtual()
    
    def _open_pty(self) -> str:
        """Open a PTY pair on Linux/macOS."""
        import pty
        import tty
        
        # Create PTY pair
        self._master_fd, self._slave_fd = pty.openpty()
        
        # Get the slave path
        self._slave_path = os.ttyname(self._slave_fd)
        
        # Configure the PTY for raw mode
        tty.setraw(self._master_fd)
        
        # Make master non-blocking
        import fcntl
        flags = fcntl.fcntl(self._master_fd, fcntl.F_GETFL)
        fcntl.fcntl(self._master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        
        self._is_open = True
        return self._slave_path
    
    def _open_virtual(self) -> str:
        """Open a virtual port for non-PTY platforms."""
        self._is_open = True
        self._slave_path = "virtual://serial"
        return self._slave_path
    
    def close(self):
        """Close the virtual serial port."""
        if not self._is_open:
            return
            
        if self._use_pty:
            if self._master_fd is not None:
                try:
                    os.close(self._master_fd)
                except OSError:
                    pass
                self._master_fd = None
            if self._slave_fd is not None:
                try:
                    os.close(self._slave_fd)
                except OSError:
                    pass
                self._slave_fd = None
        
        self._is_open = False
    
    def write_to_slave(self, data: bytes):
        """
        Write data to the slave side (simulates hardware sending data to client).
        
        Args:
            data: Bytes to write
        """
        if not self._is_open:
            raise IOError("Port is not open")
            
        with self._lock:
            if self._use_pty and self._master_fd is not None:
                os.write(self._master_fd, data)
            else:
                for byte in data:
                    self._read_buffer.put(bytes([byte]))
    
    def read_from_slave(self, size: int = 1024) -> bytes:
        """
        Read data from the slave side (reads what client sent to hardware).
        
        Args:
            size: Maximum number of bytes to read
            
        Returns:
            Bytes read from the slave side
        """
        if not self._is_open:
            raise IOError("Port is not open")
            
        if self._use_pty and self._master_fd is not None:
            try:
                return os.read(self._master_fd, size)
            except (BlockingIOError, OSError):
                return b""
        else:
            data = b""
            try:
                while len(data) < size:
                    data += self._write_buffer.get_nowait()
            except queue.Empty:
                pass
            return data
    
    def readline_from_slave(self, timeout: Optional[float] = None) -> bytes:
        """
        Read a line from the slave side.
        
        Args:
            timeout: Read timeout in seconds (uses default if None)
            
        Returns:
            Line read from the slave side (including newline)
        """
        if timeout is None:
            timeout = self.timeout
            
        start_time = time.time()
        line = b""
        
        while True:
            if time.time() - start_time > timeout:
                break
                
            chunk = self.read_from_slave(1)
            if chunk:
                line += chunk
                if chunk == b"\n":
                    break
            else:
                time.sleep(0.01)
        
        return line
    
    @property
    def port_path(self) -> Optional[str]:
        """Get the path to the slave serial port."""
        return self._slave_path
    
    @property
    def is_open(self) -> bool:
        """Check if the port is open."""
        return self._is_open
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class MockSerial:
    """
    A mock serial.Serial-like object that can be used as a drop-in replacement.
    
    This connects to the slave side of a VirtualSerialPort through the 
    underlying file descriptors or an internal buffer.
    """
    
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0,
                 virtual_port: Optional[VirtualSerialPort] = None):
        """
        Initialize the mock serial port.
        
        Args:
            port: Serial port path (for compatibility, may be ignored)
            baudrate: Baud rate (for compatibility)
            timeout: Read timeout in seconds
            virtual_port: The VirtualSerialPort to connect to (if using internal buffer mode)
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._virtual_port = virtual_port
        self._is_open = False
        self._fd = None
        self._file = None
        self._read_buffer = b""
        
        # Open the port
        self._open()
    
    def _open(self):
        """Open the serial port."""
        if self._is_open:
            return
            
        if self._virtual_port and not self._virtual_port._use_pty:
            # Use internal buffer mode
            self._is_open = True
            return
            
        # Try to open the port path
        try:
            self._fd = os.open(self.port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
            self._is_open = True
        except OSError as e:
            raise IOError(f"Could not open port {self.port}: {e}")
    
    def close(self):
        """Close the serial port."""
        if not self._is_open:
            return
            
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
        
        self._is_open = False
    
    def write(self, data: bytes) -> int:
        """
        Write data to the serial port.
        
        Args:
            data: Bytes to write
            
        Returns:
            Number of bytes written
        """
        if not self._is_open:
            raise IOError("Port is not open")
            
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        if self._virtual_port and not self._virtual_port._use_pty:
            for byte in data:
                self._virtual_port._write_buffer.put(bytes([byte]))
            return len(data)
            
        if self._fd is not None:
            return os.write(self._fd, data)
        
        return 0
    
    def read(self, size: int = 1) -> bytes:
        """
        Read data from the serial port.
        
        Args:
            size: Number of bytes to read
            
        Returns:
            Bytes read
        """
        if not self._is_open:
            raise IOError("Port is not open")
            
        if self._virtual_port and not self._virtual_port._use_pty:
            data = b""
            start_time = time.time()
            while len(data) < size:
                if time.time() - start_time > self.timeout:
                    break
                try:
                    data += self._virtual_port._read_buffer.get(timeout=0.01)
                except queue.Empty:
                    pass
            return data
            
        if self._fd is not None:
            start_time = time.time()
            data = b""
            while len(data) < size:
                if time.time() - start_time > self.timeout:
                    break
                try:
                    chunk = os.read(self._fd, size - len(data))
                    if chunk:
                        data += chunk
                except (BlockingIOError, OSError):
                    time.sleep(0.01)
            return data
        
        return b""
    
    def readline(self) -> bytes:
        """
        Read a line from the serial port.
        
        Returns:
            Line read (including newline character)
        """
        line = b""
        start_time = time.time()
        
        while True:
            if time.time() - start_time > self.timeout:
                break
                
            char = self.read(1)
            if char:
                line += char
                if char == b"\n":
                    break
            else:
                time.sleep(0.01)
        
        return line
    
    @property
    def in_waiting(self) -> int:
        """Get the number of bytes in the input buffer."""
        if self._virtual_port and not self._virtual_port._use_pty:
            return self._virtual_port._read_buffer.qsize()
            
        if self._fd is not None:
            import fcntl
            import termios
            buf = bytearray(4)
            try:
                fcntl.ioctl(self._fd, termios.FIONREAD, buf)
                return int.from_bytes(buf, byteorder='little')
            except (OSError, IOError):
                return 0
        
        return 0
    
    def flushInput(self):
        """Flush the input buffer."""
        if self._virtual_port and not self._virtual_port._use_pty:
            while not self._virtual_port._read_buffer.empty():
                try:
                    self._virtual_port._read_buffer.get_nowait()
                except queue.Empty:
                    break
            return
            
        if self._fd is not None:
            import termios
            try:
                termios.tcflush(self._fd, termios.TCIFLUSH)
            except (OSError, termios.error):
                pass
    
    def flushOutput(self):
        """Flush the output buffer."""
        if self._virtual_port and not self._virtual_port._use_pty:
            while not self._virtual_port._write_buffer.empty():
                try:
                    self._virtual_port._write_buffer.get_nowait()
                except queue.Empty:
                    break
            return
            
        if self._fd is not None:
            import termios
            try:
                termios.tcflush(self._fd, termios.TCOFLUSH)
            except (OSError, termios.error):
                pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
