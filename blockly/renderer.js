// Blockly workspace
let workspace;

// Server URL - use 127.0.0.1 to avoid DNS resolution issues
const SERVER_URL = 'http://127.0.0.1:5000';

// Cache for function signatures to avoid repeated API calls
const functionCache = new Map();

// Track imported modules to avoid duplicates in toolbox
const importedModules = new Set();

// Initialize Blockly when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  initCustomBlocks();
  initPythonGenerator();
  initBlockly();
  setupCustomPrompts();
});

// Initialize custom blocks
function initCustomBlocks() {
  // Define the import module block
  Blockly.Blocks['import_module'] = {
    init: function() {
      const block = this;
      const validator = function(newValue) {
        if (block.importTimeout_) {
          clearTimeout(block.importTimeout_);
        }
        block.importTimeout_ = setTimeout(() => {
          syncToolboxWithImports();
        }, 500);
        return newValue;
      };

      this.appendDummyInput()
          .appendField("import")
          .appendField(new Blockly.FieldTextInput("math", validator), "MODULE_NAME");
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setColour(230);
      this.setTooltip("Import a Python library and add its functions to the toolbox.");
      this.setHelpUrl("");
    }
  };

  // Define the dynamic function call block
  Blockly.Blocks['function_call'] = {
    init: function() {
      // Store reference to the block for use in validator
      const block = this;

      // Create validator function that has access to the block
      const validator = function(newValue) {
        // Debounce the API call
        if (block.validateTimeout_) {
          clearTimeout(block.validateTimeout_);
        }

        block.validateTimeout_ = setTimeout(() => {
          block.updateFunctionInfo(newValue);
        }, 300);

        return newValue;
      };

      this.appendDummyInput('FUNCTION_NAME')
          .appendField('call')
          .appendField(new Blockly.FieldTextInput('print', validator), 'FUNC_NAME');

      this.setInputsInline(false);
      this.setOutput(true, null);
      this.setColour(290);
      this.setTooltip('Call a Python function. Enter the function name to see its parameters.');
      this.setHelpUrl('');

      // Store function info
      this.functionInfo_ = null;
      this.isStatement_ = false;
    },

    // Add context menu to toggle between statement and expression
    customContextMenu: function(options) {
      const block = this;
      const option = {
        text: this.isStatement_ ? "Use as Expression" : "Use as Statement",
        enabled: true,
        callback: function() {
          block.setStatementMode(!block.isStatement_);
        }
      };
      options.push(option);
    },

    setStatementMode: function(isStatement) {
      if (this.isStatement_ === isStatement) {
        return;
      }
      this.isStatement_ = isStatement;
      this.updateShape_();
    },

    updateShape_: function() {
      if (this.isStatement_) {
        this.setOutput(false);
        this.setPreviousStatement(true);
        this.setNextStatement(true);
      } else {
        this.setPreviousStatement(false);
        this.setNextStatement(false);
        this.setOutput(true);
      }
    },

    // Fetch function info from server and update block
    updateFunctionInfo: async function(funcName) {
      if (!funcName || funcName.trim() === '' || funcName === '...') {
        return;
      }

      // Check cache first
      if (functionCache.has(funcName)) {
        this.applyFunctionInfo(functionCache.get(funcName));
        return;
      }

      try {
        const response = await fetch(`${SERVER_URL}/inspect`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ function: funcName })
        });

        const info = await response.json();

        if (info.success) {
          functionCache.set(funcName, info);
          this.applyFunctionInfo(info);
        } else {
          // Show error in tooltip
          this.setTooltip(`Error: ${info.error}`);
        }
      } catch (error) {
        console.error('Failed to fetch function info:', error);
        this.setTooltip(`Failed to fetch function info: ${error.message}`);
      }
    },

    // Apply function info to update the block's inputs
    applyFunctionInfo: function(info) {
      this.functionInfo_ = info;

      // Update tooltip with docstring (first 500 chars)
      const docPreview = info.docstring.length > 500
        ? info.docstring.substring(0, 500) + '...'
        : info.docstring;
      this.setTooltip(docPreview);

      // Save current input values before rebuilding
      const oldValues = {};
      if (this.paramInputs_) {
        for (const paramName of this.paramInputs_) {
          const input = this.getInput(`PARAM_${paramName}`);
          if (input && input.connection && input.connection.targetBlock()) {
            oldValues[paramName] = input.connection.targetBlock();
          }
        }
      }

      // Remove all parameter inputs
      const inputNames = this.inputList.map(i => i.name).filter(n => n && n.startsWith('PARAM_'));
      for (const name of inputNames) {
        this.removeInput(name);
      }

      // Create new parameter inputs
      this.paramInputs_ = [];

      for (const param of info.parameters) {
        const paramName = param.name;
        this.paramInputs_.push(paramName);

        // Create input label
        let labelText = paramName;
        if (param.has_default) {
          labelText += ` = ${param.default}`;
        }
        if (param.is_varargs) {
          labelText = '*' + paramName;
        } else if (param.is_varkwargs) {
          labelText = '**' + paramName;
        }

        // Create the input
        const input = this.appendValueInput(`PARAM_${paramName}`)
            .setCheck(null)
            .appendField(labelText);

        // Restore old value if exists
        if (oldValues[paramName]) {
          input.connection.connect(oldValues[paramName].outputConnection);
        }
      }

      // Update the block's shape
      this.render();
    },

    // Save extra state for serialization
    mutationToDom: function() {
      const container = document.createElement('mutation');
      container.setAttribute('func_name', this.getFieldValue('FUNC_NAME'));
      container.setAttribute('is_statement', this.isStatement_);

      if (this.functionInfo_) {
        container.setAttribute('params', JSON.stringify(this.functionInfo_.parameters.map(p => p.name)));
      }

      return container;
    },

    // Load extra state from serialization
    domToMutation: function(xmlElement) {
      const funcName = xmlElement.getAttribute('func_name');
      const isStatement = xmlElement.getAttribute('is_statement') === 'true';
      this.setStatementMode(isStatement);
      if (funcName) {
        // Trigger async update
        this.updateFunctionInfo(funcName);
      }
    },

    saveExtraState: function() {
      return {
        'func_name': this.getFieldValue('FUNC_NAME'),
        'is_statement': this.isStatement_,
        'params': this.functionInfo_ ? this.functionInfo_.parameters.map(p => p.name) : []
      };
    },

    loadExtraState: function(state) {
      if (state.is_statement !== undefined) {
        this.setStatementMode(state.is_statement);
      }
      if (state.func_name) {
        this.updateFunctionInfo(state.func_name);
      }
    }
  };

  // Define the dynamic function call block with dropdown for libraries
  Blockly.Blocks['library_function_call'] = {
    init: function() {
      this.appendDummyInput('FUNCTION_NAME')
          .appendField('call')
          .appendField(new Blockly.FieldDropdown([['...', '...']]), 'FUNC_NAME');

      this.setInputsInline(false);
      this.setOutput(true, null);
      this.setColour(290);
      this.setTooltip('Call a function from the library.');
      this.setHelpUrl('');

      this.functionInfo_ = null;
      this.isStatement_ = false;
    },

    // Re-use logic from function_call
    updateFunctionInfo: Blockly.Blocks['function_call'].updateFunctionInfo,
    applyFunctionInfo: Blockly.Blocks['function_call'].applyFunctionInfo,
    customContextMenu: Blockly.Blocks['function_call'].customContextMenu,
    setStatementMode: Blockly.Blocks['function_call'].setStatementMode,
    updateShape_: Blockly.Blocks['function_call'].updateShape_,

    mutationToDom: function() {
      const container = Blockly.Blocks['function_call'].mutationToDom.call(this);
      const dropdown = this.getField('FUNC_NAME');
      if (dropdown && dropdown.menuGenerator_) {
        const options = dropdown.menuGenerator_.map(opt => opt[1]);
        container.setAttribute('options', JSON.stringify(options));
      }
      return container;
    },
    domToMutation: function(xmlElement) {
      const funcName = xmlElement.getAttribute('func_name');
      const optionsStr = xmlElement.getAttribute('options');
      const isStatement = xmlElement.getAttribute('is_statement') === 'true';
      this.setStatementMode(isStatement);
      if (optionsStr) {
        try {
          const options = JSON.parse(optionsStr);
          this.updateOptions(options);
        } catch (e) {}
      }
      if (funcName) {
        this.setFieldValue(funcName, 'FUNC_NAME');
        this.updateFunctionInfo(funcName);
      }
    },

    saveExtraState: function() {
      const dropdown = this.getField('FUNC_NAME');
      return {
        'func_name': this.getFieldValue('FUNC_NAME'),
        'is_statement': this.isStatement_,
        'options': dropdown && dropdown.menuGenerator_ ? dropdown.menuGenerator_.map(opt => opt[1]) : []
      };
    },
    loadExtraState: function(state) {
      if (state.is_statement !== undefined) {
        this.setStatementMode(state.is_statement);
      }
      if (state.options) {
        this.updateOptions(state.options);
      }
      if (state.func_name) {
        this.setFieldValue(state.func_name, 'FUNC_NAME');
        this.updateFunctionInfo(state.func_name);
      }
    },

    // Update dropdown options
    updateOptions: function(options) {
      const dropdown = this.getField('FUNC_NAME');
      if (dropdown) {
        const menuOptions = options.map(opt => [opt.split('.').pop(), opt]);
        // If no options, add placeholder
        if (menuOptions.length === 0) {
          menuOptions.push(['...', '...']);
        }
        dropdown.menuGenerator_ = menuOptions;

        // Add validator to trigger info update when selected
        dropdown.setValidator((newValue) => {
          this.updateFunctionInfo(newValue);
          return newValue;
        });
      }
    }
  };

  // Define the instance function call block
  Blockly.Blocks['instance_function_call'] = {
    init: function() {
      this.appendDummyInput('INSTANCE')
          .appendField('call')
          .appendField(new Blockly.FieldVariable('item'), 'INSTANCE')
          .appendField('.')
          .appendField(new Blockly.FieldDropdown([['...', '...']]), 'METHOD');

      this.setInputsInline(false);
      this.setOutput(true, null);
      this.setColour(290);
      this.setTooltip('Call a method on an instance.');
      this.setHelpUrl('');

      this.functionInfo_ = null;
      this.isStatement_ = false;
      this.methodOptions_ = [];
    },

    updateFunctionInfo: function(methodName) {
      updateInstanceMethodInfo(this, methodName);
    },
    applyFunctionInfo: Blockly.Blocks['function_call'].applyFunctionInfo,
    customContextMenu: Blockly.Blocks['function_call'].customContextMenu,
    setStatementMode: Blockly.Blocks['function_call'].setStatementMode,
    updateShape_: Blockly.Blocks['function_call'].updateShape_,

    updateOptions: function(options) {
      this.methodOptions_ = options || [];
      const dropdown = this.getField('METHOD');
      if (dropdown) {
        const menuOptions = this.methodOptions_.length
          ? this.methodOptions_.map(opt => [opt, opt])
          : [['...', '...']];
        dropdown.menuGenerator_ = menuOptions;
        dropdown.setValidator((newValue) => {
          if (newValue && newValue !== '...') {
            this.updateFunctionInfo(newValue);
          }
          return newValue;
        });
      }
    },

    mutationToDom: function() {
      const container = Blockly.Blocks['function_call'].mutationToDom.call(this);
      container.setAttribute('method_options', JSON.stringify(this.methodOptions_));
      return container;
    },
    domToMutation: function(xmlElement) {
      const methodOptions = xmlElement.getAttribute('method_options');
      const funcName = xmlElement.getAttribute('func_name');
      const isStatement = xmlElement.getAttribute('is_statement') === 'true';
      this.setStatementMode(isStatement);
      if (methodOptions) {
        try {
          this.updateOptions(JSON.parse(methodOptions));
        } catch (e) {}
      }
      if (funcName) {
        this.setFieldValue(funcName, 'METHOD');
        this.updateFunctionInfo(funcName);
      }
    },

    saveExtraState: function() {
      return {
        'func_name': this.getFieldValue('METHOD'),
        'is_statement': this.isStatement_,
        'method_options': this.methodOptions_
      };
    },
    loadExtraState: function(state) {
      if (state.is_statement !== undefined) {
        this.setStatementMode(state.is_statement);
      }
      if (state.method_options) {
        this.updateOptions(state.method_options);
      }
      if (state.func_name) {
        this.setFieldValue(state.func_name, 'METHOD');
        this.updateFunctionInfo(state.func_name);
      }
    }
  };
}

