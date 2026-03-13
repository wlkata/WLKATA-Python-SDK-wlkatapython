"""
Introspection module for the Blockly server.
Handles inspection of functions, modules, and instances.
"""

import inspect
import builtins
import importlib
from .executor import CodeExecutor


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
                    try:
                        param_info['default'] = repr(param.default)
                    except Exception:
                        param_info['default'] = str(param.default)
                else:
                    param_info['has_default'] = False
                    param_info['default'] = None

                # Get annotation if available
                if param.annotation is not inspect.Parameter.empty:
                    try:
                        param_info['annotation'] = str(param.annotation)
                    except Exception:
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


class InstanceInspector:
    """Handles introspection of instance members."""

    @staticmethod
    def _build_safe_globals(code: str) -> dict:
        """Build safe globals dict by executing code and extracting imports."""
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

    @staticmethod
    def inspect_instance_members(code: str, instance_name: str) -> dict:
        """Inspect instance members (methods and fields)."""
        try:
            safe_globals = InstanceInspector._build_safe_globals(code)

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

    @staticmethod
    def inspect_instance_method(code: str, instance_name: str, method_name: str) -> dict:
        """Inspect a specific instance method."""
        try:
            safe_globals = InstanceInspector._build_safe_globals(code)

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
                    except Exception:
                        param_info['default'] = str(param.default)
                else:
                    param_info['has_default'] = False
                    param_info['default'] = None

                if param.annotation is not inspect.Parameter.empty:
                    try:
                        param_info['annotation'] = str(param.annotation)
                    except Exception:
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
