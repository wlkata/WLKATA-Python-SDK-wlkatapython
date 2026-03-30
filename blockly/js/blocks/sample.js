/**
 * Local Variables Icon for Procedure Blocks
 * Adds an icon to procedure definition blocks that allows access to local variables.
 */

(function() {
  'use strict';

  // Only run if Blockly is available
  if (typeof Blockly === 'undefined') {
    console.warn('Blockly not available, skipping LocalVariablesIcon');
    return;
  }

  // Create the icon class extending Blockly.icons.Icon
  class LocalVariablesIcon extends Blockly.icons.Icon {
    /**
     * @param {!Blockly.Block} block The block this icon is attached to.
     */
    constructor(block) {
      super(block);
      this.tooltip = 'Click to see local variables for this function';
    }

    /**
     * @override
     */
    getType() {
      return LocalVariablesIcon.TYPE;
    }

    /**
     * @override
     */
    initView(pointerdownListener) {
      // Call parent's initView first to set up svgRoot and event handling
      super.initView(pointerdownListener);

      // Now add our custom content to the svgRoot created by parent
      if (!this.svgRoot) return;

      // Clear any existing content
      while (this.svgRoot.firstChild) {
        this.svgRoot.removeChild(this.svgRoot.firstChild);
      }

      // Ensure the svgRoot is visible
      this.svgRoot.setAttribute('style', 'display: inline;');

      // Simple circular background for the icon
      const circle = Blockly.utils.dom.createSvgElement(
        Blockly.utils.Svg.CIRCLE, {
          'cx': '10',
          'cy': '10',
          'r': '9',
          'fill': '#4CAF50',
          'stroke': '#2E7D32',
          'stroke-width': '1',
        },
        this.svgRoot
      );

      // Text "V" for Variables
      const text = Blockly.utils.dom.createSvgElement(
        Blockly.utils.Svg.TEXT, {
          'x': '10',
          'y': '14',
          'text-anchor': 'middle',
          'font-size': '12',
          'font-weight': 'bold',
          'fill': '#fff',
        },
        this.svgRoot
      );
      text.textContent = 'V';
    }

    /**
     * @override
     */
    getSize() {
      return new Blockly.utils.Size(20, 20);
    }

    /**
     * @override
     */
    getWeight() {
      return 1;
    }

    /**
     * @override
     */
    onClick() {
      this.showLocalVariablesMenu();
    }

    /**
     * Show a context menu with local variables for this function.
     */
    showLocalVariablesMenu() {
      const block = this.getSourceBlock();
      if (!block || block.isInFlyout) return;

      // Get parameters (local variables)
      const params = block.getVars ? block.getVars() : [];
      const paramModels = block.getVarModels ? block.getVarModels() : [];

      // Also collect any variables used in the function body
      const localVars = new Set();

      // Add parameters
      paramModels.forEach(model => {
        if (model) localVars.add(model);
      });

      // Find variables used in the function's statements
      const stackInput = block.getInput('STACK');
      if (stackInput && stackInput.connection && stackInput.connection.targetBlock()) {
        const collectVars = (b) => {
          if (b.getVars) {
            b.getVars().forEach(v => {
              // Only add if it's not a parameter (those are already added)
              const model = block.workspace.getVariableMap().getVariable(v, '');
              if (model && !params.includes(v)) {
                localVars.add(model);
              }
            });
          }
          // Recurse into children
          b.getChildren(false).forEach(child => collectVars(child));
        };
        collectVars(stackInput.connection.targetBlock());
      }

      // Build context menu options
      const options = [];

      // Add parameter variables
      if (paramModels.length > 0) {
        options.push({
          text: 'Parameters:',
          enabled: false,
        });
        paramModels.forEach(model => {
          if (model) {
            options.push({
              text: '  ' + model.getName(),
              enabled: true,
              callback: () => {
                // Create a variable get block for this local variable
                const workspace = block.workspace;
                const xml = Blockly.utils.xml.createElement('block');
                xml.setAttribute('type', 'variables_get');
                const field = Blockly.utils.xml.createElement('field');
                field.setAttribute('name', 'VAR');
                field.setAttribute('id', model.getId());
                field.setAttribute('variabletype', model.getType());
                field.textContent = model.getName();
                xml.appendChild(field);
                
                const newBlock = Blockly.Xml.domToBlock(xml, workspace);
                // Position near the function block
                const xy = block.getRelativeToSurfaceXY();
                newBlock.moveBy(xy.x + 100, xy.y + 50);
                newBlock.outputConnection.bumpNeighbours();
              },
            });
          }
        });
      }

      // Add other local variables
      if (localVars.size > paramModels.length) {
        options.push({
          text: 'Local Variables:',
          enabled: false,
        });
        localVars.forEach(model => {
          if (model && !paramModels.includes(model)) {
            options.push({
              text: '  ' + model.getName(),
              enabled: true,
              callback: () => {
                const workspace = block.workspace;
                const xml = Blockly.utils.xml.createElement('block');
                xml.setAttribute('type', 'variables_get');
                const field = Blockly.utils.xml.createElement('field');
                field.setAttribute('name', 'VAR');
                field.setAttribute('id', model.getId());
                field.setAttribute('variabletype', model.getType());
                field.textContent = model.getName();
                xml.appendChild(field);
                
                const newBlock = Blockly.Xml.domToBlock(xml, workspace);
                const xy = block.getRelativeToSurfaceXY();
                newBlock.moveBy(xy.x + 100, xy.y + 50);
                newBlock.outputConnection.bumpNeighbours();
              },
            });
          }
        });
      }

      if (options.length <= 1) {
        options.push({
          text: 'No local variables yet',
          enabled: false,
        });
        options.push({
          text: 'Add variables to the function body to use them here',
          enabled: false,
        });
      }

      // Show context menu
      Blockly.ContextMenu.show(event, options, block.RTL);
    }

    /**
     * @override
     */
    dispose() {
      // Safely dispose - only call super if svgRoot exists
      // The base Icon.dispose() may try to unbind events that were never bound
      if (this.svgRoot) {
        try {
          // Remove event listeners
          if (this.svgRoot.parentNode) {
            this.svgRoot.parentNode.removeChild(this.svgRoot);
          }
        } catch (e) {
          // Ignore errors during disposal
        }
        this.svgRoot = null;
      }
      // Don't call super.dispose() as it may cause issues with unbinding
      // that wasn't properly set up
    }

    /**
     * @override
     */
    applyColour() {
      // Color is already set in initView, no dynamic color changes needed
    }

    /**
     * @override
     */
    hideForInsertionMarker() {
      // Hide the icon when block is an insertion marker
      if (this.svgRoot) {
        this.svgRoot.style.display = 'none';
      }
    }

    /**
     * @override
     */
    updateEditable() {
      // Icon is always interactive, no changes needed
    }

    /**
     * @override
     */
    updateCollapsed() {
      // Hide when block is collapsed
      if (this.svgRoot) {
        const block = this.getSourceBlock();
        if (block && block.isCollapsed()) {
          this.svgRoot.style.display = 'none';
        } else {
          this.svgRoot.style.display = '';
        }
      }
    }

    /**
     * @override
     */
    isShownWhenCollapsed() {
      return false;
    }

    /**
     * @override
     */
    setOffsetInBlock(offset) {
      // Store offset for positioning - base class may handle this
      this.offsetInBlock = offset;
      if (this.svgRoot) {
        this.svgRoot.setAttribute('transform', `translate(${offset.x}, ${offset.y})`);
      }
    }

    /**
     * @override
     */
    onLocationChange(blockOrigin) {
      // Update position when block moves
      // The base class typically handles this
    }
  }

  // Static type for the icon
  LocalVariablesIcon.TYPE = new Blockly.icons.IconType('local_variables');

  // Export globally
  window.LocalVariablesIcon = LocalVariablesIcon;

  // Register the icon type
  Blockly.icons.registry.register(LocalVariablesIcon.TYPE, LocalVariablesIcon);

  console.log('LocalVariablesIcon registered');

  /**
   * Add local variables icon to a procedure block.
   * @param {!Blockly.Block} block The block to add the icon to.
   */
  function addIconToBlock(block) {
    if (!block || block.isInFlyout) return;
    if (block.type !== 'procedures_defnoreturn' && block.type !== 'procedures_defreturn') return;
    if (block.getIcon(LocalVariablesIcon.TYPE)) return; // Already has icon
    
    try {
      const icon = new LocalVariablesIcon(block);
      block.addIcon(icon);
      console.log('Added LocalVariablesIcon to block:', block.id);
    } catch (e) {
      console.warn('Could not add LocalVariablesIcon:', e);
    }
  }

  /**
   * Set up workspace listener to add icons to procedure blocks.
   * This should be called after the workspace is created.
   */
  function setupProcedureIconListener() {
    if (typeof getWorkspace !== 'function') {
      console.warn('getWorkspace not available, will retry...');
      setTimeout(setupProcedureIconListener, 500);
      return;
    }
    
    const workspace = getWorkspace();
    if (!workspace) {
      console.warn('Workspace not available, will retry...');
      setTimeout(setupProcedureIconListener, 500);
      return;
    }

    // Add icons to existing procedure blocks
    workspace.getAllBlocks(false).forEach(block => {
      addIconToBlock(block);
    });

    // Listen for new blocks
    workspace.addChangeListener((event) => {
      if (event.type === Blockly.Events.BLOCK_CREATE) {
        const block = workspace.getBlockById(event.blockId);
        if (block) {
          // Small delay to ensure block is fully initialized
          setTimeout(() => addIconToBlock(block), 10);
        }
      }
    });

    console.log('Procedure icon listener set up');
  }

  // Set up listener when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      // Wait for Blockly and workspace to be ready
      setTimeout(setupProcedureIconListener, 500);
    });
  } else {
    setTimeout(setupProcedureIconListener, 500);
  }

  /**
   * Override Blockly.Variables.flyoutCategory to hide function parameters
   * AND local variables (variables used inside functions) from the variables tab.
   * These are function-local and shouldn't clutter the global variables list.
   */
  function overrideVariableFlyout() {
    if (!Blockly.Variables || !Blockly.Variables.flyoutCategory) {
      console.warn('Blockly.Variables.flyoutCategory not available, will retry...');
      setTimeout(overrideVariableFlyout, 500);
      return;
    }

    // Store original flyoutCategory
    const originalFlyoutCategory = Blockly.Variables.flyoutCategory;

    /**
     * Get all variable IDs that are local to functions (parameters + local vars).
     */
    function getLocalVariableIds(workspace) {
      const localVarIds = new Set();
      const blocks = workspace.getAllBlocks(false);

      for (const block of blocks) {
        if (block.type === 'procedures_defnoreturn' || block.type === 'procedures_defreturn') {
          // Parameters
          const varModels = block.getVarModels ? block.getVarModels() : [];
          varModels.forEach(model => {
            if (model) localVarIds.add(model.getId());
          });

          // Variables used inside the function body
          const stackInput = block.getInput('STACK');
          if (stackInput && stackInput.connection && stackInput.connection.targetBlock()) {
            const collectVars = (b) => {
              if (b.getVarModels) {
                b.getVarModels().forEach(m => {
                  if (m) localVarIds.add(m.getId());
                });
              }
              b.getChildren(false).forEach(child => collectVars(child));
            };
            collectVars(stackInput.connection.targetBlock());
          }
        }
      }
      return localVarIds;
    }

    // Override to filter out local variables
    Blockly.Variables.flyoutCategory = function(workspace, useXml) {
      const localVarIds = getLocalVariableIds(workspace);

      // Call original to get all variable items
      const items = originalFlyoutCategory.call(Blockly.Variables, workspace, useXml);

      // If useXml is true, items are DOM Elements; filter them
      if (useXml === true) {
        const filtered = [];
        for (const item of items) {
          // Check if this item is a block with a variable that is local
          if (item.nodeName === 'block' || (item.nodeName && item.nodeName.toLowerCase() === 'block')) {
            const field = item.querySelector && item.querySelector('field[name="VAR"]');
            if (field) {
              const varId = field.getAttribute('id');
              if (varId && localVarIds.has(varId)) {
                continue; // Skip local variables
              }
            }
          }
          // Also filter flyout buttons/items that reference local variables
          if (item.nodeName === 'button' || item.nodeName === 'label') {
            // Keep buttons and labels
          }
          filtered.push(item);
        }
        return filtered;
      }

      // If useXml is false, items are FlyoutItemInfo objects
      if (Array.isArray(items)) {
        return items.filter(item => {
          if (item.kind === 'block' && item.type === 'variables_get') {
            const varId = item.fields && item.fields.VAR && item.fields.VAR.id;
            if (varId && localVarIds.has(varId)) {
              return false; // Skip local variables
            }
          }
          return true;
        });
      }

      return items;
    };

    console.log('Overrode Blockly.Variables.flyoutCategory to hide function parameters and local variables');
  }

  /**
   * Robustly override Blockly.Variables.flyoutCategory when Blockly is ready.
   * Uses workspace change listener to re-apply override when workspace loads.
   */
  let variableFlyoutOverrideApplied = false;

  function applyVariableFlyoutOverride() {
    if (variableFlyoutOverrideApplied) return;

    // Check if Blockly.Variables is available
    if (typeof Blockly === 'undefined' || !Blockly.Variables || !Blockly.Variables.flyoutCategory) {
      console.log('[LocalVars] Blockly.Variables not ready, will retry...');
      return false;
    }

    // Check if workspace is ready
    let workspace = null;
    if (typeof getWorkspace === 'function') {
      workspace = getWorkspace();
    }
    if (!workspace) {
      console.log('[LocalVars] Workspace not ready, will retry...');
      return false;
    }

    // Store original if not already stored
    if (!Blockly.Variables._originalFlyoutCategory) {
      Blockly.Variables._originalFlyoutCategory = Blockly.Variables.flyoutCategory;
    }
    const originalFlyoutCategory = Blockly.Variables._originalFlyoutCategory;

    /**
     * Get all variable IDs that are local to functions (parameters + local vars).
     */
    function getLocalVariableIds(ws) {
      const localVarIds = new Set();
      const blocks = ws.getAllBlocks(false);

      for (const block of blocks) {
        if (block.type === 'procedures_defnoreturn' || block.type === 'procedures_defreturn') {
          // Parameters
          const varModels = block.getVarModels ? block.getVarModels() : [];
          varModels.forEach(model => {
            if (model) localVarIds.add(model.getId());
          });

          // Variables used inside the function body
          const stackInput = block.getInput('STACK');
          if (stackInput && stackInput.connection && stackInput.connection.targetBlock()) {
            const collectVars = (b) => {
              if (b.getVarModels) {
                b.getVarModels().forEach(m => {
                  if (m) localVarIds.add(m.getId());
                });
              }
              b.getChildren(false).forEach(child => collectVars(child));
            };
            collectVars(stackInput.connection.targetBlock());
          }
        }
      }
      return localVarIds;
    }

    // Override to filter out local variables
    Blockly.Variables.flyoutCategory = function(ws, useXml) {
      const localVarIds = getLocalVariableIds(ws);

      // Call original to get all variable items
      const items = originalFlyoutCategory.call(Blockly.Variables, ws, useXml);

      // If useXml is true, items are DOM Elements; filter them
      if (useXml === true) {
        const filtered = [];
        for (const item of items) {
          if (item.nodeName === 'block' || (item.nodeName && item.nodeName.toLowerCase() === 'block')) {
            const field = item.querySelector && item.querySelector('field[name="VAR"]');
            if (field) {
              const varId = field.getAttribute('id');
              if (varId && localVarIds.has(varId)) {
                continue; // Skip local variables
              }
            }
          }
          filtered.push(item);
        }
        return filtered;
      }

      // If useXml is false, items are FlyoutItemInfo objects
      if (Array.isArray(items)) {
        return items.filter(item => {
          if (item.kind === 'block' && item.type === 'variables_get') {
            const varId = item.fields && item.fields.VAR && item.fields.VAR.id;
            if (varId && localVarIds.has(varId)) {
              return false; // Skip local variables
            }
          }
          return true;
        });
      }

      return items;
    };

    variableFlyoutOverrideApplied = true;
    console.log('[LocalVars] Overrode Blockly.Variables.flyoutCategory to hide function parameters and local variables');
    return true;
  }

  /**
   * Set up robust loading detection for the flyout override.
   */
  function setupFlyoutOverrideWithLoadingDetection() {
    // Try immediately
    if (applyVariableFlyoutOverride()) {
      return;
    }

    // Try with increasing delays
    const delays = [100, 250, 500, 1000, 2000, 3000, 5000];
    let delayIndex = 0;

    function tryAgain() {
      if (applyVariableFlyoutOverride()) {
        return;
      }
      if (delayIndex < delays.length) {
        setTimeout(tryAgain, delays[delayIndex]);
        delayIndex++;
      } else {
        // Keep trying every 5 seconds
        setTimeout(tryAgain, 5000);
      }
    }

    // Start trying
    setTimeout(tryAgain, 100);
  }

  // Also listen for workspace events that might indicate loading is done
  if (typeof Blockly !== 'undefined' && Blockly.Events) {
    // Add a global change listener that will trigger re-application
    // when blocks are created (indicating workspace is active)
    const checkAndApply = function(event) {
      if (!variableFlyoutOverrideApplied && event.type === Blockly.Events.BLOCK_CREATE) {
        applyVariableFlyoutOverride();
      }
    };
    // Store for potential cleanup
    window._localVarsFlyoutCheck = checkAndApply;
  }

  // Start the loading detection
  setupFlyoutOverrideWithLoadingDetection();

  /**
   * Add default value inputs to procedure blocks for parameter defaults.
   * This allows users to set initial values for function parameters.
   */
  function addDefaultInputsToProcedureBlock(block) {
    if (!block || (block.type !== 'procedures_defnoreturn' && block.type !== 'procedures_defreturn')) {
      return;
    }

    const params = block.getVars ? block.getVars() : [];
    if (!params || params.length === 0) return;

    // For each parameter (names from getVars), add a DEFAULT_<name> input
    for (const paramName of params) {
      const inputName = 'DEFAULT_' + paramName;
      
      // Check if input already exists
      if (block.getInput(inputName)) continue;

      // Add a value input for the default value
      try {
        const input = block.appendValueInput(inputName)
          .setAlign(Blockly.ALIGN_RIGHT)
          .appendField('default ' + paramName + ':');
        
        console.log('[LocalVars] Added default input for parameter:', paramName);
      } catch (e) {
        console.warn('[LocalVars] Could not add default input for', paramName, ':', e);
      }
    }
  }

  /**
   * Set up listener to add default inputs to procedure blocks.
   */
  function setupDefaultInputsListener() {
    if (typeof getWorkspace !== 'function') {
      setTimeout(setupDefaultInputsListener, 500);
      return;
    }

    const workspace = getWorkspace();
    if (!workspace) {
      setTimeout(setupDefaultInputsListener, 500);
      return;
    }

    // Add default inputs to existing procedure blocks
    workspace.getAllBlocks(false).forEach(block => {
      addDefaultInputsToProcedureBlock(block);
    });

    // Listen for new blocks
    workspace.addChangeListener((event) => {
      if (event.type === Blockly.Events.BLOCK_CREATE) {
        const block = workspace.getBlockById(event.blockId);
        if (block) {
          setTimeout(() => addDefaultInputsToProcedureBlock(block), 50);
        }
      } else if (event.type === Blockly.Events.BLOCK_CHANGE && event.name === 'params') {
        // Parameters changed, re-add default inputs
        const block = workspace.getBlockById(event.blockId);
        if (block) {
          setTimeout(() => addDefaultInputsToProcedureBlock(block), 50);
        }
      }
    });

    console.log('[LocalVars] Set up default parameter inputs listener');
  }

  // Set up default inputs listener
  setTimeout(setupDefaultInputsListener, 1000);
})();
