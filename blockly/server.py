#!/usr/bin/env python3
"""
Python backend server for Blockly Desktop App.
Provides a REST API to execute Python code sent from the Electron frontend.
"""

import json
import sys
import io
import traceback
import inspect
import builtins
import importlib
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread


class FunctionInspector:
    """Handles introspection of Python functions for Blockly blocks."""

    # Available built-in functions that users can call
    AVAILABLE_BUILTINS = [
        'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'chr', 'complex',
        'dict', 'dir', 'divmod', 'enumerate', 'filter', 'float', 'format',
        'frozenset', 'hash', 'hex', 'id', 'input', 'int', 'isinstance',
        'iter', 'len', 'list', 'map', 'max', 'min', 'next', 'oct', 'ord',
        'pow', 'print', 'range', 'repr', 'reversed', 'round', 'set',
        'slice', 'sorted', 'str', 'sum', 'tuple', 'type', 'zip',
    ]

    @staticmethod
    def inspect_function(func_name: str) -> dict:
        """
        Inspect a function and return its signature information.

        Returns a dict with:
        - success: bool
        - name: function name
        - docstring: function docstring
        - parameters: list of parameter info dicts
        - error: error message if inspection failed
        """
        try:
            # Check if it's a module.function pattern
            if '.' in func_name:
                parts = func_name.rsplit('.', 1)
                module_path = parts[0]
                function_name = parts[1]
                try:
                    module = importlib.import_module(module_path)
                    func = getattr(module, function_name)
                except (ImportError, AttributeError):
                    return {
                        'success': False,
                        'error': f'Function "{function_name}" not found in module "{module_path}"'
                    }
            else:
                # Try to get the function from builtins
                if func_name not in FunctionInspector.AVAILABLE_BUILTINS:
                    # Also check if it's a valid builtin not in our restricted list
                    if not hasattr(builtins, func_name):
                        return {
                            'success': False,
                            'error': f'Function "{func_name}" not found in available builtins'
                        }

                func = getattr(builtins, func_name)

            if not callable(func):
                return {
                    'success': False,
                    'error': f'"{func_name}" is not callable'
                }

            # Get docstring
            docstring = inspect.getdoc(func) or 'No documentation available.'

            # Get signature
            try:
                sig = inspect.signature(func)
            except (ValueError, TypeError):
                # Some builtins don't have inspectable signatures
                return {
                    'success': True,
                    'name': func_name,
                    'docstring': docstring,
                    'parameters': [],
                    'has_varargs': False,
                    'has_varkwargs': False
                }

            parameters = []
            has_varargs = False
            has_varkwargs = False

            for param_name, param in sig.parameters.items():
                param_info = {
                    'name': param_name,
                    'kind': str(param.kind.name),
                }

                # Determine the kind
                if param.kind == inspect.Parameter.VAR_POSITIONAL:
                    param_info['kind'] = 'VAR_POSITIONAL'
                    param_info['is_varargs'] = True
                    has_varargs = True
                elif param.kind == inspect.Parameter.VAR_KEYWORD:
                    param_info['kind'] = 'VAR_KEYWORD'
                    param_info['is_varkwargs'] = True
                    has_varkwargs = True
                elif param.kind == inspect.Parameter.KEYWORD_ONLY:
                    param_info['kind'] = 'KEYWORD_ONLY'
                    param_info['is_keyword_only'] = True
                elif param.kind == inspect.Parameter.POSITIONAL_ONLY:
                    param_info['kind'] = 'POSITIONAL_ONLY'
                    param_info['is_positional_only'] = True
                else:
                    param_info['kind'] = 'POSITIONAL_OR_KEYWORD'

                # Get default value
                if param.default is not inspect.Parameter.empty:
                    param_info['has_default'] = True
                    # Convert default to a string representation for display
                    try:
                        param_info['default'] = repr(param.default)
                    except:
                        param_info['default'] = str(param.default)
                else:
                    param_info['has_default'] = False
                    param_info['default'] = None

                # Get annotation if available
                if param.annotation is not inspect.Parameter.empty:
                    try:
                        param_info['annotation'] = str(param.annotation)
                    except:
                        param_info['annotation'] = None
                else:
                    param_info['annotation'] = None

                parameters.append(param_info)

            return {
                'success': True,
                'name': func_name,
                'docstring': docstring,
                'parameters': parameters,
                'has_varargs': has_varargs,
                'has_varkwargs': has_varkwargs
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error inspecting function: {str(e)}'
            }

    @staticmethod
    def list_available_functions() -> list:
        """Return a list of available function names."""
        return FunctionInspector.AVAILABLE_BUILTINS

    @staticmethod
    def list_module_functions(module_path: str) -> dict:
        """List all public functions in a module."""
        try:
            module = importlib.import_module(module_path)
            functions = []
            for name, obj in inspect.getmembers(module):
                # Only include public functions/callables
                if not name.startswith('_') and callable(obj):
                    functions.append(f"{module_path}.{name}")

            return {
                'success': True,
                'module': module_path,
                'functions': sorted(functions)
            }
        except ImportError as e:
            return {
                'success': False,
                'error': f'Module "{module_path}" not found: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error listing functions for "{module_path}": {str(e)}'
            }


