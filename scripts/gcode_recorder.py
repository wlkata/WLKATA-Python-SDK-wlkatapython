#!/usr/bin/env python
"""
G-code Recorder Script

This script starts a simulated serial connection that:
1. Responds to commands like real hardware
2. Records all received G-code commands to a file with timestamps

Usage:
    python scripts/gcode_recorder.py [OPTIONS]
    
    # Start recorder with default settings (Mirobot, output to gcode_log.txt)
    python scripts/gcode_recorder.py
    
    # Specify model and output file
    python scripts/gcode_recorder.py --model e4 --output my_commands.log
    
    # With verbose output
    python scripts/gcode_recorder.py -v
    
    # Run until specific number of commands received
    python scripts/gcode_recorder.py --max-commands 100

The script will print the virtual serial port path. Connect your application
to this port to have commands recorded.

Press Ctrl+C to stop recording.
"""

import argparse
import sys
import time
import signal
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, TextIO

# Prefer installed package; when run from a checkout, put src/ on path.
_project_root = Path(__file__).parent.parent
_src = _project_root / "src"
if _src.is_dir() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from wlkatapython.simulator import (
    MirobotSimulator,
    E4Simulator,
    MT4Simulator,
    MS4220Simulator,
    create_simulator,
    SimulatedHardware,
)


class GCodeRecorder:
    """
    A wrapper around simulators that records all received commands.
    """
    
    def __init__(
        self,
        model: str = "mirobot",
        address: int = -1,
        output_file: str = "gcode_log.txt",
        verbose: bool = False,
        max_commands: Optional[int] = None,
        timestamp_format: str = "%Y-%m-%d %H:%M:%S.%f",
    ):
        """
        Initialize the G-code recorder.
        
        Args:
            model: Robot model to simulate (mirobot, e4, mt4, ms4220)
            address: RS485 address (-1 for UART mode)
            output_file: Path to the output log file
            verbose: Print commands to console as they're received
            max_commands: Stop after receiving this many commands (None = unlimited)
            timestamp_format: Format for timestamps in the log
        """
        self.model = model
        self.address = address
        self.output_file = Path(output_file)
        self.verbose = verbose
        self.max_commands = max_commands
        self.timestamp_format = timestamp_format
        
        self._simulator: Optional[SimulatedHardware] = None
        self._log_file: Optional[TextIO] = None
        self._command_count = 0
        self._running = False
        self._lock = threading.Lock()
        
        # Original command handler reference
        self._original_handle_command = None
    
    def _create_simulator(self) -> SimulatedHardware:
        """Create the appropriate simulator based on model."""
        return create_simulator(self.model, self.address)
    
    def _wrap_command_handler(self):
        """
        Wrap the simulator's command handler to intercept and log commands.
        """
        original_handler = self._simulator._handle_command
        
        def wrapped_handler(command: str):
            # Log the command
            self._log_command(command)
            
            # Check max commands limit
            if self.max_commands and self._command_count >= self.max_commands:
                print(f"\nMax commands ({self.max_commands}) reached. Stopping...")
                self._running = False
                return
            
            # Call original handler
            return original_handler(command)
        
        self._simulator._handle_command = wrapped_handler
    
    def _log_command(self, command: str):
        """Log a command to the file and optionally to console."""
        with self._lock:
            self._command_count += 1
            timestamp = datetime.now().strftime(self.timestamp_format)
            
            # Format log entry
            log_entry = f"[{timestamp}] #{self._command_count}: {command}"
            
            # Write to file
            if self._log_file:
                self._log_file.write(log_entry + "\n")
                self._log_file.flush()  # Ensure immediate write
            
            # Print to console if verbose
            if self.verbose:
                print(f"  Received: {command}")
    
    def start(self) -> str:
        """
        Start the recorder.
        
        Returns:
            The path to the virtual serial port.
        """
        # Create simulator
        self._simulator = self._create_simulator()
        
        # Open log file
        self._log_file = open(self.output_file, "a", encoding="utf-8")
        
        # Write header
        header = (
            f"\n{'='*60}\n"
            f"G-Code Recording Session\n"
            f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Model: {self.model}\n"
            f"Address: {self.address}\n"
            f"{'='*60}\n"
        )
        self._log_file.write(header)
        self._log_file.flush()
        
        # Wrap command handler before starting
        self._wrap_command_handler()
        
        # Start simulator
        port_path = self._simulator.start()
        self._running = True
        
        return port_path
    
    def stop(self):
        """Stop the recorder and close files."""
        self._running = False
        
        if self._simulator:
            self._simulator.stop()
            self._simulator = None
        
        if self._log_file:
            # Write footer
            footer = (
                f"\n{'='*60}\n"
                f"Recording Session Ended\n"
                f"Stopped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Total Commands: {self._command_count}\n"
                f"{'='*60}\n\n"
            )
            self._log_file.write(footer)
            self._log_file.close()
            self._log_file = None
    
    def wait(self):
        """Wait until recording should stop."""
        try:
            while self._running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
    
    @property
    def command_count(self) -> int:
        """Get the number of commands recorded."""
        return self._command_count
    
    @property
    def is_running(self) -> bool:
        """Check if the recorder is running."""
        return self._running
    
    @property
    def port_path(self) -> Optional[str]:
        """Get the virtual serial port path."""
        if self._simulator:
            return self._simulator.port_path
        return None
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Record G-code commands sent to a simulated robot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              Start with defaults (Mirobot)
  %(prog)s --model e4                    Simulate E4 robot
  %(prog)s --output session.log          Save to custom file
  %(prog)s -v                            Verbose output
  %(prog)s --max-commands 50             Stop after 50 commands
  %(prog)s --model ms4220 --address 10   MS4220 with RS485 address

