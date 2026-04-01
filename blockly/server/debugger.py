"""
Step-by-step debugger for Blockly code execution.

Uses sys.settrace() to pause execution at each line and a threading.Event
to synchronise with the frontend.  Each debug session runs the user code
in a dedicated daemon thread so the Flask request thread is never blocked
for more than the step-wait timeout.
"""

import sys
import io
import threading
import traceback
import uuid
import copy
from .executor import CodeExecutor


class DebugSession:
    """Represents a single step-debug session."""

    def __init__(self, code: str, session_id: str):
        self.session_id = session_id
        self.code = code

        # Synchronisation primitives
        self._step_event = threading.Event()   # signalled by /step to advance
        self._state_ready = threading.Event()  # signalled by trace when paused
        self._lock = threading.Lock()

        # Control flags
        self.stopped = False       # /stop requested
        self.continuing = False    # /continue requested (run without pausing)
        self.finished = False      # execution completed

        # Current state (written by trace callback, read by /step response)
        self.current_line = None
        self.current_variables = {}
        self.current_call_stack = []
        self.current_event = None  # 'line', 'call', 'return', 'exception'

        # Output capture
        self.stdout_buffer = io.StringIO()
        self.stderr_buffer = io.StringIO()
        self._last_stdout_pos = 0   # track incremental stdout reads

        # Execution result
        self.error = None
        self.error_traceback = None

        # The background thread running the user code
        self._thread = None

        # The source filename used in compile() – needed to filter traces
        self._filename = '<blockly>'

    # ── Public API (called from Flask routes) ──────────────────────

    def start(self) -> dict:
        """Compile the code, start the execution thread, wait for first pause."""
        try:
            self._compiled = compile(self.code, self._filename, 'exec')
        except SyntaxError as e:
            self.finished = True
            return {
                'success': False,
                'error': f'Syntax Error: {e.msg} at line {e.lineno}',
            }

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

        # Wait for the trace to pause on the first line (or finish)
        ready = self._state_ready.wait(timeout=10)
        if not ready and not self.finished:
            self.stopped = True
            return {'success': False, 'error': 'Timeout waiting for first trace event'}

        return self._build_state_response()

    def step(self) -> dict:
        """Advance execution by one line."""
        if self.finished:
            return self._build_state_response()

        # Clear state-ready so we can wait for the next pause
        self._state_ready.clear()

        # Signal the trace callback to continue
        self._step_event.set()

        # Wait for the trace to pause again (or finish)
        ready = self._state_ready.wait(timeout=30)
        if not ready and not self.finished:
            # Execution may have completed between signal and wait
            pass

        return self._build_state_response()

    def continue_run(self) -> dict:
        """Run the rest of the code without pausing."""
        self.continuing = True
        self._state_ready.clear()
        self._step_event.set()

        # Wait for execution to finish
        self._thread.join(timeout=30)
        self.finished = True

        return self._build_state_response()

    def stop(self) -> dict:
        """Abort execution."""
        self.stopped = True
        self._step_event.set()  # unblock the trace if it's waiting
        if self._thread:
            self._thread.join(timeout=5)
        self.finished = True
        return {'success': True, 'finished': True}

    # ── Trace callback (runs in the code thread) ──────────────────

    def _trace_dispatch(self, frame, event, arg):
        """sys.settrace callback – called for every line/call/return."""
        # Only trace our own code, not library internals
        if frame.f_code.co_filename != self._filename:
            return self._trace_dispatch

        # Stop requested
        if self.stopped:
            sys.settrace(None)
            raise SystemExit('Debug session stopped')

        # Continue mode – don't pause
        if self.continuing:
            return self._trace_dispatch

        # We only pause on 'line' events (not call/return/exception)
        if event != 'line':
            return self._trace_dispatch

        # ── Capture current state ──
        with self._lock:
            self.current_line = frame.f_lineno
            self.current_event = event
            self.current_variables = self._capture_variables(frame)
            self.current_call_stack = self._capture_call_stack(frame)

        # Signal that state is ready for the frontend to read
        self._state_ready.set()

        # Block until /step signals us to continue
        self._step_event.wait()
        self._step_event.clear()

        # Check stop again after waking up
        if self.stopped:
            sys.settrace(None)
            raise SystemExit('Debug session stopped')

        return self._trace_dispatch

    # ── Code execution thread ─────────────────────────────────────

    def _run(self):
        """Execute the user code with tracing enabled."""
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        try:
            sys.stdout = self.stdout_buffer
            sys.stderr = self.stderr_buffer

            safe_globals = CodeExecutor._safe_globals()
            sys.settrace(self._trace_dispatch)
            try:
                exec(self._compiled, safe_globals)
            except SystemExit:
                pass  # normal stop
            except Exception as e:
                self.error = str(e)
                self.error_traceback = traceback.format_exc()
            finally:
                sys.settrace(None)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            self.finished = True
            # Signal state-ready so any waiting /step call unblocks
            self._state_ready.set()

    # ── Helpers ────────────────────────────────────────────────────

    def _capture_variables(self, frame) -> dict:
        """Snapshot the local variables from the current frame."""
        variables = {}
        for name, value in frame.f_locals.items():
            if name.startswith('__'):
                continue
            try:
                variables[name] = {
                    'value': repr(value),
                    'type': type(value).__name__,
                }
            except Exception:
                variables[name] = {
                    'value': '<unrepresentable>',
                    'type': type(value).__name__,
                }
        return variables

    def _capture_call_stack(self, frame) -> list:
        """Walk frame.f_back to build a call-stack list."""
        stack = []
        f = frame
        while f is not None:
            if f.f_code.co_filename == self._filename:
                stack.append({
                    'line': f.f_lineno,
                    'function': f.f_code.co_name,
                })
            f = f.f_back
        return stack  # innermost first

    def _get_new_stdout(self) -> str:
        """Return only the stdout produced since the last read."""
        full = self.stdout_buffer.getvalue()
        new = full[self._last_stdout_pos:]
        self._last_stdout_pos = len(full)
        return new

    def _build_state_response(self) -> dict:
        """Build the JSON response dict for the current state."""
        with self._lock:
            resp = {
                'success': True,
                'session_id': self.session_id,
                'finished': self.finished,
                'line': self.current_line,
                'variables': self.current_variables,
                'call_stack': self.current_call_stack,
                'stdout': self._get_new_stdout(),
                'stderr': self.stderr_buffer.getvalue(),
            }
            if self.error:
                resp['error'] = self.error
                resp['traceback'] = self.error_traceback
            return resp


