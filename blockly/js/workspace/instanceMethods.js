/**
 * Instance Methods Module
 * Handles inspection and updating of instance method information.
 */

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
    const serverUrl = getServerUrl ? getServerUrl() : 'http://127.0.0.1:5000';

    if (!workspace) return;

    try {
      const code = Blockly.Python.workspaceToCode(workspace);

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
  const serverUrl = getServerUrl ? getServerUrl() : 'http://127.0.0.1:5000';

  if (!workspace) return;

  try {
    const code = Blockly.Python.workspaceToCode(workspace);
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
