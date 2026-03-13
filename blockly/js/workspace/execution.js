/**
 * Code Execution Module
 * Handles running Python code on the server and displaying output.
 */

/**
 * Execute the current workspace code on the Python server.
 * This function is called when the user clicks the Run button.
 */
async function runCode() {
  const runBtn = document.getElementById('runBtn');
  const outputContent = document.getElementById('output-content');
  const serverUrl = getServerUrl ? getServerUrl() : 'http://127.0.0.1:5000';

  // Disable button during execution
  runBtn.disabled = true;
  runBtn.textContent = '⏳ Running...';

  // Clear previous output
  outputContent.innerHTML = '';

  try {
    // First check if server is healthy
    try {
      const healthCheck = await fetch(`${serverUrl}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000)
      });
      if (!healthCheck.ok) {
        throw new Error('Server health check failed');
      }
    } catch (healthError) {
      appendOutput('Python server is not running. Please restart the application.', 'error');
      return;
    }

    // Generate Python code from blocks
    const workspace = getWorkspace ? getWorkspace() : null;
    const pythonCode = workspace ? Blockly.Python.workspaceToCode(workspace) : '';

    if (!pythonCode.trim()) {
      appendOutput('No code to execute. Add some blocks first!', 'error');
      return;
    }

    // Send code to Python server
    const response = await fetch(`${serverUrl}/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ code: pythonCode }),
      signal: AbortSignal.timeout(30000) // 30 second timeout
    });

    // Check if response is OK before parsing JSON
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Server error (${response.status}): ${text || 'Unknown error'}`);
    }

    // Try to parse JSON response
    let result;
    try {
      const text = await response.text();
      if (!text) {
        throw new Error('Empty response from server');
      }
      result = JSON.parse(text);
    } catch (parseError) {
      throw new Error(`Invalid JSON response: ${parseError.message}`);
    }

    if (result.success) {
      // Display output
      if (result.stdout) {
        appendOutput(result.stdout, 'stdout');
      }
      if (result.result !== null && result.result !== undefined) {
        appendOutput(`Result: ${result.result}`, 'result');
      }
      if (result.stderr) {
        appendOutput(result.stderr, 'stderr');
      }
    } else {
      appendOutput(`Error: ${result.error}`, 'error');
      if (result.traceback) {
        appendOutput(result.traceback, 'stderr');
      }
    }
  } catch (error) {
    appendOutput(`Connection Error: ${error.message}`, 'error');
    appendOutput('Make sure the Python server is running.', 'stderr');
  } finally {
    runBtn.disabled = false;
    runBtn.textContent = '▶ Run Code';
  }
}

/**
 * Append a line of output to the output panel.
 * @param {string} text - The text to display
 * @param {string} type - The output type ('stdout', 'stderr', 'result', 'error')
 */
function appendOutput(text, type) {
  const outputContent = document.getElementById('output-content');
  if (!outputContent) return;

  const line = document.createElement('div');
  line.className = `output-line output-${type}`;
  line.textContent = text;
  outputContent.appendChild(line);
  outputContent.scrollTop = outputContent.scrollHeight;
}
