/**
 * Main Entry Point for Blockly Application
 * Initializes all modules and sets up the workspace.
 */

// Initialize Blockly when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  initCustomBlocks();
  initPythonGenerator();
  initBlockly();
  setupCustomPrompts();
});

/**
 * Initialize the Blockly workspace with toolbox and event listeners.
 */
function initBlockly() {
  const toolbox = getToolboxConfig();

  // Inject Blockly
  const workspace = Blockly.inject('blocklyDiv', {
    toolbox: toolbox,
    grid: {
      spacing: 20,
      length: 3,
      colour: '#ccc',
      snap: true,
    },
    trashcan: true,
    zoom: {
      controls: true,
      wheel: true,
      startScale: 1.0,
      maxScale: 3,
      minScale: 0.3,
      scaleSpeed: 1.2,
    },
  });

  // Store workspace reference
  setWorkspace(workspace);

  // Store initial toolbox structure
  workspace.initialToolbox = JSON.parse(JSON.stringify(toolbox));

  // Update code preview on block change
  workspace.addChangeListener(updateCodePreview);

  // Listen for block creation and changes to trigger library loading
  workspace.addChangeListener((event) => {
    // Sync toolbox for import blocks
    if (event.type === Blockly.Events.BLOCK_CREATE ||
        event.type === Blockly.Events.BLOCK_DELETE ||
        (event.type === Blockly.Events.BLOCK_CHANGE && event.name === 'MODULE_NAME')) {
      syncToolboxWithImports();
    }

    // Update function info for call blocks
    if (event.type === Blockly.Events.BLOCK_CREATE) {
      const block = workspace.getBlockById(event.blockId);
      if (block && (block.type === 'function_call' || block.type === 'library_function_call')) {
        const funcName = block.getFieldValue('FUNC_NAME');
        if (funcName && funcName !== '...') {
          block.updateFunctionInfo(funcName);
        }
      } else if (block && block.type === 'instance_function_call') {
        updateInstanceMethodsForBlock(block);
      }
    } else if (event.type === Blockly.Events.BLOCK_CHANGE && event.name === 'FUNC_NAME') {
      const block = workspace.getBlockById(event.blockId);
      if (block && (block.type === 'function_call' || block.type === 'library_function_call')) {
        block.updateFunctionInfo(event.newValue);
      }
    } else if (event.type === Blockly.Events.BLOCK_CHANGE && event.name === 'INSTANCE') {
      const block = workspace.getBlockById(event.blockId);
      if (block && block.type === 'instance_function_call') {
        updateInstanceMethodsForBlock(block);
      }
    } else if (event.type === Blockly.Events.BLOCK_CHANGE && event.name === 'METHOD') {
      const block = workspace.getBlockById(event.blockId);
      if (block && block.type === 'instance_function_call') {
        const methodName = block.getFieldValue('METHOD');
        if (methodName && methodName !== '...') {
          block.updateFunctionInfo(methodName);
        }
      }
    }
  });
}