The script prints the virtual serial port path (e.g., /dev/pts/3).
Connect your application to this port to record commands.
        """
    )
    
    parser.add_argument(
        "--model", "-m",
        choices=["mirobot", "e4", "mt4", "ms4220"],
        default="mirobot",
        help="Robot model to simulate (default: mirobot)"
    )
    
    parser.add_argument(
        "--address", "-a",
        type=int,
        default=-1,
        help="RS485 address (-1 for UART mode, default: -1)"
    )
    
    parser.add_argument(
        "--output", "-o",
        default="gcode_log.txt",
        help="Output file for recorded commands (default: gcode_log.txt)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print commands to console as received"
    )
    
    parser.add_argument(
        "--max-commands", "-n",
        type=int,
        default=None,
        help="Stop after receiving this many commands"
    )
    
    parser.add_argument(
        "--append", 
        action="store_true",
        help="Append to existing log file instead of overwriting"
    )
    
    args = parser.parse_args()
    
    # Handle file mode
    output_path = Path(args.output)
    if not args.append and output_path.exists():
        # Clear existing file if not appending
        output_path.write_text("")
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    G-Code Recorder                           ║
╠══════════════════════════════════════════════════════════════╣
║  Model: {args.model:<52} ║
║  Address: {args.address:<50} ║
║  Output: {str(args.output):<51} ║
║  Verbose: {str(args.verbose):<50} ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    # Create and start recorder
    recorder = GCodeRecorder(
        model=args.model,
        address=args.address,
        output_file=args.output,
        verbose=args.verbose,
        max_commands=args.max_commands,
    )
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n\nStopping recorder...")
        recorder.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        port_path = recorder.start()
        
        print(f"╔══════════════════════════════════════════════════════════════╗")
        print(f"║  VIRTUAL SERIAL PORT: {port_path:<38} ║")
        print(f"╚══════════════════════════════════════════════════════════════╝")
        print()
        print("Connect your application to this port.")
        print("Commands will be logged to:", args.output)
        print()
        print("Press Ctrl+C to stop recording...")
        print()
        
        if args.verbose:
            print("--- Commands ---")
        
        # Wait for commands
        recorder.wait()
        
    finally:
        recorder.stop()
        print(f"\nRecording complete. {recorder.command_count} commands logged to {args.output}")


if __name__ == "__main__":
    main()