// Python code generator for the function call block
// Define it as a separate function and register it after Blockly loads
function initPythonGenerator() {
  if (!Blockly.Python) {
    console.error('Blockly.Python not available');
    return;
  }

  // In newer Blockly versions, generators use forBlock namespace
  // In older versions, they're directly on the generator object
  const generatorTarget = Blockly.Python.forBlock || Blockly.Python;

  generatorTarget['import_module'] = function(block) {
    const moduleName = block.getFieldValue('MODULE_NAME');
    return `import ${moduleName}\n`;
  };

  generatorTarget['function_call'] = function(block) {
    const funcName = block.getFieldValue('FUNC_NAME');
    const funcInfo = block.functionInfo_;

    if (!funcInfo || !funcInfo.parameters || funcInfo.parameters.length === 0) {
      // No parameters - just call the function
      return [`${funcName}()`, Blockly.Python.ORDER_FUNCTION_CALL];
    }

    const args = [];

    for (const param of funcInfo.parameters) {
      const inputName = `PARAM_${param.name}`;
      const inputValue = Blockly.Python.valueToCode(block, inputName, Blockly.Python.ORDER_NONE);

      if (inputValue) {
        if (param.is_varargs) {
          // For *args, just pass the value (assuming it's a tuple/list)
          args.push(`*${inputValue}`);
        } else if (param.is_varkwargs) {
          // For **kwargs, just pass the value (assuming it's a dict)
          args.push(`**${inputValue}`);
        } else if (param.is_keyword_only || param.has_default) {
          // Use keyword argument
          args.push(`${param.name}=${inputValue}`);
        } else {
          // Positional argument
          args.push(inputValue);
        }
      } else if (!param.has_default && !param.is_varargs && !param.is_varkwargs) {
        // Required parameter without value - use None as placeholder
        args.push('None');
      }
      // If has default and no value provided, skip it (use default)
    }

    const code = `${funcName}(${args.join(', ')})`;
    if (block.isStatement_) {
      return code + '\n';
    }
    return [code, Blockly.Python.ORDER_FUNCTION_CALL];
  };

  generatorTarget['library_function_call'] = generatorTarget['function_call'];
  generatorTarget['instance_function_call'] = function(block) {
    const instanceField = block.getField('INSTANCE');
    const instanceModel = instanceField ? instanceField.getVariable() : null;
    const instanceName = instanceModel ? instanceModel.name : block.getFieldValue('INSTANCE');
    const rawMethodName = block.getFieldValue('METHOD');
    const methodName = rawMethodName && rawMethodName.includes('.') ? rawMethodName.split('.').pop() : rawMethodName;
    const funcInfo = block.functionInfo_;
    const isStatement = !!(block.previousConnection || block.nextConnection);

    if (!instanceName || !methodName || methodName === '...') {
      return isStatement ? '' : ['None', Blockly.Python.ORDER_ATOMIC];
    }

    const callTarget = `${instanceName}.${methodName}`;

    if (!funcInfo || !funcInfo.parameters || funcInfo.parameters.length === 0) {
      const code = `${callTarget}()`;
      if (isStatement) {
        return code + '\n';
      }
      return [code, Blockly.Python.ORDER_FUNCTION_CALL];
    }

    const args = [];

    for (const param of funcInfo.parameters) {
      const inputName = `PARAM_${param.name}`;
      const inputValue = Blockly.Python.valueToCode(block, inputName, Blockly.Python.ORDER_NONE);

      if (inputValue) {
        if (param.is_varargs) {
          args.push(`*${inputValue}`);
        } else if (param.is_varkwargs) {
          args.push(`**${inputValue}`);
        } else if (param.is_keyword_only || param.has_default) {
          args.push(`${param.name}=${inputValue}`);
        } else {
          args.push(inputValue);
        }
      } else if (!param.has_default && !param.is_varargs && !param.is_varkwargs) {
        args.push('None');
      }
    }

    const code = `${callTarget}(${args.join(', ')})`;
    if (isStatement) {
      return code + '\n';
    }
    return [code, Blockly.Python.ORDER_FUNCTION_CALL];
  };
}

