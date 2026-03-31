/**
 * Instance Methods Module
 * Handles inspection and updating of instance method information.
 */

/**
 * Preprocess generated Python code for instance inspection.
 *
 * When a variable is assigned from a user-defined function that creates and
 * returns an instance (e.g. `asd = do_something()` where `do_something`
 * creates a Mirobot_UART and returns it), the server's exec() may fail
 * because the constructor tries to open hardware.  We flatten the function
 * body so the server sees a direct assignment instead.
 *
 * Example input:
 *   def do_something():
 *     a = wlkatapython.Mirobot_UART()
 *     a.homing()
 *     return a
 *   asd = do_something()
 *
 * Example output:
 *   import wlkatapython
 *   asd = wlkatapython.Mirobot_UART()
 *
 * @param {string} code - The full generated Python code
 * @param {string} instanceName - The variable name to inspect
 * @returns {string} Preprocessed code suitable for exec()
 */
function preprocessCodeForInspection(code, instanceName) {
  const lines = code.split('\n');

  // Phase 1: Find what function (if any) is assigned to instanceName
  // e.g. "asd = do_something()" -> funcName = "do_something"
  let assignedFunc = null;
  for (const line of lines) {
    const trimmed = line.trim();
    const escaped = instanceName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const assignMatch = trimmed.match(new RegExp('^' + escaped + '\\s*=\\s*(\\w+)\\s*\\('));
    if (assignMatch) {
      assignedFunc = assignMatch[1];
      break;
    }
  }

  // If no function call assignment found, or it's a known constructor, return as-is
  if (!assignedFunc) {
    console.log('[preprocessCodeForInspection] No function-return assignment found for "' + instanceName + '", using raw code');
    return code;
  }
  console.log('[preprocessCodeForInspection] Found "' + instanceName + ' = ' + assignedFunc + '()", flattening...');

  // Phase 2: Find the function definition and extract its body
  let inFunc = false;
  let funcIndent = 0;
  let bodyLines = [];
  let internalVar = null;  // the variable that gets the instance inside the function
  let returnsVar = null;   // what the function returns

  for (const line of lines) {
    const trimmed = line.trim();

    if (!inFunc) {
      const defMatch = trimmed.match(new RegExp('^def\\s+' + assignedFunc.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\s*\\('));
      if (defMatch) {
        inFunc = true;
        funcIndent = line.search(/\S/);
      }
      continue;
    }

    // Inside the function
    const lineIndent = line.search(/\S/);
    if (trimmed.length > 0 && lineIndent <= funcIndent) {
      break; // left the function
    }

    // Track the return statement
    const retMatch = trimmed.match(/^return\s+(\w+)/);
    if (retMatch) {
      returnsVar = retMatch[1];
      continue; // don't include return in body
    }

    // Skip global declarations
    if (trimmed.startsWith('global ')) continue;

    // Track instance creation
    const createMatch = trimmed.match(/^(\w+)\s*=\s*\w+\.\w+\s*\(/);
    if (createMatch) {
      internalVar = createMatch[1];
      // Only keep the creation line — method calls on the instance
      // (e.g. a.homing()) can crash exec() and aren't needed for inspection
      bodyLines.push(trimmed);
      continue;
    }

    // Skip method calls inside the function body (a.homing(), a.gripper(), etc.)
    // For inspection we only need the instance creation, not its usage
    if (/^\w+\.\w+\s*\(/.test(trimmed)) continue;

    bodyLines.push(trimmed);
  }

  // If the function doesn't return a tracked variable, can't flatten
  if (!returnsVar || !internalVar) {
    console.log('[preprocessCodeForInspection] Cannot flatten: returnsVar=' + returnsVar + ', internalVar=' + internalVar);
    return code;
  }

  // Phase 3: Build flattened code
  // First, collect all user-defined function names (their defs will be stripped)
  const strippedFuncNames = new Set();
  {
    let sf = false, si = 0;
    for (const l of lines) {
      const t = l.trim();
      if (sf) {
        const li = l.search(/\S/);
        if (t.length > 0 && li <= si) sf = false; else continue;
      }
      const dm = t.match(/^def\s+(\w+)\s*\(/);
      if (dm) { strippedFuncNames.add(dm[1]); sf = true; si = l.search(/\S/); }
    }
  }

  // Now collect top-level lines, skipping:
  //   - function definitions and their bodies
  //   - any line that calls a stripped function (e.g. asd = do_something())
  //   - varName = None declarations
  //   - comments
  const topLines = [];
  let skipFunc = false;
  let skipFuncIndent = 0;

  for (const line of lines) {
    const trimmed = line.trim();

    if (skipFunc) {
      const lineIndent = line.search(/\S/);
      if (trimmed.length > 0 && lineIndent <= skipFuncIndent) {
        skipFunc = false;
      } else {
        continue;
      }
    }

    if (trimmed.match(/^def\s+\w+\s*\(/)) {
      skipFunc = true;
      skipFuncIndent = line.search(/\S/);
      continue;
    }

    // Skip comments
    if (trimmed.startsWith('#')) continue;

    // Skip "varName = None" declarations
    if (/^\w+\s*=\s*None\s*$/.test(trimmed)) continue;

    // Skip any line that calls a stripped user-defined function
    let callsStripped = false;
    for (const fn of strippedFuncNames) {
      const esc = fn.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      if (new RegExp('(^|=\\s*)' + esc + '\\s*\\(').test(trimmed)) {
        callsStripped = true;
        break;
      }
    }
    if (callsStripped) continue;

    // Skip method calls on any variable (e.g. ad.cancellation())
    // These can crash exec() if the method tries to use hardware.
    // For inspection we only need imports and instance creation lines.
    if (/^\w+\.\w+\s*\(/.test(trimmed)) continue;

    if (trimmed.length > 0) {
      topLines.push(line);
    }
  }

  // Replace internal variable name with the instance name in body lines
  const renamedBody = bodyLines.map(function(bline) {
    // Replace occurrences of internalVar with instanceName
    // Use word boundary replacement
    const re = new RegExp('\\b' + internalVar.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b', 'g');
    return bline.replace(re, instanceName);
  });

  const result = topLines.join('\n') + '\n' + renamedBody.join('\n');
  console.log('[preprocessCodeForInspection] Flattened code for "' + instanceName + '":\n' + result);
  return result;
}

/**
 * Update the method dropdown for an instance_function_call block based on the instance variable.
 * @param {Blockly.Block} block - The instance_function_call block
 */
async function updateInstanceMethodsForBlock(block) {
  if (!block || block.disposed) {
    return;
  }

  const instanceField = block.getField('INSTANCE');
  const instanceModel = instanceField ? instanceField.getVariable() : null;
  const instanceName = instanceModel ? instanceModel.name : block.getFieldValue('INSTANCE');
  if (!instanceName) {
    return;
  }

  // Use a debounce to avoid rapid-fire requests while dragging/typing
  if (block.updateTimer_) {
    clearTimeout(block.updateTimer_);
  }

  block.updateTimer_ = setTimeout(async () => {
    const workspace = getWorkspace ? getWorkspace() : null;
    const serverUrl = getServerUrl ? getServerUrl() : 'http://127.0.0.1:5080';

    if (!workspace) return;

    try {
      const rawCode = Blockly.Python.workspaceToCode(workspace);
      // Preprocess: flatten function-return assignments so the server
      // sees a direct instance creation for the variable.
      const code = preprocessCodeForInspection(rawCode, instanceName);

      const response = await fetch(`${serverUrl}/inspect-instance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, instance: instanceName })
      });

      const info = await response.json();
      if (info.success) {
        const methods = info.methods || [];

        const currentMethod = block.getFieldValue('METHOD');
        block.updateOptions(methods);

        if (methods.length > 0) {
          if (!currentMethod || currentMethod === '...' || !methods.includes(currentMethod)) {
            block.setFieldValue(methods[0], 'METHOD');
            block.updateFunctionInfo(methods[0]);
          }
        }
      } else {
        console.warn(`Instance inspection failed for ${instanceName}: ${info.error}`);
        block.updateOptions([]);
      }
    } catch (error) {
      console.error('Failed to inspect instance:', error);
    }
  }, 300);
}

/**
 * Fetch and apply method information for an instance method call.
 * @param {Blockly.Block} block - The instance_function_call block
 * @param {string} methodName - The method name to inspect
 */
async function updateInstanceMethodInfo(block, methodName) {
  if (!block || block.disposed || !methodName || methodName === '...') {
    return;
  }

  const instanceField = block.getField('INSTANCE');
  const instanceModel = instanceField ? instanceField.getVariable() : null;
  const instanceName = instanceModel ? instanceModel.name : block.getFieldValue('INSTANCE');
  if (!instanceName) {
    return;
  }

  const cleanMethod = methodName.includes('.') ? methodName.split('.').pop() : methodName;

  const workspace = getWorkspace ? getWorkspace() : null;
  const serverUrl = getServerUrl ? getServerUrl() : 'http://127.0.0.1:5080';

  if (!workspace) return;

  try {
    const rawCode = Blockly.Python.workspaceToCode(workspace);
    const code = preprocessCodeForInspection(rawCode, instanceName);
    const response = await fetch(`${serverUrl}/inspect-instance-method`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, instance: instanceName, method: cleanMethod })
    });

    const info = await response.json();
    if (info.success) {
      block.applyFunctionInfo(info);
      block.functionInfo_ = info;
    } else {
      block.setTooltip(`Error: ${info.error}`);
    }
  } catch (error) {
    console.error('Failed to fetch instance method info:', error);
  }
}
