/**
 * Debug Execution Module
 * Handles step-by-step debugging of Python code via the server's
 * /debug/start, /debug/step, /debug/continue, /debug/stop endpoints.
 */

// ── Debug session state ──────────────────────────────────────────
var _debugSessionId = null;
var _debugLineToBlock = {};  // line number -> block id
var _debugActive = false;
var _debugHighlightedBlock = null;  // currently highlighted block id

/**
 * Start a debug session.
 */
async function debugStart() {
  var workspace = getWorkspace ? getWorkspace() : null;
  var serverUrl = getServerUrl ? getServerUrl() : 'http://127.0.0.1:5080';
  if (!workspace) return;

  // Generate code + line-to-block map in one pass
  var generated = generateCodeWithMap(workspace);
  var pythonCode = generated.code;
  _debugLineToBlock = generated.lineToBlock;

  if (!pythonCode.trim()) {
    appendOutput('No code to debug. Add some blocks first!', 'error');
    return;
  }

  console.log('[Debug] Line-to-block map:', _debugLineToBlock);

  // Clear previous output
  var outputContent = document.getElementById('output-content');
  if (outputContent) outputContent.innerHTML = '';

  // Show debug UI
  _setDebugMode(true);

  try {
    var response = await fetch(serverUrl + '/debug/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: pythonCode }),
      signal: AbortSignal.timeout(15000)
    });

    var result = await response.json();
    if (result.success) {
      _debugSessionId = result.session_id;
      _debugActive = true;
      _applyDebugState(result);
    } else {
      appendOutput('Debug error: ' + (result.error || 'Unknown error'), 'error');
      _setDebugMode(false);
    }
  } catch (error) {
    appendOutput('Debug connection error: ' + error.message, 'error');
    _setDebugMode(false);
  }
}

/**
 * Step one line forward.
 */
async function debugStep() {
  if (!_debugSessionId || !_debugActive) return;
  var serverUrl = getServerUrl ? getServerUrl() : 'http://127.0.0.1:5080';

  // Disable step button during request to prevent double-clicks
  var stepBtn = document.getElementById('stepBtn');
  if (stepBtn) stepBtn.disabled = true;

  try {
    var response = await fetch(serverUrl + '/debug/step', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: _debugSessionId }),
      signal: AbortSignal.timeout(35000)
    });

    var result = await response.json();
    if (result.success) {
      _applyDebugState(result);
      if (result.finished) {
        _endDebugSession('Execution finished.');
      }
    } else {
      appendOutput('Step error: ' + (result.error || 'Unknown error'), 'error');
      _endDebugSession();
    }
  } catch (error) {
    appendOutput('Step error: ' + error.message, 'error');
    _endDebugSession();
  } finally {
    if (stepBtn) stepBtn.disabled = false;
  }
}

/**
 * Continue running without pausing.
 */
async function debugContinue() {
  if (!_debugSessionId || !_debugActive) return;
  var serverUrl = getServerUrl ? getServerUrl() : 'http://127.0.0.1:5080';

  _setDebugButtonsEnabled(false);
  appendOutput('Continuing execution...', 'stdout');

  try {
    var response = await fetch(serverUrl + '/debug/continue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: _debugSessionId }),
      signal: AbortSignal.timeout(35000)
    });

    var result = await response.json();
    if (result.success) {
      // Show any remaining output
      if (result.stdout) appendOutput(result.stdout, 'stdout');
      if (result.stderr) appendOutput(result.stderr, 'stderr');
      if (result.error) appendOutput('Error: ' + result.error, 'error');
    }
    _endDebugSession('Execution completed.');
  } catch (error) {
    appendOutput('Continue error: ' + error.message, 'error');
    _endDebugSession();
  }
}

/**
 * Stop the debug session.
 */
async function debugStop() {
  if (!_debugSessionId) {
    _setDebugMode(false);
    return;
  }
  var serverUrl = getServerUrl ? getServerUrl() : 'http://127.0.0.1:5080';

  try {
    await fetch(serverUrl + '/debug/stop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: _debugSessionId }),
      signal: AbortSignal.timeout(5000)
    });
  } catch (e) {
    // Ignore errors on stop
  }
  _endDebugSession('Debug session stopped.');
}

// ── Internal helpers ─────────────────────────────────────────────

/**
 * Apply the debug state from a server response to the UI.
 */
function _applyDebugState(state) {
  var workspace = getWorkspace ? getWorkspace() : null;

  // Highlight the current block
  if (workspace && state.line) {
    // Clear previous highlight
    _clearDebugActive(workspace);

    var blockId = _debugLineToBlock[state.line];
    if (blockId) {
      _debugHighlightedBlock = blockId;
      _applyDebugActive(workspace, blockId);
      workspace.centerOnBlock(blockId);
    }
  }

  // Update line info
  var lineInfo = document.getElementById('debug-line-info');
  if (lineInfo) {
    lineInfo.textContent = state.line ? 'Line ' + state.line : '';
  }

  // Update variables panel
  var varsEl = document.getElementById('debug-variables');
  if (varsEl) {
    varsEl.innerHTML = '';
    var variables = state.variables || {};
    var names = Object.keys(variables).sort();
    if (names.length === 0) {
      varsEl.innerHTML = '<div style="color:#999;padding:4px;">No variables yet</div>';
    } else {
      for (var i = 0; i < names.length; i++) {
        var name = names[i];
        var info = variables[name];
        var row = document.createElement('div');
        row.className = 'debug-var-row';
        row.innerHTML =
          '<span class="debug-var-name">' + _escapeHtml(name) + '</span>' +
          '<span class="debug-var-value">' + _escapeHtml(info.value) + '</span>' +
          '<span class="debug-var-type">' + _escapeHtml(info.type) + '</span>';
        varsEl.appendChild(row);
      }
    }
  }

  // Update call stack
  var stackEl = document.getElementById('debug-callstack');
  if (stackEl) {
    stackEl.innerHTML = '';
    var stack = state.call_stack || [];
    if (stack.length > 0) {
      for (var s = 0; s < stack.length; s++) {
        var frame = stack[s];
        var frameEl = document.createElement('div');
        frameEl.className = 'callstack-frame' + (s === 0 ? ' current' : '');
        var funcName = frame.function === '<module>' ? '<module>' : frame.function + '()';
        frameEl.textContent = (s === 0 ? '\u25B6 ' : '  ') + 'line ' + frame.line + ' in ' + funcName;
        stackEl.appendChild(frameEl);
      }
    }
  }

  // Append any new stdout
  if (state.stdout) {
    appendOutput(state.stdout, 'stdout');
  }

  // Show errors
  if (state.error) {
    appendOutput('Error: ' + state.error, 'error');
    if (state.traceback) {
      appendOutput(state.traceback, 'stderr');
    }
  }
}

