/**
 * Function Call Block Definition
 * Dynamic block that fetches function info from the server and updates its parameters.
 */

// ── Shared helpers for dynamic *args / **kwargs value-input slots ──

/**
 * Get sorted indices of existing vararg value-input slots for a parameter.
 * Slots are named VARARG_<paramName>_<index>.
 */
function getVarargIndices(block, paramName) {
  const prefix = `VARARG_${paramName}_`;
  const indices = [];
  for (const input of block.inputList) {
    if (input.name && input.name.startsWith(prefix)) {
      const idx = parseInt(input.name.substring(prefix.length), 10);
      if (!isNaN(idx)) indices.push(idx);
    }
  }
  indices.sort((a, b) => a - b);
  return indices;
}

/**
 * Get sorted indices of existing varkw slot-pairs for a parameter.
 * Each pair consists of VARKW_KEY_<paramName>_<index> and
 * VARKW_VAL_<paramName>_<index>.  We detect by the KEY input.
 */
function getVarkwIndices(block, paramName) {
  const prefix = `VARKW_KEY_${paramName}_`;
  const indices = [];
  for (const input of block.inputList) {
    if (input.name && input.name.startsWith(prefix)) {
      const idx = parseInt(input.name.substring(prefix.length), 10);
      if (!isNaN(idx)) indices.push(idx);
    }
  }
  indices.sort((a, b) => a - b);
  return indices;
}

/**
 * Find the name of the first input that comes after all slots for a given
 * parameter.  Used as `refInput` for `moveInputBefore` so that newly
 * created slots are placed before any subsequent parameters.
 */
function findInsertBeforeInput(block, paramName) {
  if (!block.functionInfo_) return null;
  const params = block.functionInfo_.parameters;
  const paramIdx = params.findIndex(p => p.name === paramName);
  for (let i = paramIdx + 1; i < params.length; i++) {
    const nextParam = params[i];
    if (nextParam.is_varargs) {
      const nextIndices = getVarargIndices(block, nextParam.name);
      if (nextIndices.length > 0) return `VARARG_${nextParam.name}_${nextIndices[0]}`;
    } else if (nextParam.is_varkwargs) {
      const nextIndices = getVarkwIndices(block, nextParam.name);
      if (nextIndices.length > 0) return `VARKW_KEY_${nextParam.name}_${nextIndices[0]}`;
    } else {
      if (block.getInput(`PARAM_${nextParam.name}`)) return `PARAM_${nextParam.name}`;
    }
  }
  return null;
}

// ── *args helpers ──

/**
 * Add a single *args value-input slot at the correct position.
 */
function addVarargSlot(block, paramName, index) {
  const inputName = `VARARG_${paramName}_${index}`;
  if (block.getInput(inputName)) return null;

  const label = index === 0 ? `*${paramName}` : '';
  const input = block.appendValueInput(inputName).setCheck(null);
  if (label) {
    input.appendField(label);
  }

  const refInput = findInsertBeforeInput(block, paramName);
  if (refInput && block.getInput(refInput)) {
    block.moveInputBefore(inputName, refInput);
  }
  return input;
}

/**
 * Ensure there is always exactly one empty trailing *args slot.
 */
function ensureVarargSlots(block, paramName) {
  if (block.isDisposed()) return;
  const indices = getVarargIndices(block, paramName);

  let hasTrailingEmpty = false;
  if (indices.length > 0) {
    const lastIdx = indices[indices.length - 1];
    const inp = block.getInput(`VARARG_${paramName}_${lastIdx}`);
    if (inp && inp.connection && !inp.connection.targetBlock()) {
      hasTrailingEmpty = true;
    }
  }

  if (!hasTrailingEmpty) {
    const newIdx = indices.length > 0 ? indices[indices.length - 1] + 1 : 0;
    addVarargSlot(block, paramName, newIdx);
  }
}

/**
 * Remove trailing empty *args slots (keep at least one).
 */
function cleanupVarargSlots(block, paramName) {
  if (block.isDisposed()) return;
  const indices = getVarargIndices(block, paramName);
  for (let i = indices.length - 1; i >= 1; i--) {
    const idx = indices[i];
    const inp = block.getInput(`VARARG_${paramName}_${idx}`);
    if (inp && inp.connection && !inp.connection.targetBlock()) {
      block.removeInput(`VARARG_${paramName}_${idx}`);
    } else {
      break;
    }
  }
}

// ── **kwargs helpers ──
// Each kwargs entry is TWO value inputs:
//   VARKW_KEY_<paramName>_<index>  (the keyword)
//   VARKW_VAL_<paramName>_<index>  (the value)
// with a dummy " =" label on the KEY input.

/**
 * Add a single **kwargs key=value pair (two value inputs) at the correct
 * position.  Returns the KEY input.
 */
