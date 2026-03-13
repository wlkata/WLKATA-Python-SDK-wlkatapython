/**
 * Function Call Block Definition
 * Dynamic block that fetches function info from the server and updates its parameters.
 */

/**
 * Initialize the function_call block.
 */
function initFunctionCallBlock() {
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

      const functionCache = getFunctionCache ? getFunctionCache() : new Map();
      const serverUrl = getServerUrl ? getServerUrl() : 'http://127.0.0.1:5000';

      // Check cache first
      if (functionCache.has(funcName)) {
        this.applyFunctionInfo(functionCache.get(funcName));
        return;
      }

      try {
        const response = await fetch(`${serverUrl}/inspect`, {
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
}