/**
 * Show/hide debug mode UI elements.
 */
function _setDebugMode(active) {
  var debugBtns = document.querySelectorAll('.debug-btn');
  var debugPanel = document.getElementById('debug-panel');
  var runBtn = document.getElementById('runBtn');
  var debugBtn = document.getElementById('debugBtn');
  var blocklyDiv = document.getElementById('blocklyDiv');

  for (var i = 0; i < debugBtns.length; i++) {
    if (active) {
      debugBtns[i].classList.add('visible');
    } else {
      debugBtns[i].classList.remove('visible');
    }
  }

  if (debugPanel) {
    if (active) {
      debugPanel.classList.add('active');
    } else {
      debugPanel.classList.remove('active');
    }
  }

  // Gray out workspace and disable editing during debug
  if (blocklyDiv) {
    if (active) {
      blocklyDiv.classList.add('debug-mode');
      // Block keyboard events (delete, backspace, etc.) on workspace
      blocklyDiv.addEventListener('keydown', _blockKeysDuringDebug, true);
    } else {
      blocklyDiv.classList.remove('debug-mode');
      blocklyDiv.removeEventListener('keydown', _blockKeysDuringDebug, true);
    }
  }

  // Disable Run/Debug buttons during debug, enable when done
  if (runBtn) runBtn.disabled = active;
  if (debugBtn) debugBtn.disabled = active;
}

/**
 * Enable/disable the step/continue/stop buttons.
 */
function _setDebugButtonsEnabled(enabled) {
  var ids = ['stepBtn', 'continueBtn', 'stopDebugBtn'];
  for (var i = 0; i < ids.length; i++) {
    var btn = document.getElementById(ids[i]);
    if (btn) btn.disabled = !enabled;
  }
}

/**
 * End the debug session and clean up.
 */
function _endDebugSession(message) {
  _debugSessionId = null;
  _debugActive = false;
  _debugLineToBlock = {};

  // Clear block highlight
  var workspace = getWorkspace ? getWorkspace() : null;
  if (workspace) {
    _clearDebugActive(workspace);
  }
  _debugHighlightedBlock = null;

  // Re-enable debug buttons before hiding them
  _setDebugButtonsEnabled(true);
  _setDebugMode(false);

  if (message) {
    appendOutput(message, 'result');
  }
}

/**
 * Add 'debug-active' class to a block's SVG and all its direct value-input blocks.
 * This highlights only the statement block and its attached value inputs,
 * NOT the next-connection blocks stacked below it.
 */
function _applyDebugActive(workspace, blockId) {
  var block = workspace.getBlockById(blockId);
  if (!block) return;

  var svg = block.getSvgRoot();
  if (svg) svg.classList.add('debug-active');

  // Also mark each value-input child block (and their nested value inputs recursively)
  var inputs = block.inputList || [];
  for (var i = 0; i < inputs.length; i++) {
    var input = inputs[i];
    // Only value and dummy inputs, skip statement inputs (which are nested stacks)
    if (input.connection && input.type !== 3) {
      var childBlock = input.connection.targetBlock();
      if (childBlock) {
        _markBlockTree(childBlock);
      }
    }
  }
}

/**
 * Recursively mark a block and all its value-input children with 'debug-active'.
 * This walks into nested value blocks (e.g. math_number inside math_arithmetic).
 */
function _markBlockTree(block) {
  if (!block) return;
  var svg = block.getSvgRoot();
  if (svg) svg.classList.add('debug-active');

  var inputs = block.inputList || [];
  for (var i = 0; i < inputs.length; i++) {
    var input = inputs[i];
    if (input.connection && input.type !== 3) {
      var child = input.connection.targetBlock();
      if (child) _markBlockTree(child);
    }
  }
}

/**
 * Remove 'debug-active' class from all blocks in the workspace.
 */
function _clearDebugActive(workspace) {
  var svgEl = workspace.getParentSvg();
  if (!svgEl) return;
  var actives = svgEl.querySelectorAll('.debug-active');
  for (var i = 0; i < actives.length; i++) {
    actives[i].classList.remove('debug-active');
  }
}

/**
 * Block keyboard events on the workspace during debug mode.
 */
function _blockKeysDuringDebug(e) {
  e.stopPropagation();
  e.preventDefault();
}

/**
 * Escape HTML entities for safe display.
 */
function _escapeHtml(str) {
  var div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}