// Override Blockly's prompt with custom implementation for Electron
function setupCustomPrompts() {
  // Override the default prompt function used by Blockly
  Blockly.dialog.setPrompt(function(message, defaultValue, callback) {
    // Create a custom modal dialog
    const modal = document.createElement('div');
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 10000;
    `;

    const dialog = document.createElement('div');
    dialog.style.cssText = `
      background: white;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
      min-width: 300px;
    `;

    const label = document.createElement('label');
    label.textContent = message;
    label.style.cssText = 'display: block; margin-bottom: 10px; font-weight: bold;';

    const input = document.createElement('input');
    input.type = 'text';
    input.value = defaultValue || '';
    input.style.cssText = `
      width: 100%;
      padding: 8px;
      border: 1px solid #ccc;
      border-radius: 4px;
      box-sizing: border-box;
      margin-bottom: 15px;
    `;

    const buttonContainer = document.createElement('div');
    buttonContainer.style.cssText = 'display: flex; justify-content: flex-end; gap: 10px;';

    const cancelBtn = document.createElement('button');
    cancelBtn.textContent = 'Cancel';
    cancelBtn.style.cssText = `
      padding: 8px 16px;
      background: #ccc;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    `;

    const okBtn = document.createElement('button');
    okBtn.textContent = 'OK';
    okBtn.style.cssText = `
      padding: 8px 16px;
      background: #2196F3;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    `;

    cancelBtn.onclick = () => {
      document.body.removeChild(modal);
      callback(null);
    };

    okBtn.onclick = () => {
      document.body.removeChild(modal);
      callback(input.value);
    };

    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        document.body.removeChild(modal);
        callback(input.value);
      }
    });

    buttonContainer.appendChild(cancelBtn);
    buttonContainer.appendChild(okBtn);
    dialog.appendChild(label);
    dialog.appendChild(input);
    dialog.appendChild(buttonContainer);
    modal.appendChild(dialog);
    document.body.appendChild(modal);

    input.focus();
    input.select();
  });

  // Also override confirm for delete operations
  Blockly.dialog.setConfirm(function(message, callback) {
    callback(confirm(message));
  });

  // Override alert
  Blockly.dialog.setAlert(function(message, callback) {
    alert(message);
    callback();
  });
}

