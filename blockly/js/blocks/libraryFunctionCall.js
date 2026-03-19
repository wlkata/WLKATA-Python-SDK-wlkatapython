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
      const serverUrl = getServerUrl ? getServerUrl() : 'http://127.0.0.1:5080';

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

    applyFunctionInfo: sharedApplyFunctionInfo,

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
      container.setAttribute('func_name', this.getFieldValue('FUNC_NAME'));
      container.setAttribute('is_statement', this.isStatement_);

      const dropdown = this.getField('FUNC_NAME');
      if (dropdown && dropdown.menuGenerator_) {
        const options = dropdown.menuGenerator_.map(opt => opt[1]);
        container.setAttribute('options', JSON.stringify(options));
      }

      if (this.functionInfo_) {
        // Save full function info for synchronous restoration
        container.setAttribute('function_info', JSON.stringify(this.functionInfo_));

        const varargData = {};
        const varkwData = {};
        for (const param of this.functionInfo_.parameters) {
          if (param.is_varargs) {
            const indices = getVarargIndices(this, param.name);
            let count = 0;
            for (const idx of indices) {
              const inp = this.getInput(`VARARG_${param.name}_${idx}`);
              if (inp && inp.connection && inp.connection.targetBlock()) count++;
            }
            if (count > 0) varargData[param.name] = count;
          } else if (param.is_varkwargs) {
            const indices = getVarkwIndices(this, param.name);
            let count = 0;
            for (const idx of indices) {
              if (isVarkwSlotOccupied(this, param.name, idx)) count++;
            }
            if (count > 0) varkwData[param.name] = count;
          }
        }
        if (Object.keys(varargData).length > 0) {
          container.setAttribute('vararg_data', JSON.stringify(varargData));
        }
        if (Object.keys(varkwData).length > 0) {
          container.setAttribute('varkw_data', JSON.stringify(varkwData));
        }
      }

      return container;
    },

    domToMutation: function(xmlElement) {
      const funcName = xmlElement.getAttribute('func_name');
      const optionsStr = xmlElement.getAttribute('options');
      const isStatement = xmlElement.getAttribute('is_statement') === 'true';
      this.setStatementMode(isStatement);

      const varargStr = xmlElement.getAttribute('vararg_data');
      const varkwStr = xmlElement.getAttribute('varkw_data');
      if (varargStr) {
        try { this.savedVarargData_ = JSON.parse(varargStr); } catch(e) {}
      }
      if (varkwStr) {
        try { this.savedVarkwData_ = JSON.parse(varkwStr); } catch(e) {}
      }

      if (optionsStr) {
        try {
          const options = JSON.parse(optionsStr);
          this.updateOptions(options);
        } catch (e) {}
      }

      // Synchronously recreate inputs from saved function info
      const funcInfoStr = xmlElement.getAttribute('function_info');
      if (funcInfoStr) {
        try {
          const savedInfo = JSON.parse(funcInfoStr);
          this.applyFunctionInfo(savedInfo);
        } catch(e) {}
      }

      if (funcName) {
        this.setFieldValue(funcName, 'FUNC_NAME');
        this.updateFunctionInfo(funcName);
      }
    },

    saveExtraState: function() {
      const dropdown = this.getField('FUNC_NAME');
      const state = {
        'func_name': this.getFieldValue('FUNC_NAME'),
        'is_statement': this.isStatement_,
        'options': dropdown && dropdown.menuGenerator_ ? dropdown.menuGenerator_.map(opt => opt[1]) : []
      };

      if (this.functionInfo_) {
        // Save full function info for synchronous restoration
        state.function_info = this.functionInfo_;

        const varargData = {};
        const varkwData = {};
        for (const param of this.functionInfo_.parameters) {
          if (param.is_varargs) {
            const indices = getVarargIndices(this, param.name);
            let count = 0;
            for (const idx of indices) {
              const inp = this.getInput(`VARARG_${param.name}_${idx}`);
              if (inp && inp.connection && inp.connection.targetBlock()) count++;
            }
            if (count > 0) varargData[param.name] = count;
          } else if (param.is_varkwargs) {
            const indices = getVarkwIndices(this, param.name);
            let count = 0;
            for (const idx of indices) {
              if (isVarkwSlotOccupied(this, param.name, idx)) count++;
            }
            if (count > 0) varkwData[param.name] = count;
          }
        }
        if (Object.keys(varargData).length > 0) state.vararg_data = varargData;
        if (Object.keys(varkwData).length > 0) state.varkw_data = varkwData;
      }

      return state;
    },

    loadExtraState: function(state) {
      if (state.is_statement !== undefined) {
        this.setStatementMode(state.is_statement);
      }
      if (state.vararg_data) this.savedVarargData_ = state.vararg_data;
      if (state.varkw_data) this.savedVarkwData_ = state.varkw_data;
      if (state.options) {
        this.updateOptions(state.options);
      }

      // Synchronously recreate inputs from saved function info
      if (state.function_info) {
        this.applyFunctionInfo(state.function_info);
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