class CodeExecutor:
    """Handles safe execution of Python code."""

    @staticmethod
    def _safe_globals() -> dict:
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
                    if last_line and not last_line.startswith(('def ', 'class ', 'if ', 'for ', 'while ', 'import ',
                                                               'from ', '#', 'print', 'try:', 'except', 'finally',
                                                               'with ')):
                        try:
                            result = eval(last_line, safe_globals)
                        except:
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


class RequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Blockly server."""

    def _build_safe_globals(self, code: str) -> dict:
        # Extract imports to load third-party libraries in advance
        import_lines = []
        for line in code.split('\n'):
            if line.strip().startswith(('import ', 'from ')):
                import_lines.append(line)

        safe_globals = CodeExecutor._safe_globals()
        for imp in import_lines:
            try:
                exec(imp, safe_globals)
            except Exception:
                pass

        try:
            exec(compile(code, '<blockly>', 'exec'), safe_globals)
        except Exception:
            # Ignore execution errors; we just need whatever variables did get defined
            pass

        return safe_globals

    def _inspect_instance_members(self, code: str, instance_name: str) -> dict:
        try:
            safe_globals = self._build_safe_globals(code)

            if instance_name not in safe_globals:
                return {
                    'success': False,
                    'error': f'Instance "{instance_name}" not found. Make sure the code defining it is valid.'
                }

            instance = safe_globals[instance_name]
            methods = []
            fields = []

            for name, attr in inspect.getmembers(instance):
                if name.startswith('_'):
                    continue

                if callable(attr):
                    methods.append(name)
                else:
                    fields.append(name)

            return {
                'success': True,
                'instance': instance_name,
                'class_name': type(instance).__name__,
                'methods': sorted(methods),
                'fields': sorted(fields)
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error inspecting instance: {str(e)}'
            }

    def _inspect_instance_method(self, code: str, instance_name: str, method_name: str) -> dict:
        try:
            safe_globals = self._build_safe_globals(code)

            if instance_name not in safe_globals:
                return {
                    'success': False,
                    'error': f'Instance "{instance_name}" not found. Make sure the code defining it is valid.'
                }

            instance = safe_globals[instance_name]
            if not hasattr(instance, method_name):
                return {
                    'success': False,
                    'error': f'Method "{method_name}" not found on instance "{instance_name}"'
                }

            method = getattr(instance, method_name)
            if not callable(method):
                return {
                    'success': False,
                    'error': f'"{method_name}" is not callable on "{instance_name}"'
                }

            docstring = inspect.getdoc(method) or 'No documentation available.'
            try:
                sig = inspect.signature(method)
            except (ValueError, TypeError):
                return {
                    'success': True,
                    'name': method_name,
                    'docstring': docstring,
                    'parameters': [],
                    'has_varargs': False,
                    'has_varkwargs': False
                }

            parameters = []
            has_varargs = False
            has_varkwargs = False

            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue

                param_info = {
                    'name': param_name,
                    'kind': str(param.kind.name),
                }

                if param.kind == inspect.Parameter.VAR_POSITIONAL:
                    param_info['kind'] = 'VAR_POSITIONAL'
                    param_info['is_varargs'] = True
                    has_varargs = True
                elif param.kind == inspect.Parameter.VAR_KEYWORD:
                    param_info['kind'] = 'VAR_KEYWORD'
                    param_info['is_varkwargs'] = True
                    has_varkwargs = True
                elif param.kind == inspect.Parameter.KEYWORD_ONLY:
                    param_info['kind'] = 'KEYWORD_ONLY'
                    param_info['is_keyword_only'] = True
                elif param.kind == inspect.Parameter.POSITIONAL_ONLY:
                    param_info['kind'] = 'POSITIONAL_ONLY'
                    param_info['is_positional_only'] = True
                else:
                    param_info['kind'] = 'POSITIONAL_OR_KEYWORD'

                if param.default is not inspect.Parameter.empty:
                    param_info['has_default'] = True
                    try:
                        param_info['default'] = repr(param.default)
                    except:
                        param_info['default'] = str(param.default)
                else:
                    param_info['has_default'] = False
                    param_info['default'] = None

                if param.annotation is not inspect.Parameter.empty:
                    try:
                        param_info['annotation'] = str(param.annotation)
                    except:
                        param_info['annotation'] = None
                else:
                    param_info['annotation'] = None

                parameters.append(param_info)

            return {
                'success': True,
                'name': method_name,
                'docstring': docstring,
                'parameters': parameters,
                'has_varargs': has_varargs,
                'has_varkwargs': has_varkwargs
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error inspecting method: {str(e)}'
            }

    def log_message(self, format, *args):
        """Override to customize logging."""
        print(f"[Server] {format % args}")

    def _send_json_response(self, data: dict, status: int = 200):
        """Send a JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/health':
            self._send_json_response({'status': 'ok', 'message': 'Blockly Python Server is running'})
        elif self.path == '/functions':
            # Return list of available functions
            self._send_json_response({
                'success': True,
                'functions': FunctionInspector.list_available_functions()
            })
        else:
            self._send_json_response({'error': 'Not found'}, 404)

    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/execute':
            # Get content length
            content_length = int(self.headers.get('Content-Length', 0))

            # Read request body
            post_data = self.rfile.read(content_length).decode('utf-8')

            try:
                # Parse JSON
                request = json.loads(post_data)
                code = request.get('code', '')

                if not code:
                    self._send_json_response({
                        'success': False,
                        'error': 'No code provided'
                    }, 400)
                    return

                # Execute the code
                result = CodeExecutor.execute(code)
                self._send_json_response(result)

            except json.JSONDecodeError as e:
                self._send_json_response({
                    'success': False,
                    'error': f'Invalid JSON: {str(e)}'
                }, 400)
            except Exception as e:
                self._send_json_response({
                    'success': False,
                    'error': f'Server error: {str(e)}'
                }, 500)
        elif self.path == '/inspect':
            # Inspect a function
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')

            try:
                request = json.loads(post_data)
                func_name = request.get('function', '')

                if not func_name:
                    self._send_json_response({
                        'success': False,
                        'error': 'No function name provided'
                    }, 400)
                    return

                result = FunctionInspector.inspect_function(func_name)
                self._send_json_response(result)

            except json.JSONDecodeError as e:
                self._send_json_response({
                    'success': False,
                    'error': f'Invalid JSON: {str(e)}'
                }, 400)
            except Exception as e:
                self._send_json_response({
                    'success': False,
                    'error': f'Server error: {str(e)}'
                }, 500)
        elif self.path == '/import':
            # List functions in a module
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')

            try:
                request = json.loads(post_data)
                module_name = request.get('module', '')

                if not module_name:
                    self._send_json_response({
                        'success': False,
                        'error': 'No module name provided'
                    }, 400)
                    return

                result = FunctionInspector.list_module_functions(module_name)
                self._send_json_response(result)

            except json.JSONDecodeError as e:
                self._send_json_response({
                    'success': False,
                    'error': f'Invalid JSON: {str(e)}'
                }, 400)
            except Exception as e:
                self._send_json_response({
                    'success': False,
                    'error': f'Server error: {str(e)}'
                }, 500)
        elif self.path == '/inspect-instance':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')

            try:
                request = json.loads(post_data)
                code = request.get('code', '')
                instance_name = request.get('instance', '')

                if not code:
                    self._send_json_response({
                        'success': False,
                        'error': 'No code provided'
                    }, 400)
                    return

                if not instance_name:
                    self._send_json_response({
                        'success': False,
                        'error': 'No instance name provided'
                    }, 400)
                    return

                result = self._inspect_instance_members(code, instance_name)
                self._send_json_response(result)

            except json.JSONDecodeError as e:
                self._send_json_response({
                    'success': False,
                    'error': f'Invalid JSON: {str(e)}'
                }, 400)
            except Exception as e:
                self._send_json_response({
                    'success': False,
                    'error': f'Server error: {str(e)}'
                }, 500)
        elif self.path == '/inspect-instance-method':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')

            try:
                request = json.loads(post_data)
                code = request.get('code', '')
                instance_name = request.get('instance', '')
                method_name = request.get('method', '')

                if not code:
                    self._send_json_response({
                        'success': False,
                        'error': 'No code provided'
                    }, 400)
                    return

                if not instance_name:
                    self._send_json_response({
                        'success': False,
                        'error': 'No instance name provided'
                    }, 400)
                    return

                if not method_name:
                    self._send_json_response({
                        'success': False,
                        'error': 'No method name provided'
                    }, 400)
                    return

                result = self._inspect_instance_method(code, instance_name, method_name)
                self._send_json_response(result)

            except json.JSONDecodeError as e:
                self._send_json_response({
                    'success': False,
                    'error': f'Invalid JSON: {str(e)}'
                }, 400)
            except Exception as e:
                self._send_json_response({
                    'success': False,
                    'error': f'Server error: {str(e)}'
                }, 500)
        else:
            self._send_json_response({'error': 'Not found'}, 404)


def run_server(host='127.0.0.1', port=5000):
    """Start the HTTP server."""
    server = HTTPServer((host, port), RequestHandler)
    print(f"Starting Blockly Python Server at http://{host}:{port}")
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()


if __name__ == '__main__':
    run_server()