class StepDebugger:
    """Manages multiple debug sessions (though typically only one is active)."""

    _sessions: dict[str, DebugSession] = {}
    _lock = threading.Lock()

    @classmethod
    def start(cls, code: str) -> dict:
        """Create a new debug session and return initial state."""
        session_id = str(uuid.uuid4())
        session = DebugSession(code, session_id)
        with cls._lock:
            cls._sessions[session_id] = session
        return session.start()

    @classmethod
    def step(cls, session_id: str) -> dict:
        """Advance one line in the given session."""
        session = cls._get_session(session_id)
        if not session:
            return {'success': False, 'error': 'Session not found'}
        result = session.step()
        if session.finished:
            cls._cleanup(session_id)
        return result

    @classmethod
    def continue_run(cls, session_id: str) -> dict:
        """Run remaining code without pausing."""
        session = cls._get_session(session_id)
        if not session:
            return {'success': False, 'error': 'Session not found'}
        result = session.continue_run()
        cls._cleanup(session_id)
        return result

    @classmethod
    def stop(cls, session_id: str) -> dict:
        """Stop and clean up a debug session."""
        session = cls._get_session(session_id)
        if not session:
            return {'success': False, 'error': 'Session not found'}
        result = session.stop()
        cls._cleanup(session_id)
        return result

    @classmethod
    def _get_session(cls, session_id: str) -> DebugSession | None:
        with cls._lock:
            return cls._sessions.get(session_id)

    @classmethod
    def _cleanup(cls, session_id: str):
        with cls._lock:
            cls._sessions.pop(session_id, None)