function addVarkwSlot(block, paramName, index) {
  const keyName = `VARKW_KEY_${paramName}_${index}`;
  const valName = `VARKW_VAL_${paramName}_${index}`;
  if (block.getInput(keyName)) return null;

  const label = index === 0 ? `**${paramName}` : '';
  const keyInput = block.appendValueInput(keyName).setCheck(null);
  if (label) {
    keyInput.appendField(label);
  }

  const valInput = block.appendValueInput(valName).setCheck(null)
      .appendField('=');

  // Move both to correct position
  const refInput = findInsertBeforeInput(block, paramName);
  if (refInput && block.getInput(refInput)) {
    block.moveInputBefore(valName, refInput);
    block.moveInputBefore(keyName, valName);
  }

  return keyInput;
}

/**
 * A varkw slot-pair is "empty" when neither the KEY nor the VAL input has a
 * connected block.
 */
function isVarkwSlotEmpty(block, paramName, idx) {
  const keyInp = block.getInput(`VARKW_KEY_${paramName}_${idx}`);
  const valInp = block.getInput(`VARKW_VAL_${paramName}_${idx}`);
  const hasKey = keyInp && keyInp.connection && keyInp.connection.targetBlock();
  const hasVal = valInp && valInp.connection && valInp.connection.targetBlock();
  return !hasKey && !hasVal;
}

/**
 * A varkw slot-pair is "occupied" when either input has a connected block.
 */
function isVarkwSlotOccupied(block, paramName, idx) {
  return !isVarkwSlotEmpty(block, paramName, idx);
}

/**
 * Ensure there is always one empty trailing **kwargs slot-pair.
 */
function ensureVarkwSlots(block, paramName) {
  if (block.isDisposed()) return;
  const indices = getVarkwIndices(block, paramName);

  let hasTrailingEmpty = false;
  if (indices.length > 0) {
    const lastIdx = indices[indices.length - 1];
    if (isVarkwSlotEmpty(block, paramName, lastIdx)) {
      hasTrailingEmpty = true;
    }
  }

  if (!hasTrailingEmpty) {
    const newIdx = indices.length > 0 ? indices[indices.length - 1] + 1 : 0;
    addVarkwSlot(block, paramName, newIdx);
  }
}

/**
 * Remove trailing empty **kwargs slot-pairs (keep at least one).
 */
function cleanupVarkwSlots(block, paramName) {
  if (block.isDisposed()) return;
  const indices = getVarkwIndices(block, paramName);
  for (let i = indices.length - 1; i >= 1; i--) {
    const idx = indices[i];
    if (isVarkwSlotEmpty(block, paramName, idx)) {
      block.removeInput(`VARKW_VAL_${paramName}_${idx}`);
      block.removeInput(`VARKW_KEY_${paramName}_${idx}`);
    } else {
      break;
    }
  }
}

// ── Combined helpers ──

/**
 * Update dynamic slots on a block: cleanup trailing empties, then ensure
 * each dynamic param still has one trailing empty slot.  Always call this
 * instead of cleanup/ensure separately so that one param's cleanup can
 * never accidentally leave another param without its empty slot.
 */
function updateDynamicSlots(block) {
  if (!block || block.isDisposed() || !block.functionInfo_) return;
  for (const param of block.functionInfo_.parameters) {
    if (param.is_varargs) {
      cleanupVarargSlots(block, param.name);
      ensureVarargSlots(block, param.name);
    } else if (param.is_varkwargs) {
      cleanupVarkwSlots(block, param.name);
      ensureVarkwSlots(block, param.name);
    }
  }
  block.render();
}

// ── Shared applyFunctionInfo implementation ──

/**
 * Common applyFunctionInfo used by function_call, library_function_call,
 * and instance_function_call blocks.
 */
