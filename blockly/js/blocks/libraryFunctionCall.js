/**
 * Library Function Call Block Definition
 * Dynamic function call block with dropdown for library functions.
 */

/**
 * Initialize the library_function_call block.
 * Reuses logic from function_call block.
 */
function initLibraryFunctionCallBlock() {
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
    updateFunctionInfo: Blockly.Blocks['function_call'] ? Blockly.Blocks['function_call'].updateFunctionInfo : async function(funcName) {
      if (!funcName || funcName.trim() === '' || funcName === '...') {
        return;
      }

      const functionCache = getFunctionCache ? getFunctionCache() : new Map();
      const serverUrl = getServerUrl ? getServerUrl() : 'http://127.0.0.1:5000';

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
          this.setTooltip(`Error: ${info.error}`);
        }
      } catch (error) {
        console.error('Failed to fetch function info:', error);
        this.setTooltip(`Failed to fetch function info: ${error.message}`);
      }
    },

    applyFunctionInfo: Blockly.Blocks['function_call'] ? Blockly.Blocks['function_call'].applyFunctionInfo : function(info) {
      this.functionInfo_ = info;

      const docPreview = info.docstring.length > 500
        ? info.docstring.substring(0, 500) + '...'
        : info.docstring;
      this.setTooltip(docPreview);

      const oldValues = {};
      if (this.paramInputs_) {
        for (const paramName of this.paramInputs_) {
          const input = this.getInput(`PARAM_${paramName}`);
          if (input && input.connection && input.connection.targetBlock()) {
            oldValues[paramName] = input.connection.targetBlock();
          }
        }
      }

      const inputNames = this.inputList.map(i => i.name).filter(n => n && n.startsWith('PARAM_'));
      for (const name of inputNames) {
        this.removeInput(name);
      }

      this.paramInputs_ = [];

      for (const param of info.parameters) {
        const paramName = param.name;
        this.paramInputs_.push(paramName);

        let labelText = paramName;
        if (param.has_default) {
          labelText += ` = ${param.default}`;
        }
        if (param.is_varargs) {
          labelText = '*' + paramName;
        } else if (param.is_varkwargs) {
          labelText = '**' + paramName;
        }

        const input = this.appendValueInput(`PARAM_${paramName}`)
            .setCheck(null)
            .appendField(labelText);

        if (oldValues[paramName]) {
          input.connection.connect(oldValues[paramName].outputConnection);
        }
      }

      this.render();
    },

    customContextMenu: Blockly.Blocks['function_call'] ? Blockly.Blocks['function_call'].customContextMenu : function(options) {
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

    setStatementMode: Blockly.Blocks['function_call'] ? Blockly.Blocks['function_call'].setStatementMode : function(isStatement) {
      if (this.isStatement_ === isStatement) {
        return;
      }
      this.isStatement_ = isStatement;
      this.updateShape_();
    },

    updateShape_: Blockly.Blocks['function_call'] ? Blockly.Blocks['function_call'].updateShape_ : function() {
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

    mutationToDom: function() {
      const container = document.createElement('mutation');
      const baseBlock = Blockly.Blocks['function_call'];
      if (baseBlock && baseBlock.mutationToDom) {
        const baseContainer = baseBlock.mutationToDom.call(this);
        container.setAttribute('func_name', baseContainer.getAttribute('func_name'));
        container.setAttribute('is_statement', baseContainer.getAttribute('is_statement'));
        if (baseContainer.getAttribute('params')) {
          container.setAttribute('params', baseContainer.getAttribute('params'));
        }
      } else {
        container.setAttribute('func_name', this.getFieldValue('FUNC_NAME'));
        container.setAttribute('is_statement', this.isStatement_);
        if (this.functionInfo_) {
          container.setAttribute('params', JSON.stringify(this.functionInfo_.parameters.map(p => p.name)));
        }
      }

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
}
