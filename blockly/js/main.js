/**
 * Main Entry Point for Blockly Application
 * Initializes all modules and sets up the workspace.
 *
 * Flow:
 *   1. Show workspace selection dialog
 *   2. Set the chosen workspace as current
 *   3. Initialize Blockly and all modules
 *   4. Load saved blocks from the workspace folder
 *   5. Set up Ctrl+S save shortcut
 */

document.addEventListener('DOMContentLoaded', async () => {
  // Init blocks & generators first (no workspace needed)
  initCustomBlocks();
  initPythonGenerator();
  setupCustomPrompts();

  // Show workspace picker and wait for selection
  var wsPath = await showWorkspaceDialog();
  setCurrentWorkspace(wsPath);

  // Now inject Blockly
  initBlockly();

  // Load blocks from the workspace folder
  loadWorkspaceBlocks();

  // Init saved functions panel
  initSavedFunctions();

  // Ctrl+S / Cmd+S to save
  document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      saveWorkspaceBlocks();
    }
  });
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

  // ── Dynamic *args / **kwargs slot management ──
  // On any connect or disconnect, immediately cleanup trailing empties and
  // ensure each dynamic param has exactly one trailing empty slot.
  workspace.addChangeListener((event) => {
    if (event.type !== Blockly.Events.BLOCK_MOVE) return;

    // Handle connect
    if (event.newParentId) {
      const parent = workspace.getBlockById(event.newParentId);
      if (parent && parent.functionInfo_) {
        updateDynamicSlots(parent);
      }
    }

    // Handle disconnect
    if (event.oldParentId) {
      const parent = workspace.getBlockById(event.oldParentId);
      if (parent && !parent.isDisposed() && parent.functionInfo_) {
        updateDynamicSlots(parent);
      }
    }
  });

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
    } else if (event.type === Blockly.Events.BLOCK_CHANGE && event.name === 'INSTANCE_NAME') {
      // local_instance_call: when user changes the local-var dropdown, fetch methods
      const block = workspace.getBlockById(event.blockId);
      if (block && block.type === 'local_instance_call' && block.updateMethodList) {
        block.updateMethodList();
      }
    } else if (event.type === Blockly.Events.BLOCK_CHANGE && event.name === 'METHOD_NAME') {
      // local_instance_call: when user picks a method, fetch its signature
      const block = workspace.getBlockById(event.blockId);
      if (block && block.type === 'local_instance_call') {
        const methodName = block.getFieldValue('METHOD_NAME');
        if (methodName && methodName !== '...' && block.updateFunctionInfo) {
          block.updateFunctionInfo(methodName);
        }
      }
    }

    // Also trigger method list fetch when a local_instance_call block is created
    if (event.type === Blockly.Events.BLOCK_CREATE) {
      const block = workspace.getBlockById(event.blockId);
      if (block && block.type === 'local_instance_call' && block.updateMethodList) {
        setTimeout(() => block.updateMethodList(), 100);
      }
    }
  });
}