function sharedApplyFunctionInfo(info) {
  this.functionInfo_ = info;

  // Update tooltip with docstring (first 500 chars)
  const docPreview = info.docstring.length > 500
    ? info.docstring.substring(0, 500) + '...'
    : info.docstring;
  this.setTooltip(docPreview);

  // Save current connected blocks before rebuilding
  const oldValues = {};
  if (this.paramInputs_) {
    for (const paramName of this.paramInputs_) {
      const input = this.getInput(`PARAM_${paramName}`);
      if (input && input.connection && input.connection.targetBlock()) {
        oldValues[paramName] = input.connection.targetBlock();
      }
    }
  }

  // Save existing vararg connected blocks before rebuilding
  const oldVarargBlocks = {};
  const oldVarkwData = {};
  if (info.parameters) {
    for (const param of info.parameters) {
      if (param.is_varargs) {
        const indices = getVarargIndices(this, param.name);
        const blocks = [];
        for (const idx of indices) {
          const inp = this.getInput(`VARARG_${param.name}_${idx}`);
          if (inp && inp.connection && inp.connection.targetBlock()) {
            blocks.push(inp.connection.targetBlock());
          }
        }
        if (blocks.length > 0) oldVarargBlocks[param.name] = blocks;
      } else if (param.is_varkwargs) {
        const indices = getVarkwIndices(this, param.name);
        const entries = [];
        for (const idx of indices) {
          const keyInp = this.getInput(`VARKW_KEY_${param.name}_${idx}`);
          const valInp = this.getInput(`VARKW_VAL_${param.name}_${idx}`);
          const keyBlock = (keyInp && keyInp.connection && keyInp.connection.targetBlock()) || null;
          const valBlock = (valInp && valInp.connection && valInp.connection.targetBlock()) || null;
          if (keyBlock || valBlock) {
            entries.push({ keyBlock, valBlock });
          }
        }
        if (entries.length > 0) oldVarkwData[param.name] = entries;
      }
    }
  }

  // Remove all parameter inputs (regular, vararg, varkw)
  const inputNames = this.inputList.map(i => i.name).filter(n => n &&
    (n.startsWith('PARAM_') || n.startsWith('VARARG_') || n.startsWith('VARKW_')));
  for (const name of inputNames) {
    this.removeInput(name);
  }

  // Create new parameter inputs
  this.paramInputs_ = [];

  for (const param of info.parameters) {
    const paramName = param.name;
    this.paramInputs_.push(paramName);

    if (param.is_varargs) {
      const savedBlocks = oldVarargBlocks[paramName] || [];
      const savedCount = savedBlocks.length ||
        (this.savedVarargData_ && this.savedVarargData_[paramName]) || 0;
      const count = savedBlocks.length || (typeof savedCount === 'number' ? savedCount : 0);

      for (let i = 0; i < count; i++) {
        const inp = addVarargSlot(this, paramName, i);
        if (inp && savedBlocks[i]) {
          inp.connection.connect(savedBlocks[i].outputConnection);
        }
      }
      ensureVarargSlots(this, paramName);

    } else if (param.is_varkwargs) {
      const savedEntries = oldVarkwData[paramName] || [];
      const savedCount = savedEntries.length ||
        (this.savedVarkwData_ && this.savedVarkwData_[paramName]) || 0;
      const count = savedEntries.length || (typeof savedCount === 'number' ? savedCount : 0);

      for (let i = 0; i < count; i++) {
        const keyInp = addVarkwSlot(this, paramName, i);
        if (keyInp && savedEntries[i]) {
          if (savedEntries[i].keyBlock) {
            keyInp.connection.connect(savedEntries[i].keyBlock.outputConnection);
          }
          const valInp = this.getInput(`VARKW_VAL_${paramName}_${i}`);
          if (valInp && savedEntries[i].valBlock) {
            valInp.connection.connect(savedEntries[i].valBlock.outputConnection);
          }
        }
      }
      ensureVarkwSlots(this, paramName);

    } else {
      let labelText = paramName;
      if (param.has_default) {
        labelText += ` = ${param.default}`;
      }

      const input = this.appendValueInput(`PARAM_${paramName}`)
          .setCheck(null)
          .appendField(labelText);

      if (oldValues[paramName]) {
        input.connection.connect(oldValues[paramName].outputConnection);
      }
    }
  }

  this.savedVarargData_ = null;
  this.savedVarkwData_ = null;
  this.render();
}

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
      const serverUrl = getServerUrl ? getServerUrl() : 'http://127.0.0.1:5080';

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
    applyFunctionInfo: sharedApplyFunctionInfo,

    // Save extra state for serialization
    mutationToDom: function() {
      const container = document.createElement('mutation');
      container.setAttribute('func_name', this.getFieldValue('FUNC_NAME'));
      container.setAttribute('is_statement', this.isStatement_);

      if (this.functionInfo_) {
        // Save full parameter info so domToMutation can recreate inputs
        // synchronously (before Blockly reconnects child blocks).
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

    // Load extra state from serialization
    domToMutation: function(xmlElement) {
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

      // Synchronously recreate inputs from saved function info so that
      // Blockly can reconnect child blocks before the async server call.
      const funcInfoStr = xmlElement.getAttribute('function_info');
      if (funcInfoStr) {
        try {
          const savedInfo = JSON.parse(funcInfoStr);
          this.applyFunctionInfo(savedInfo);
        } catch(e) {}
      }

      // Refresh from server (will preserve already-connected blocks)
      if (funcName) {
        this.updateFunctionInfo(funcName);
      }
    },

    saveExtraState: function() {
      const state = {
        'func_name': this.getFieldValue('FUNC_NAME'),
        'is_statement': this.isStatement_
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

      // Synchronously recreate inputs from saved function info
      if (state.function_info) {
        this.applyFunctionInfo(state.function_info);
      }

      // Refresh from server
      if (state.func_name) {
        this.updateFunctionInfo(state.func_name);
      }
    }
  };
}
