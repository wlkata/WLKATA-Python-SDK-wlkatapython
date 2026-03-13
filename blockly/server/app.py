"""
Flask application and routes for the Blockly server.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from .executor import CodeExecutor
from .inspector import FunctionInspector, InstanceInspector

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'message': 'Blockly Python Server is running'})


@app.route('/functions', methods=['GET'])
def list_functions():
    """Return list of available built-in functions."""
    return jsonify({
        'success': True,
        'functions': FunctionInspector.list_available_functions()
    })


@app.route('/execute', methods=['POST'])
def execute_code():
    """Execute Python code."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400

        code = data.get('code', '')
        if not code:
            return jsonify({'success': False, 'error': 'No code provided'}), 400

        result = CodeExecutor.execute(code)
        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500


@app.route('/inspect', methods=['POST'])
def inspect_function():
    """Inspect a function signature."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400

        func_name = data.get('function', '')
        if not func_name:
            return jsonify({'success': False, 'error': 'No function name provided'}), 400

        result = FunctionInspector.inspect_function(func_name)
        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500


@app.route('/import', methods=['POST'])
def import_module():
    """List functions in a module."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400

        module_name = data.get('module', '')
        if not module_name:
            return jsonify({'success': False, 'error': 'No module name provided'}), 400

        result = FunctionInspector.list_module_functions(module_name)
        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500


@app.route('/inspect-instance', methods=['POST'])
def inspect_instance():
    """Inspect instance members (methods and fields)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400

        code = data.get('code', '')
        instance_name = data.get('instance', '')

        if not code:
            return jsonify({'success': False, 'error': 'No code provided'}), 400

        if not instance_name:
            return jsonify({'success': False, 'error': 'No instance name provided'}), 400

        result = InstanceInspector.inspect_instance_members(code, instance_name)
        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500


@app.route('/inspect-instance-method', methods=['POST'])
def inspect_instance_method():
    """Inspect a specific instance method."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400

        code = data.get('code', '')
        instance_name = data.get('instance', '')
        method_name = data.get('method', '')

        if not code:
            return jsonify({'success': False, 'error': 'No code provided'}), 400

        if not instance_name:
            return jsonify({'success': False, 'error': 'No instance name provided'}), 400

        if not method_name:
            return jsonify({'success': False, 'error': 'No method name provided'}), 400

        result = InstanceInspector.inspect_instance_method(code, instance_name, method_name)
        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500


def create_app():
    """Factory function to create the Flask app."""
    return app
