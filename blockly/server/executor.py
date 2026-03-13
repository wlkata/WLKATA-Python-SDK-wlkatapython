"""
Code execution module for the Blockly server.
Handles safe execution of Python code and captures stdout/stderr.
"""

import sys
import io
import traceback


class CodeExecutor:
    """Handles safe execution of Python code."""

    @staticmethod
    def _safe_globals() -> dict:
        """Return a sandboxed globals dictionary with basic safe builtins."""
        return {
            '__builtins__': {
                'print': print,
                'len': len,
                'range': range,
                'enumerate': enumerate,
                'zip': zip,
                'map': map,
                'filter': filter,
                'sum': sum,
                'min': min,
                'max': max,
                'abs': abs,
                'round': round,
                'pow': pow,
                'divmod': divmod,
                'int': int,
                'float': float,
                'str': str,
                'bool': bool,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set,
                'type': type,
                'isinstance': isinstance,
                'hasattr': hasattr,
                'getattr': getattr,
                'setattr': setattr,
                'dir': dir,
                'chr': chr,
                'ord': ord,
                'hex': hex,
                'bin': bin,
                'oct': oct,
                'format': format,
                'sorted': sorted,
                'reversed': reversed,
                'any': any,
                'all': all,
                'vars': vars,
                'locals': locals,
                'globals': globals,
                'repr': repr,
                'ascii': ascii,
                'callable': callable,
                'classmethod': classmethod,
                'staticmethod': staticmethod,
                'property': property,
                'slice': slice,
                'complex': complex,
                'frozenset': frozenset,
                'bytearray': bytearray,
                'bytes': bytes,
                'memoryview': memoryview,
                'hash': hash,
                'help': help,
                'id': id,
                'input': input,
                'iter': iter,
                'next': next,
                'object': object,
                'super': super,
                '__import__': __import__,
                '__name__': '__main__',
                '__doc__': None,
            }
        }

    @staticmethod
    def execute(code: str) -> dict:
        """
        Execute Python code and return results.

        Returns a dict with:
        - success: bool
        - stdout: captured stdout
        - stderr: captured stderr
        - result: the result of the last expression (if any)
        - error: error message if execution failed
        - traceback: full error traceback if execution failed
        """
        # Create string buffers for stdout and stderr
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        # Save original streams
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        try:
            # Redirect stdout and stderr
            sys.stdout = stdout_buffer
            sys.stderr = stderr_buffer

            # Create a sandboxed globals dict with basic safe builtins
            safe_globals = CodeExecutor._safe_globals()

            # Compile and execute the code
            try:
                compiled = compile(code, '<blockly>', 'exec')
                exec(compiled, safe_globals)

                # Get the result - try to find the last expression value
                result = None
                # Check if there's a last expression to evaluate
                lines = code.strip().split('\n')
                if lines:
                    last_line = lines[-1].strip()
                    # Skip common statements that don't yield a result
                    if last_line and not last_line.startswith(('def ', 'class ', 'if ', 'for ', 'while ', 'import ',
                                                               'from ', '#', 'print', 'try:', 'except', 'finally',
                                                               'with ')):
                        try:
                            result = eval(last_line, safe_globals)
                        except Exception:
                            pass

                return {
                    'success': True,
                    'stdout': stdout_buffer.getvalue(),
                    'stderr': stderr_buffer.getvalue(),
                    'result': repr(result) if result is not None else None
                }
            except SyntaxError as e:
                return {
                    'success': False,
                    'error': f'Syntax Error: {e.msg} at line {e.lineno}',
                    'stdout': stdout_buffer.getvalue(),
                    'stderr': stderr_buffer.getvalue()
                }
            except Exception as e:
                error_msg = traceback.format_exc()
                return {
                    'success': False,
                    'error': str(e),
                    'traceback': error_msg,
                    'stdout': stdout_buffer.getvalue(),
                    'stderr': stderr_buffer.getvalue()
                }
        finally:
            # Restore original streams
            sys.stdout = old_stdout
            sys.stderr = old_stderr
