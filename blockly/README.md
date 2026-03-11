# Blockly Desktop App

A visual programming desktop application built with Electron and Blockly, featuring a Python backend for code execution. Supports both Windows and macOS.

## Features

- **Visual Block Programming**: Drag and drop blocks to create programs
- **Python Code Generation**: Automatically generates Python code from blocks
- **Code Execution**: Execute generated Python code in a sandboxed environment
- **Cross-Platform**: Works on Windows and macOS
- **Export/Import**: Save and load your block workspaces

## Project Structure

```
blockly-desktop-app/
├── main.js           # Electron main process
├── index.html        # Main application window
├── renderer.js       # Frontend logic and Blockly integration
├── server.py         # Python backend for code execution
└── package.json      # Project configuration
```

## Prerequisites

- [Node.js](https://nodejs.org/) (v18 or higher recommended)
- [Python](https://python.org/) (v3.7 or higher)

## Installation

1. Clone or download this repository
2. Install Node.js dependencies:

```bash
npm install
```

## Running the Application

### Development Mode

Start the application in development mode:

```bash
npm start
# or
npm run dev
```

This will:
1. Start the Python backend server on port 5000
2. Launch the Electron application with Blockly interface

### Building for Production

Build the application for distribution:

```bash
# Build for Windows
npm run build:win

# Build for macOS
npm run build:mac

# Build for both platforms
npm run build:all
```

Built applications will be in the `dist/` directory.

## Usage

1. **Create Programs**: Drag blocks from the toolbox on the left to the workspace
2. **View Generated Code**: The Python code is shown in the right panel
3. **Run Code**: Click the "Run Code" button to execute your program
4. **See Output**: Results and print statements appear in the Output panel
5. **Save/Load**: Use Export/Import buttons to save and load your workspaces

## Available Block Categories

- **Logic**: If statements, comparisons, boolean operations
- **Loops**: For loops, while loops, repeat blocks
- **Math**: Arithmetic operations, mathematical functions
- **Text**: String manipulation and operations
- **Lists**: List creation and manipulation
- **Variables**: Create and use variables
- **Functions**: Define and call custom functions

## Python Backend API

The Python server provides a simple REST API:

- `GET /health` - Check server status
- `POST /execute` - Execute Python code
  - Request body: `{ "code": "print('Hello World')" }`
  - Response: `{ "success": true, "stdout": "", "stderr": "", "result": null }`

## Troubleshooting

### Python Server Not Starting
- Ensure Python 3.7+ is installed and available in your PATH
- On Windows, use `python`; on macOS/Linux, use `python3`

### Port 5000 Already in Use
- The Python server uses port 5000 by default
- If this port is occupied, modify the port in `server.py` and `renderer.js`

### Blockly Not Loading
- Ensure all npm dependencies are installed
- Check the browser console for JavaScript errors

## License

ISC