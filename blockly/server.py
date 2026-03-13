#!/usr/bin/env python3
"""
Python backend server for Blockly Desktop App.
Provides a REST API to execute Python code sent from the Electron frontend.
Uses Flask for better request handling.
"""

import argparse
from server.app import create_app


def run_server(host='127.0.0.1', port=5000, debug=False):
    """Start the Flask server."""
    app = create_app()
    print(f"Starting Blockly Python Server at http://{host}:{port}")
    print("Press Ctrl+C to stop")
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Blockly Python Server')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to (default: 5000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()

    run_server(host=args.host, port=args.port, debug=args.debug)
