/**
 * Instance Function Call Block Definition
 * Block for calling methods on an instance variable.
 */

/**
 * Initialize the instance_function_call block.
 */
function initInstanceFunctionCallBlock() {
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
      if (typeof updateInstanceMethodInfo === 'function') {
        updateInstanceMethodInfo(this, methodName);
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
      const container = document.createElement('mutation');
      container.setAttribute('func_name', this.getFieldValue('METHOD'));
      container.setAttribute('is_statement', this.isStatement_);
      container.setAttribute('method_options', JSON.stringify(this.methodOptions_));

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
      const methodOptions = xmlElement.getAttribute('method_options');
      const funcName = xmlElement.getAttribute('func_name');
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

      if (methodOptions) {
        try {
          this.updateOptions(JSON.parse(methodOptions));
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
        this.setFieldValue(funcName, 'METHOD');
        this.updateFunctionInfo(funcName);
      }
    },

    saveExtraState: function() {
      const state = {
        'func_name': this.getFieldValue('METHOD'),
        'is_statement': this.isStatement_,
        'method_options': this.methodOptions_
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
      if (state.method_options) {
        this.updateOptions(state.method_options);
      }

      // Synchronously recreate inputs from saved function info
      if (state.function_info) {
        this.applyFunctionInfo(state.function_info);
      }

      if (state.func_name) {
        this.setFieldValue(state.func_name, 'METHOD');
        this.updateFunctionInfo(state.func_name);
      }
    }
  };
}