function initBlockly() {
  // Define toolbox with basic blocks
  const toolbox = {
    kind: 'categoryToolbox',
    contents: [
      {
        kind: 'category',
        name: 'Logic',
        colour: '#5C81A6',
        contents: [
          { kind: 'block', type: 'controls_if' },
          { kind: 'block', type: 'logic_compare' },
          { kind: 'block', type: 'logic_operation' },
          { kind: 'block', type: 'logic_negate' },
          { kind: 'block', type: 'logic_boolean' },
        ],
      },
      {
        kind: 'category',
        name: 'Loops',
        colour: '#5CA65C',
        contents: [
          { kind: 'block', type: 'controls_repeat_ext' },
          { kind: 'block', type: 'controls_whileUntil' },
          { kind: 'block', type: 'controls_for' },
          { kind: 'block', type: 'controls_forEach' },
          { kind: 'block', type: 'controls_flow_statements' },
        ],
      },
      {
        kind: 'category',
        name: 'Math',
        colour: '#5C68A6',
        contents: [
          { kind: 'block', type: 'math_number' },
          { kind: 'block', type: 'math_arithmetic' },
          { kind: 'block', type: 'math_single' },
          { kind: 'block', type: 'math_trig' },
          { kind: 'block', type: 'math_constant' },
          { kind: 'block', type: 'math_number_property' },
          { kind: 'block', type: 'math_round' },
          { kind: 'block', type: 'math_on_list' },
          { kind: 'block', type: 'math_modulo' },
          { kind: 'block', type: 'math_constrain' },
          { kind: 'block', type: 'math_random_int' },
          { kind: 'block', type: 'math_random_float' },
        ],
      },
      {
        kind: 'category',
        name: 'Text',
        colour: '#A65C81',
        contents: [
          { kind: 'block', type: 'text' },
          { kind: 'block', type: 'text_join' },
          { kind: 'block', type: 'text_append' },
          { kind: 'block', type: 'text_length' },
          { kind: 'block', type: 'text_isEmpty' },
          { kind: 'block', type: 'text_indexOf' },
          { kind: 'block', type: 'text_charAt' },
          { kind: 'block', type: 'text_getSubstring' },
          { kind: 'block', type: 'text_changeCase' },
          { kind: 'block', type: 'text_trim' },
          { kind: 'block', type: 'text_print' },
          { kind: 'block', type: 'text_prompt_ext' },
        ],
      },
      {
        kind: 'category',
        name: 'Lists',
        colour: '#A65C5C',
        contents: [
          { kind: 'block', type: 'lists_create_with' },
          { kind: 'block', type: 'lists_create_with' },
          { kind: 'block', type: 'lists_repeat' },
          { kind: 'block', type: 'lists_length' },
          { kind: 'block', type: 'lists_isEmpty' },
          { kind: 'block', type: 'lists_indexOf' },
          { kind: 'block', type: 'lists_getIndex' },
          { kind: 'block', type: 'lists_setIndex' },
          { kind: 'block', type: 'lists_getSublist' },
          { kind: 'block', type: 'lists_split' },
          { kind: 'block', type: 'lists_sort' },
        ],
      },
      {
        kind: 'category',
        name: 'Variables',
        colour: '#A65CA6',
        custom: 'VARIABLE',
      },
      {
        kind: 'category',
        name: 'Functions',
        colour: '#9A5CA6',
        custom: 'PROCEDURE',
      },
      {
        kind: 'category',
        name: 'Python',
        colour: '#4B8BBE',
        contents: [
          { kind: 'block', type: 'import_module' },
          { kind: 'block', type: 'function_call' },
          { kind: 'block', type: 'instance_function_call' },
        ],
      },
    ],
  };

  // Inject Blockly
  workspace = Blockly.inject('blocklyDiv', {
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

let syncTimeout;
/**
 * Synchronizes the toolbox with the current import blocks in the workspace.
 */
async function syncToolboxWithImports() {
  if (syncTimeout) {
    clearTimeout(syncTimeout);
  }

  syncTimeout = setTimeout(async () => {
    const blocks = workspace.getAllBlocks(false);
    const currentImports = new Set();

    for (const block of blocks) {
      if (block.type === 'import_module') {
        const moduleName = block.getFieldValue('MODULE_NAME');
        if (moduleName) {
          currentImports.add(moduleName);
        }
      }
    }

    // Check for modules to add
    for (const moduleName of currentImports) {
      if (!importedModules.has(moduleName)) {
        await loadModuleInfo(moduleName);
      }
    }

    // Check for modules to remove
    let changed = false;
    for (const moduleName of importedModules) {
      if (!currentImports.has(moduleName)) {
        importedModules.delete(moduleName);
        changed = true;
      }
    }

    if (changed || [...currentImports].some(m => !isModuleInToolbox(m))) {
      updateToolboxDisplay();
    }
  }, 100);
}

// Cache for module function lists
const moduleFunctionCache = new Map();

async function loadModuleInfo(moduleName) {
  if (moduleFunctionCache.has(moduleName)) {
    importedModules.add(moduleName);
    return;
  }

  try {
    const response = await fetch(`${SERVER_URL}/import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ module: moduleName })
    });

    const info = await response.json();
    if (info.success) {
      moduleFunctionCache.set(moduleName, info.functions);
      importedModules.add(moduleName);
    }
  } catch (error) {
    console.error(`Error loading module ${moduleName}:`, error);
  }
}

function isModuleInToolbox(moduleName) {
  const currentToolbox = workspace.options.languageTree;
  return currentToolbox.contents.some(cat => cat.kind === 'category' && cat.name === moduleName);
}

function updateToolboxDisplay() {
  const toolbox = JSON.parse(JSON.stringify(workspace.initialToolbox));

  for (const moduleName of importedModules) {
    const functions = moduleFunctionCache.get(moduleName);
    if (functions) {
      toolbox.contents.push({
        kind: 'category',
        name: moduleName,
        colour: '#4B8BBE',
        contents: [
          {
            kind: 'block',
            type: 'library_function_call',
            extraState: {
              'func_name': functions[0],
              'options': functions
            }
          }
        ]
      });
    }
  }

  workspace.updateToolbox(toolbox);
}

const instanceMethodCache = new Map();

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
    try {
      const code = Blockly.Python.workspaceToCode(workspace);

      const response = await fetch(`${SERVER_URL}/inspect-instance`, {
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

  try {
    const code = Blockly.Python.workspaceToCode(workspace);
    const response = await fetch(`${SERVER_URL}/inspect-instance-method`, {
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

function updateCodePreview() {
  try {
    const code = Blockly.Python.workspaceToCode(workspace);
    document.getElementById('code-preview').textContent = code;
  } catch (error) {
    console.error('Failed to generate code preview:', error);
  }
}

async function runCode() {
  const runBtn = document.getElementById('runBtn');
  const outputContent = document.getElementById('output-content');

  // Disable button during execution
  runBtn.disabled = true;
  runBtn.textContent = '⏳ Running...';

  // Clear previous output
  outputContent.innerHTML = '';

  try {
    // First check if server is healthy
    try {
      const healthCheck = await fetch(`${SERVER_URL}/health`, {
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
    const pythonCode = Blockly.Python.workspaceToCode(workspace);

    if (!pythonCode.trim()) {
      appendOutput('No code to execute. Add some blocks first!', 'error');
      return;
    }

    // Send code to Python server
    const response = await fetch(`${SERVER_URL}/execute`, {
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

function appendOutput(text, type) {
  const outputContent = document.getElementById('output-content');
  const line = document.createElement('div');
  line.className = `output-line output-${type}`;
  line.textContent = text;
  outputContent.appendChild(line);
  outputContent.scrollTop = outputContent.scrollHeight;
}

function clearWorkspace() {
  if (confirm('Are you sure you want to clear the workspace?')) {
    workspace.clear();
    updateCodePreview();
    document.getElementById('output-content').innerHTML = '';

    // Reset toolbox to initial state
    if (workspace.initialToolbox) {
      workspace.updateToolbox(workspace.initialToolbox);
      importedModules.clear();
    }
  }
}

function exportBlocks() {
  const xml = Blockly.Xml.workspaceToDom(workspace);
  const xmlText = Blockly.Xml.domToText(xml);
  
  // Create a blob and download link
  const blob = new Blob([xmlText], { type: 'text/xml' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'blockly_workspace.xml';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function importBlocks() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.xml';
  input.onchange = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const xml = Blockly.utils.xml.textToDom(event.target.result);
          workspace.clear();
          Blockly.Xml.domToWorkspace(xml, workspace);
          updateCodePreview();
        } catch (err) {
          alert('Error loading file: ' + err.message);
        }
      };
      reader.readAsText(file);
    }
  };
  input.click();
}