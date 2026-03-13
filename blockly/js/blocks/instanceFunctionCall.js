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
      const baseBlock = Blockly.Blocks['function_call'];
      if (baseBlock && baseBlock.mutationToDom) {
        const baseContainer = baseBlock.mutationToDom.call(this);
        container.setAttribute('func_name', baseContainer.getAttribute('func_name'));
        container.setAttribute('is_statement', baseContainer.getAttribute('is_statement'));
      } else {
        container.setAttribute('func_name', this.getFieldValue('METHOD'));
        container.setAttribute('is_statement', this.isStatement_);
      }
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
