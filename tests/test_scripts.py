"""
Tests for the scripts module.
"""

import pytest
import time
import serial
import tempfile
from pathlib import Path

pytestmark = pytest.mark.scripts

from scripts.gcode_recorder import GCodeRecorder


class TestGCodeRecorder:
    """Tests for the G-code recorder script."""
    
    def test_recorder_initialization(self):
        """Test recorder can be initialized."""
        recorder = GCodeRecorder(model="mirobot")
        assert recorder.model == "mirobot"
        assert recorder.address == -1
        assert recorder.command_count == 0
    
    def test_recorder_starts_and_stops(self):
        """Test recorder can start and stop."""
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            log_path = f.name
        
        try:
            recorder = GCodeRecorder(model="mirobot", output_file=log_path)
            port = recorder.start()
            
            assert port is not None
            assert recorder.is_running
            assert recorder.port_path == port
            
            recorder.stop()
            
            assert not recorder.is_running
        finally:
            Path(log_path).unlink(missing_ok=True)
    
    def test_recorder_context_manager(self):
        """Test recorder as context manager."""
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            log_path = f.name
        
        try:
            with GCodeRecorder(model="mirobot", output_file=log_path) as recorder:
                assert recorder.is_running
            
            assert not recorder.is_running
        finally:
            Path(log_path).unlink(missing_ok=True)
    
    def test_recorder_logs_commands(self):
        """Test that commands are logged to file."""
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            log_path = f.name
        
        try:
            recorder = GCodeRecorder(model="mirobot", output_file=log_path)
            port = recorder.start()
            time.sleep(0.1)
            
            # Send commands
            ser = serial.Serial(port, 115200, timeout=1.0)
            commands = ["?", "o105=8", "M3 S500"]
            
            for cmd in commands:
                ser.write((cmd + "\r\n").encode())
                time.sleep(0.15)
                ser.readline()  # Read response
            
            ser.close()
            recorder.stop()
            
            # Verify commands were logged
            assert recorder.command_count == 3
            
            log_content = Path(log_path).read_text()
            assert "?" in log_content
            assert "o105=8" in log_content
            assert "M3 S500" in log_content
            assert "#1:" in log_content
            assert "#2:" in log_content
            assert "#3:" in log_content
        finally:
            Path(log_path).unlink(missing_ok=True)
    
    def test_recorder_verbose_mode(self):
        """Test recorder verbose mode doesn't crash."""
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            log_path = f.name
        
        try:
            recorder = GCodeRecorder(
                model="mirobot", 
                output_file=log_path,
                verbose=True
            )
            port = recorder.start()
            time.sleep(0.1)
            
            ser = serial.Serial(port, 115200, timeout=1.0)
            ser.write(b"?\r\n")
            time.sleep(0.15)
            ser.readline()
            
            ser.close()
            recorder.stop()
            
            assert recorder.command_count == 1
        finally:
            Path(log_path).unlink(missing_ok=True)
    
    def test_recorder_max_commands(self):
        """Test recorder stops after max commands."""
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            log_path = f.name
        
        try:
            recorder = GCodeRecorder(
                model="mirobot",
                output_file=log_path,
                max_commands=3
            )
            port = recorder.start()
            time.sleep(0.1)
            
            ser = serial.Serial(port, 115200, timeout=1.0)
            
            # Send commands one at a time and check if recorder stops
            for i in range(5):
                if not recorder.is_running:
                    break
                ser.write(b"?\r\n")
                time.sleep(0.2)
                if ser.in_waiting:
                    ser.readline()
            
            time.sleep(0.2)
            
            ser.close()
            recorder.stop()
            
            # Should have stopped at or around max_commands
            assert recorder.command_count >= 3
            assert recorder.command_count <= 4  # Allow for race condition
        finally:
            Path(log_path).unlink(missing_ok=True)
    
    def test_recorder_different_models(self):
        """Test recorder works with different robot models."""
        models = ["mirobot", "e4", "mt4", "ms4220"]
        
        for model in models:
            with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
                log_path = f.name
            
            try:
                address = 10 if model == "ms4220" else -1
                recorder = GCodeRecorder(
                    model=model,
                    address=address,
                    output_file=log_path
                )
                port = recorder.start()
                time.sleep(0.1)
                
                assert recorder.is_running
                assert port is not None
                
                recorder.stop()
            finally:
                Path(log_path).unlink(missing_ok=True)
    
    def test_recorder_responds_correctly(self):
        """Test recorder still responds to commands correctly."""
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            log_path = f.name
        
        try:
            recorder = GCodeRecorder(model="mirobot", output_file=log_path)
            port = recorder.start()
            time.sleep(0.1)
            
            ser = serial.Serial(port, 115200, timeout=1.0)
            
            # Test status query response
            ser.write(b"?\r\n")
            time.sleep(0.15)
            response = ser.readline().decode()
            assert "<" in response and ">" in response
            assert "Idle" in response
            
            # Test homing response
            ser.write(b"o105=8\r\n")
            time.sleep(0.15)
            response = ser.readline().decode()
            assert "ok" in response
            
            ser.close()
            recorder.stop()
        finally:
            Path(log_path).unlink(missing_ok=True)
    
    def test_recorder_log_format(self):
        """Test log file format is correct."""
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            log_path = f.name
        
        try:
            recorder = GCodeRecorder(model="mirobot", output_file=log_path)
            port = recorder.start()
            time.sleep(0.1)
            
            ser = serial.Serial(port, 115200, timeout=1.0)
            ser.write(b"?\r\n")
            time.sleep(0.15)
            ser.readline()
            ser.close()
            
            recorder.stop()
            
            log_content = Path(log_path).read_text()
            
            # Check header
            assert "G-Code Recording Session" in log_content
            assert "Model: mirobot" in log_content
            assert "Address: -1" in log_content
            
            # Check command format includes timestamp
            assert "[" in log_content
            assert "]" in log_content
            assert "#1:" in log_content
            
            # Check footer
            assert "Recording Session Ended" in log_content
            assert "Total Commands: 1" in log_content
        finally:
            Path(log_path).unlink(missing_ok=True)
