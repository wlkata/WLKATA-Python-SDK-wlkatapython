/**
 * Function Parameter & Local Variable System
 *
 * 1. function_param_get  – dropdown-based block to get a param or local var
 * 2. function_param_set  – dropdown-based block to set a param or local var
 * 3. Procedure overrides – suppress workspace variable creation for params,
 *    remove "Create get x" context items, persist localVars_
 * 4. PROCEDURE flyout    – only procedures_defreturn
 * 5. VARIABLE flyout     – hides param and local-var names
 * 6. LocalVariablesIcon  – green "V" icon: get, set, call, add/remove local vars
 * 7. Workspace listener  – auto-attach icon + default-value inputs
 */

// ────────────────────────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────────────────────────

function findEnclosingProcedure(block) {
  var current = block;
  while (current) {
    if (current.type === 'procedures_defnoreturn' ||
        current.type === 'procedures_defreturn') {
      return current;
    }
    current = current.getSurroundParent();
  }
  return null;
}

function getProcLocalNames(procBlock) {
  var params = (procBlock.arguments_ || []).slice();
  var locals = (procBlock.localVars_ || []).slice();
  return { params: params, locals: locals, all: params.concat(locals) };
}

function getAllLocalScopeNames(workspace) {
  var names = new Set();
  var blocks = workspace.getAllBlocks(false);
  for (var i = 0; i < blocks.length; i++) {
    var b = blocks[i];
    if (b.type === 'procedures_defnoreturn' || b.type === 'procedures_defreturn') {
      if (b.arguments_) { for (var j = 0; j < b.arguments_.length; j++) { if (b.arguments_[j]) names.add(b.arguments_[j]); } }
      if (b.localVars_)  { for (var k = 0; k < b.localVars_.length; k++)  { if (b.localVars_[k])  names.add(b.localVars_[k]);  } }
    }
  }
  return names;
}

/** Build a dropdown option list from the enclosing procedure's params+locals. */
function _buildLocalDropdown() {
  return function () {
    var proc = findEnclosingProcedure(this.getSourceBlock());
    if (!proc) return [['(none)', '__NONE__']];
    var info = getProcLocalNames(proc);
    if (info.all.length === 0) return [['(none)', '__NONE__']];
    var opts = [];
    for (var i = 0; i < info.all.length; i++) {
      opts.push([info.all[i], info.all[i]]);
    }
    return opts;
  };
}

// ────────────────────────────────────────────────────────────────────────────
// 1.  function_param_get  &  function_param_set  (dropdown)
// ────────────────────────────────────────────────────────────────────────────

function initFunctionParamBlock() {

  // ── GET ──
  Blockly.Blocks['function_param_get'] = {
    init: function () {
      this.appendDummyInput()
          .appendField('get')
          .appendField(new Blockly.FieldDropdown(_buildLocalDropdown()), 'PARAM_NAME');
      this.setOutput(true, null);
      this.setColour(330);
      this.setTooltip('Get the value of a function parameter or local variable.');
    },
    onchange: function () {
      var proc = findEnclosingProcedure(this);
      if (!proc) { this.setWarningText('Place inside a function definition.'); }
      else { this.setWarningText(null); }
    }
  };

  // ── SET ──
  Blockly.Blocks['function_param_set'] = {
    init: function () {
      this.appendValueInput('VALUE')
          .appendField('set')
          .appendField(new Blockly.FieldDropdown(_buildLocalDropdown()), 'PARAM_NAME')
          .appendField('to');
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setColour(330);
      this.setTooltip('Set the value of a function parameter or local variable.');
    },
    onchange: function () {
      var proc = findEnclosingProcedure(this);
      if (!proc) { this.setWarningText('Place inside a function definition.'); }
      else { this.setWarningText(null); }
    }
  };

  // ── LOCAL INSTANCE CALL ──
  // Calls a method on a local variable: abc.xyz(args...)
  // Uses the local-var dropdown for instance, method dropdown auto-populated
  // from the server (like instance_function_call).
  Blockly.Blocks['local_instance_call'] = {
    init: function () {
      this.appendDummyInput('INSTANCE_ROW')
          .appendField('call')
          .appendField(new Blockly.FieldDropdown(_buildLocalDropdown()), 'INSTANCE_NAME')
          .appendField('.')
          .appendField(new Blockly.FieldDropdown([['...', '...']]), 'METHOD_NAME');
      this.setInputsInline(false);
      this.setOutput(true, null);
      this.setColour(290);
      this.setTooltip('Call a method on a local variable or parameter.');
      this.isStatement_ = false;
      this.functionInfo_ = null;
      this.methodOptions_ = [];
    },
    onchange: function () {
      var proc = findEnclosingProcedure(this);
      if (!proc) { this.setWarningText('Place inside a function definition.'); }
      else { this.setWarningText(null); }
    },
    /**
     * Build inspection code for the server.
     *
     * The problem: local variables like `abc = SomeClass()` live inside
     * `def func(): ...` in the generated code.  The server does exec()
     * at top-level, so it never sees them.
     *
     * Solution: parse the generated code string, find the enclosing
     * function's def block, extract its indented body lines, dedent
     * them to top-level, and combine with imports + top-level code.
     */
    _buildInspectionCode: function() {
      var ws = typeof getWorkspace === 'function' ? getWorkspace() : null;
      if (!ws) return null;
      var fullCode;
      try { fullCode = Blockly.Python.workspaceToCode(ws); } catch(e) { return null; }
      if (!fullCode) return null;

      // Get the function name from the enclosing procedure block
      var proc = findEnclosingProcedure(this);
      if (!proc) return fullCode;
      var funcName = proc.getFieldValue('NAME');
      if (!funcName) return fullCode;

      // Use the raw function name — Blockly doesn't mangle procedure names
      // in practice (they go through getProcedureName which just sanitises).
      // We also try a sanitised version: replace spaces with underscores.
      var pyFuncName = funcName.replace(/ /g, '_');

      var lines = fullCode.split('\n');
      var topLines = [];      // imports, top-level assignments
      var bodyLines = [];     // indented body of our function
      var state = 'top';      // 'top', 'our_func', 'other_func'
      var indent = '  ';      // Blockly default indent

      for (var i = 0; i < lines.length; i++) {
        var line = lines[i];
        var trimmed = line.trimStart();
        var isIndented = line.length > 0 && (line[0] === ' ' || line[0] === '\t');

        if (state === 'our_func') {
          if (line.length === 0 || isIndented) {
            bodyLines.push(line);
          } else {
            // Back to top level
            state = 'top';
            // Fall through to process this line as top-level
          }
        }

        if (state === 'other_func') {
          if (line.length === 0 || isIndented) {
            continue; // skip other function's body
          } else {
            state = 'top';
            // Fall through to process this line as top-level
          }
        }

        if (state === 'top') {
          if (trimmed.startsWith('def ' + pyFuncName + '(')) {
            state = 'our_func';
          } else if (trimmed.startsWith('def ')) {
            state = 'other_func';
          } else if (line.length > 0 && !isIndented) {
            // Skip lines that call our function (since we inlined its body,
            // the function is not defined and calling it would crash exec())
            // Matches: anything = pyFuncName(...) or bare pyFuncName(...)
            var callPattern = new RegExp('(^|=\\s*)' + pyFuncName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\s*\\(');
            if (!callPattern.test(trimmed)) {
              topLines.push(line);
            }
          }
        }
      }

      // Dedent body lines (remove one level of indentation)
      var dedented = [];
      for (var j = 0; j < bodyLines.length; j++) {
        var bline = bodyLines[j];
        if (bline.length === 0) { dedented.push(''); continue; }
        // Remove leading indent (try Blockly indent first, then tab)
        if (bline.substring(0, indent.length) === indent) {
          dedented.push(bline.substring(indent.length));
        } else if (bline[0] === '\t') {
          dedented.push(bline.substring(1));
        } else {
          dedented.push(bline);
        }
      }

      // Remove lines that would break exec():
      // - 'global ...' declarations
      // - lines generated by this block itself (e.g. "a....()") or any
      //   local_instance_call with placeholder "..." method
      var instanceName = this.getFieldValue('INSTANCE_NAME');
      var cleanBody = [];
      for (var k = 0; k < dedented.length; k++) {
        var cline = dedented[k].trimStart();
        if (cline.startsWith('global ')) continue;
        // Skip lines from local_instance_call blocks with "..." placeholder
        // These look like: "varname....(...)" or "varname.None"
        if (cline.indexOf('....') !== -1) continue;
        if (cline === 'None') continue;
        // Skip return statements (they'd error at top level)
        if (cline.startsWith('return ')) continue;
        cleanBody.push(dedented[k]);
      }

      var result = topLines.join('\n') + '\n' + cleanBody.join('\n');
      return result;
    },

    // Fetch available methods for the instance from the server
    updateMethodList: function() {
      var block = this;
      var instanceName = block.getFieldValue('INSTANCE_NAME');
      if (!instanceName || instanceName === '__NONE__') return;
      if (block.updateTimer_) clearTimeout(block.updateTimer_);
      block.updateTimer_ = setTimeout(function() {
        var serverUrl = typeof getServerUrl === 'function' ? getServerUrl() : 'http://127.0.0.1:5080';
        var code = block._buildInspectionCode();
        if (!code) return;
        console.log('[local_instance_call] Inspection code for "' + instanceName + '":\n' + code);
        fetch(serverUrl + '/inspect-instance', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code: code, instance: instanceName })
        }).then(function(r) { return r.json(); }).then(function(info) {
          if (info.success) {
            var methods = info.methods || [];
            var currentMethod = block.getFieldValue('METHOD_NAME');
            block.updateOptions(methods);
            if (methods.length > 0) {
              if (!currentMethod || currentMethod === '...' || methods.indexOf(currentMethod) === -1) {
                block.setFieldValue(methods[0], 'METHOD_NAME');
                block.updateFunctionInfo(methods[0]);
              }
            }
          } else {
            block.updateOptions([]);
          }
        }).catch(function() {});
      }, 300);
    },
    updateOptions: function(options) {
      this.methodOptions_ = options || [];
      var dropdown = this.getField('METHOD_NAME');
      if (dropdown) {
        var menuOptions = this.methodOptions_.length
          ? this.methodOptions_.map(function(opt) { return [opt, opt]; })
          : [['...', '...']];
        dropdown.menuGenerator_ = menuOptions;
        var block = this;
        dropdown.setValidator(function(newValue) {
          if (newValue && newValue !== '...') {
            block.updateFunctionInfo(newValue);
          }
          return newValue;
        });
      }
    },
    // Fetch method signature from server
    updateFunctionInfo: function(methodName) {
      var block = this;
      var instanceName = block.getFieldValue('INSTANCE_NAME');
      if (!instanceName || instanceName === '__NONE__' || !methodName || methodName === '...') return;
      var serverUrl = typeof getServerUrl === 'function' ? getServerUrl() : 'http://127.0.0.1:5080';
      var cleanMethod = methodName.indexOf('.') !== -1 ? methodName.split('.').pop() : methodName;
      var code = block._buildInspectionCode();
      if (!code) return;
      fetch(serverUrl + '/inspect-instance-method', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: code, instance: instanceName, method: cleanMethod })
      }).then(function(r) { return r.json(); }).then(function(info) {
        if (info.success) {
          block.applyFunctionInfo(info);
          block.functionInfo_ = info;
        }
      }).catch(function() {});
    },
    applyFunctionInfo: sharedApplyFunctionInfo,
    customContextMenu: function(options) {
      var block = this;
      options.push({
        text: block.isStatement_ ? 'Use as Expression' : 'Use as Statement',
        enabled: true,
        callback: function() { block.setStatementMode(!block.isStatement_); }
      });
    },
    setStatementMode: function(isStatement) {
      if (this.isStatement_ === isStatement) return;
      this.isStatement_ = isStatement;
      if (isStatement) {
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
      var container = document.createElement('mutation');
      container.setAttribute('is_statement', this.isStatement_);
      container.setAttribute('method_options', JSON.stringify(this.methodOptions_ || []));
      if (this.functionInfo_) {
        container.setAttribute('function_info', JSON.stringify(this.functionInfo_));
      }
      return container;
    },
    domToMutation: function(xmlElement) {
      var isStatement = xmlElement.getAttribute('is_statement') === 'true';
      this.setStatementMode(isStatement);
      var methodOptions = xmlElement.getAttribute('method_options');
      if (methodOptions) {
        try { this.updateOptions(JSON.parse(methodOptions)); } catch(e) {}
      }
      var funcInfoStr = xmlElement.getAttribute('function_info');
      if (funcInfoStr) {
        try { this.applyFunctionInfo(JSON.parse(funcInfoStr)); } catch(e) {}
      }
      var methodName = xmlElement.getAttribute('method_name');
      if (methodName) {
        this.setFieldValue(methodName, 'METHOD_NAME');
        this.updateFunctionInfo(methodName);
      }
    },
    saveExtraState: function() {
      var state = {
        is_statement: this.isStatement_,
        method_name: this.getFieldValue('METHOD_NAME'),
        method_options: this.methodOptions_ || []
      };
      if (this.functionInfo_) state.function_info = this.functionInfo_;
      return state;
    },
    loadExtraState: function(state) {
      if (state.is_statement !== undefined) this.setStatementMode(state.is_statement);
      if (state.method_options) this.updateOptions(state.method_options);
      if (state.function_info) this.applyFunctionInfo(state.function_info);
      if (state.method_name) {
        this.setFieldValue(state.method_name, 'METHOD_NAME');
        this.updateFunctionInfo(state.method_name);
      }
    }
  };
}

// ────────────────────────────────────────────────────────────────────────────
// 2.  Procedure overrides
// ────────────────────────────────────────────────────────────────────────────

function initProcedureOverrides() {
  var PROC_TYPES = ['procedures_defnoreturn', 'procedures_defreturn'];

  for (var i = 0; i < PROC_TYPES.length; i++) {
    var procType = PROC_TYPES[i];
    var original = Blockly.Blocks[procType];
    if (!original) continue;

    // ── Remove "Create 'get x'" context-menu items for params ──
    (function(orig) {
      var origCtx = orig.customContextMenu;
      orig.customContextMenu = function (options) {
        if (origCtx) origCtx.call(this, options);
        var paramNames = new Set(this.arguments_ || []);
        if (paramNames.size > 0) {
          var kept = [];
          for (var j = 0; j < options.length; j++) {
            var opt = options[j];
            var dominated = false;
            if (opt.text) {
              paramNames.forEach(function(pn) {
                if (opt.text.includes(pn) && opt.text.toLowerCase().includes('get')) dominated = true;
              });
            }
            if (!dominated) kept.push(opt);
          }
          options.length = 0;
          for (var k = 0; k < kept.length; k++) options.push(kept[k]);
        }
      };
    })(original);

    // ── Suppress workspace variable creation for parameters ──
    // Override compose() so that after the built-in compose runs we
    // add default-value input slots for each parameter.
    (function(orig) {
      var origCompose = orig.compose;
      orig.compose = function (containerBlock) {
        // Run original compose (this creates workspace variables + updates arguments_)
        if (origCompose) origCompose.call(this, containerBlock);

        var newParams = this.arguments_ ? this.arguments_.slice() : [];
        var paramSet = new Set(newParams);

        // Remove ALL DEFAULT_ inputs that don't match a current param
        var allInputs = this.inputList.slice();
        for (var r = 0; r < allInputs.length; r++) {
          var inp = allInputs[r];
          if (inp.name && inp.name.startsWith('DEFAULT_')) {
            var pName = inp.name.substring(8);
            if (!paramSet.has(pName)) {
              try { this.removeInput(inp.name); } catch(e) {}
            }
          }
        }

        // Add DEFAULT_ inputs for params that don't have one yet
        for (var a = 0; a < newParams.length; a++) {
          var inputName = 'DEFAULT_' + newParams[a];
          if (this.getInput(inputName)) continue;
          try {
            this.appendValueInput(inputName)
              .setAlign(Blockly.ALIGN_RIGHT)
              .appendField('default ' + newParams[a] + ':');
          } catch(e) {}
        }
      };
    })(original);

    // ── Persist localVars_ via JSON (saveExtraState / loadExtraState) ──
    (function(orig) {
      var origSave = orig.saveExtraState;
      orig.saveExtraState = function () {
        var state = origSave ? origSave.call(this) : null;
        var out = state || {};
        if (this.localVars_ && this.localVars_.length > 0) {
          out.localVars = this.localVars_.slice();
        }
        return (Object.keys(out).length > 0) ? out : null;
      };
      var origLoad = orig.loadExtraState;
      orig.loadExtraState = function (state) {
        if (origLoad) origLoad.call(this, state);
        if (state && state.localVars) {
          this.localVars_ = state.localVars.slice();
        }
      };
    })(original);

    // ── Persist localVars_ via XML (mutationToDom / domToMutation) ──
    (function(orig) {
      var origMutToDom = orig.mutationToDom;
      orig.mutationToDom = function (opt_paramIds) {
        var container = origMutToDom ? origMutToDom.call(this, opt_paramIds) : document.createElement('mutation');
        if (this.localVars_ && this.localVars_.length > 0) {
          container.setAttribute('localvars', JSON.stringify(this.localVars_));
        }
        return container;
      };
      var origDomToMut = orig.domToMutation;
      orig.domToMutation = function (xmlElement) {
        if (origDomToMut) origDomToMut.call(this, xmlElement);
        var lv = xmlElement.getAttribute('localvars');
        if (lv) { try { this.localVars_ = JSON.parse(lv); } catch (e) { /* ignore */ } }
      };
    })(original);
  }

  scheduleFlyoutOverrides();
}

// ────────────────────────────────────────────────────────────────────────────
// 3.  PROCEDURE flyout
// ────────────────────────────────────────────────────────────────────────────

function scheduleFlyoutOverrides() {
  var tryOverride = function () {
    var ws = typeof getWorkspace === 'function' ? getWorkspace() : null;
    if (!ws) { setTimeout(tryOverride, 100); return; }
    installProcedureFlyout(ws);
    installFilteredVariablesFlyout(ws);
  };
  setTimeout(tryOverride, 200);
}

function installProcedureFlyout(workspace) {
  workspace.registerToolboxCategoryCallback('PROCEDURE', function (ws) {
    var items = [];
    if (Blockly.Blocks['procedures_defreturn']) {
      items.push({ kind:'block', type:'procedures_defreturn', gap:16,
        fields:{ NAME: Blockly.Msg['PROCEDURES_DEFRETURN_PROCEDURE'] || 'do something' } });
    }
    if (Blockly.Blocks['procedures_ifreturn']) {
      items.push({ kind:'block', type:'procedures_ifreturn', gap:24 });
    }
    var allProcs = Blockly.Procedures.allProcedures(ws);
    for (var i = 0; i < allProcs[0].length; i++) {
      var p = allProcs[0][i];
      items.push({ kind:'block', type:'procedures_callnoreturn', gap:16,
        extraState:{ name:p[0], params:p[1] } });
    }
    for (var j = 0; j < allProcs[1].length; j++) {
      var q = allProcs[1][j];
      items.push({ kind:'block', type:'procedures_callreturn', gap:16,
        extraState:{ name:q[0], params:q[1] } });
    }
    return items;
  });
}

// ────────────────────────────────────────────────────────────────────────────
// 4.  VARIABLE flyout  (hides params AND local vars)
// ────────────────────────────────────────────────────────────────────────────

function installFilteredVariableDropdown() {
  // Override FieldVariable.prototype.getOptions so that the dropdown on
  // variables_get / variables_set blocks never shows function parameters
  // or local variables.  We wrap the original getOptions to filter results.
  var FV = Blockly.FieldVariable;
  if (!FV || !FV.prototype) return;

  var origGetOptions = FV.prototype.getOptions;
  FV.prototype.getOptions = function(opt_useCache) {
    var options = origGetOptions.call(this, opt_useCache);
    // Only filter when generating fresh options (not cached)
    var block = this.getSourceBlock();
    if (!block || block.isInFlyout) return options;
    var ws = block.workspace;
    if (!ws || typeof getAllLocalScopeNames !== 'function') return options;
    var localNames = getAllLocalScopeNames(ws);
    if (localNames.size === 0) return options;
    // Filter: keep options whose display text is NOT a local-scope name
    // Options format: [[displayName, id], ...] with special entries at the end
    // (Rename variable, Delete variable) that we always keep.
    var filtered = [];
    for (var i = 0; i < options.length; i++) {
      var opt = options[i];
      var displayName = opt[0];
      // Keep special menu items (Rename/Delete) — they have special constant IDs
      if (opt[1] === 'RENAME_VARIABLE_ID' || opt[1] === 'DELETE_VARIABLE_ID') {
        filtered.push(opt);
        continue;
      }
      // Filter out local-scope names
      if (!localNames.has(displayName)) {
        filtered.push(opt);
      }
    }
    return filtered.length > 0 ? filtered : options;
  };
}

function installFilteredVariablesFlyout(workspace) {
  workspace.registerToolboxCategoryCallback('VARIABLE', function (ws) {
    var localNames = getAllLocalScopeNames(ws);
    ws.registerButtonCallback('CREATE_VARIABLE', function (btn) {
      Blockly.Variables.createVariableButtonHandler(btn.getTargetWorkspace());
    });
    var items = [{ kind:'button', text:'%{BKY_NEW_VARIABLE}', callbackkey:'CREATE_VARIABLE' }];
    var allVars = ws.getVariableMap().getVariablesOfType('');
    var filtered = localNames.size > 0
      ? allVars.filter(function(v) { return !localNames.has(v.getName()); })
      : allVars;
    if (filtered.length === 0) return items;
    filtered.sort(function(a,b) { return a.getName().localeCompare(b.getName(), undefined, {sensitivity:'base'}); });
    var last = filtered[filtered.length - 1];
    if (Blockly.Blocks['variables_set']) {
      items.push({ kind:'block', type:'variables_set',
        gap: Blockly.Blocks['math_change'] ? 8 : 24,
        fields:{ VAR:{ name:last.getName(), type:last.getType() } } });
    }
    if (Blockly.Blocks['math_change']) {
      items.push({ kind:'block', type:'math_change',
        gap: Blockly.Blocks['variables_get'] ? 20 : 8,
        fields:{ VAR:{ name:last.getName(), type:last.getType() } },
        inputs:{ DELTA:{ shadow:{ type:'math_number', fields:{ NUM:1 } } } } });
    }
    if (Blockly.Blocks['variables_get']) {
      for (var i = 0; i < filtered.length; i++) {
        items.push({ kind:'block', type:'variables_get', gap:8,
          fields:{ VAR:{ name:filtered[i].getName(), type:filtered[i].getType() } } });
      }
    }
    return items;
  });
}

// ────────────────────────────────────────────────────────────────────────────
// 5.  LocalVariablesIcon
// ────────────────────────────────────────────────────────────────────────────

var _LocalVariablesIcon = null;

/** Electron-safe prompt dialog. */
function _localVarPrompt(message, defaultValue, callback) {
  var modal = document.createElement('div');
  modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:flex;justify-content:center;align-items:center;z-index:10000;';
  var dialog = document.createElement('div');
  dialog.style.cssText = 'background:white;padding:20px;border-radius:8px;box-shadow:0 4px 20px rgba(0,0,0,0.3);min-width:300px;';
  var label = document.createElement('label');
  label.textContent = message;
  label.style.cssText = 'display:block;margin-bottom:10px;font-weight:bold;white-space:pre-line;';
  var input = document.createElement('input');
  input.type = 'text'; input.value = defaultValue || '';
  input.style.cssText = 'width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;margin-bottom:15px;';
  var btnRow = document.createElement('div');
  btnRow.style.cssText = 'display:flex;justify-content:flex-end;gap:10px;';
  var cancelBtn = document.createElement('button');
  cancelBtn.textContent = 'Cancel';
  cancelBtn.style.cssText = 'padding:8px 16px;background:#ccc;border:none;border-radius:4px;cursor:pointer;';
  var okBtn = document.createElement('button');
  okBtn.textContent = 'OK';
  okBtn.style.cssText = 'padding:8px 16px;background:#2196F3;color:white;border:none;border-radius:4px;cursor:pointer;';
  function close(val) { document.body.removeChild(modal); callback(val); }
  cancelBtn.onclick = function() { close(null); };
  okBtn.onclick = function() { close(input.value); };
  input.addEventListener('keypress', function(e) { if (e.key === 'Enter') close(input.value); });
  btnRow.appendChild(cancelBtn); btnRow.appendChild(okBtn);
  dialog.appendChild(label); dialog.appendChild(input); dialog.appendChild(btnRow);
  modal.appendChild(dialog); document.body.appendChild(modal);
  input.focus(); input.select();
}

/** Electron-safe alert dialog. */
function _localVarAlert(message, callback) {
  var modal = document.createElement('div');
  modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:flex;justify-content:center;align-items:center;z-index:10000;';
  var dialog = document.createElement('div');
  dialog.style.cssText = 'background:white;padding:20px;border-radius:8px;box-shadow:0 4px 20px rgba(0,0,0,0.3);min-width:280px;';
  var label = document.createElement('p');
  label.textContent = message; label.style.cssText = 'margin:0 0 15px 0;';
  var okBtn = document.createElement('button');
  okBtn.textContent = 'OK';
  okBtn.style.cssText = 'padding:8px 16px;background:#2196F3;color:white;border:none;border-radius:4px;cursor:pointer;float:right;';
  okBtn.onclick = function() { document.body.removeChild(modal); if (callback) callback(); };
  dialog.appendChild(label); dialog.appendChild(okBtn);
  modal.appendChild(dialog); document.body.appendChild(modal); okBtn.focus();
}

function initLocalVariablesIcon() {
  if (typeof Blockly === 'undefined') return;

  class LocalVariablesIcon extends Blockly.icons.Icon {
    constructor(block) { super(block); this.tooltip = 'Parameters & local variables'; }
    getType()   { return LocalVariablesIcon.TYPE; }
    getSize()   { return new Blockly.utils.Size(20, 20); }
    getWeight() { return 1; }

    initView(pointerdownListener) {
      super.initView(pointerdownListener);
      if (!this.svgRoot) return;
      while (this.svgRoot.firstChild) this.svgRoot.removeChild(this.svgRoot.firstChild);
      this.svgRoot.setAttribute('style', 'display: inline;');
      Blockly.utils.dom.createSvgElement(Blockly.utils.Svg.CIRCLE,
        { cx:'10', cy:'10', r:'9', fill:'#4CAF50', stroke:'#2E7D32', 'stroke-width':'1' }, this.svgRoot);
      var t = Blockly.utils.dom.createSvgElement(Blockly.utils.Svg.TEXT,
        { x:'10', y:'14', 'text-anchor':'middle', 'font-size':'12', 'font-weight':'bold', fill:'#fff' }, this.svgRoot);
      t.textContent = 'V';
    }

    onClick() { this.showMenu(); }

    showMenu() {
      var block = this.getSourceBlock();
      if (!block || block.isInFlyout) return;
      var info = getProcLocalNames(block);
      var options = [];
      var self = this;
      var hasAny = info.all.length > 0;

      // ── Single "get" block (dropdown will list all params+locals) ──
      options.push({ text: 'Create GET block', enabled: hasAny,
        callback: function() { self._createParamBlock('function_param_get', info.all[0]); } });

      // ── Single "set" block ──
      options.push({ text: 'Create SET block', enabled: hasAny,
        callback: function() { self._createParamBlock('function_param_set', info.all[0]); } });

      // ── Call method on a local variable (abc.xyz()) ──
      options.push({ text: 'Create local.method() call', enabled: hasAny,
        callback: function() { self._createParamBlock('local_instance_call', info.all[0]); } });

      // ── Call this function (recursive / from inside) ──
      var funcName = block.getFieldValue('NAME');
      if (funcName) {
        options.push({ text: 'Create CALL "' + funcName + '"', enabled: true,
          callback: function() { self._createCallBlock(block); } });
      }

      // ── Separator ──
      options.push({ text: '────────────', enabled: false });

      // ── List current params ──
      if (info.params.length > 0) {
        options.push({ text: 'Params: ' + info.params.join(', '), enabled: false });
      }

      // ── List current local vars ──
      if (info.locals.length > 0) {
        options.push({ text: 'Locals: ' + info.locals.join(', '), enabled: false });
      }

      // ── Add / Remove local variable ──
      options.push({ text: '+ Add local variable', enabled: true,
        callback: function() { self._addLocalVar(); } });
      if (info.locals.length > 0) {
        options.push({ text: '- Remove local variable', enabled: true,
          callback: function() { self._removeLocalVar(); } });
      }

      if (!hasAny) {
        options.push({ text: '(no parameters or local variables)', enabled: false });
      }

      Blockly.ContextMenu.show(event, options, block.RTL);
    }

    _createParamBlock(type, defaultName) {
      var block = this.getSourceBlock();
      var ws = block.workspace;
      var nb = ws.newBlock(type);
      if (defaultName) {
        // local_instance_call uses INSTANCE_NAME; get/set use PARAM_NAME
        var fieldName = (type === 'local_instance_call') ? 'INSTANCE_NAME' : 'PARAM_NAME';
        try { nb.setFieldValue(defaultName, fieldName); } catch(e) { /* dropdown may not have it yet */ }
      }
      nb.initSvg(); nb.render();
      var xy = block.getRelativeToSurfaceXY();
      nb.moveBy(xy.x + 30, xy.y + block.getHeightWidth().height + 20);
    }

    _createCallBlock(procBlock) {
      var ws = procBlock.workspace;
      var funcName = procBlock.getFieldValue('NAME');
      // Determine call type based on procedure type
      var callType = (procBlock.type === 'procedures_defreturn')
        ? 'procedures_callreturn' : 'procedures_callnoreturn';
      var nb = ws.newBlock(callType);
      nb.initSvg(); nb.render();
      // The call block auto-links to the procedure by name via Blockly internals
      // but we need to trigger the mutation to set the name
      try {
        // For Blockly's built-in call blocks, setting via setProcedureParameters_
        // or renameProcedure is the standard way. We just position it and
        // Blockly's event system will sync it.
        var mutation = document.createElement('mutation');
        mutation.setAttribute('name', funcName);
        var params = procBlock.arguments_ || [];
        for (var i = 0; i < params.length; i++) {
          var arg = document.createElement('arg');
          arg.setAttribute('name', params[i]);
          mutation.appendChild(arg);
        }
        nb.domToMutation(mutation);
      } catch(e) { /* ignore */ }
      nb.initSvg(); nb.render();
      var xy = procBlock.getRelativeToSurfaceXY();
      nb.moveBy(xy.x + 30, xy.y + procBlock.getHeightWidth().height + 20);
    }

    _addLocalVar() {
      var block = this.getSourceBlock();
      var info = getProcLocalNames(block);
      _localVarPrompt('Local variable name:', '', function(name) {
        if (!name || !name.trim()) return;
        var trimmed = name.trim();
        if (info.all.includes(trimmed)) {
          _localVarAlert('"' + trimmed + '" already exists.');
          return;
        }
        if (!block.localVars_) block.localVars_ = [];
        block.localVars_.push(trimmed);
        try {
          Blockly.Events.fire(
            new (Blockly.Events.get(Blockly.Events.BLOCK_CHANGE))(
              block, 'mutation', null, null, null));
        } catch (e) { /* ignore */ }
      });
    }

    _removeLocalVar() {
      var block = this.getSourceBlock();
      if (!block.localVars_ || block.localVars_.length === 0) return;
      _localVarPrompt('Remove which local variable?\nCurrent: ' + block.localVars_.join(', '), '', function(name) {
        if (!name || !name.trim()) return;
        var idx = block.localVars_.indexOf(name.trim());
        if (idx === -1) {
          _localVarAlert('"' + name.trim() + '" not found.');
          return;
        }
        block.localVars_.splice(idx, 1);
        try {
          Blockly.Events.fire(
            new (Blockly.Events.get(Blockly.Events.BLOCK_CHANGE))(
              block, 'mutation', null, null, null));
        } catch (e) { /* ignore */ }
      });
    }

    dispose() {
      if (this.svgRoot) {
        try { if (this.svgRoot.parentNode) this.svgRoot.parentNode.removeChild(this.svgRoot); }
        catch(e) {}
        this.svgRoot = null;
      }
    }
    applyColour() {}
    hideForInsertionMarker() { if (this.svgRoot) this.svgRoot.style.display = 'none'; }
    updateEditable() {}
    updateCollapsed() {
      if (this.svgRoot) {
        var b = this.getSourceBlock();
        this.svgRoot.style.display = (b && b.isCollapsed()) ? 'none' : '';
      }
    }
    isShownWhenCollapsed() { return false; }
    setOffsetInBlock(offset) {
      this.offsetInBlock = offset;
      if (this.svgRoot) this.svgRoot.setAttribute('transform', 'translate(' + offset.x + ',' + offset.y + ')');
    }
    onLocationChange() {}
  }

  LocalVariablesIcon.TYPE = new Blockly.icons.IconType('local_variables');
  Blockly.icons.registry.register(LocalVariablesIcon.TYPE, LocalVariablesIcon);
  _LocalVariablesIcon = LocalVariablesIcon;
  console.log('[LocalVars] LocalVariablesIcon registered');
}

// ────────────────────────────────────────────────────────────────────────────
// 6.  Workspace listener
// ────────────────────────────────────────────────────────────────────────────

function setupLocalVarIconListener() {
  var trySetup = function () {
    var ws = typeof getWorkspace === 'function' ? getWorkspace() : null;
    if (!ws || !_LocalVariablesIcon) { setTimeout(trySetup, 200); return; }

    function addIcon(block) {
      if (!block || block.isInFlyout) return;
      if (block.type !== 'procedures_defnoreturn' && block.type !== 'procedures_defreturn') return;
      if (block.getIcon(_LocalVariablesIcon.TYPE)) return;
      try { block.addIcon(new _LocalVariablesIcon(block)); } catch(e) {}
    }

    function addDefaultInputs(block) {
      if (!block || (block.type !== 'procedures_defnoreturn' && block.type !== 'procedures_defreturn')) return;
      var params = block.getVars ? block.getVars() : [];
      var paramSet = new Set(params);

      // Remove any DEFAULT_ inputs that no longer match a current param
      var allInputs = block.inputList.slice(); // copy to avoid mutation during iteration
      for (var j = 0; j < allInputs.length; j++) {
        var inp = allInputs[j];
        if (inp.name && inp.name.startsWith('DEFAULT_')) {
          var pName = inp.name.substring(8); // strip 'DEFAULT_'
          if (!paramSet.has(pName)) {
            try { block.removeInput(inp.name); } catch(e) {}
          }
        }
      }

      // Add DEFAULT_ inputs for current params that don't have one yet
      for (var i = 0; i < params.length; i++) {
        var inputName = 'DEFAULT_' + params[i];
        if (block.getInput(inputName)) continue;
        try {
          block.appendValueInput(inputName)
            .setAlign(Blockly.ALIGN_RIGHT)
            .appendField('default ' + params[i] + ':');
        } catch(e) {}
      }
    }

    // Clean up param workspace variables that already exist
    function cleanParamVars() {
      var localNames = getAllLocalScopeNames(ws);
      // We don't delete them (compose needs them), but the VARIABLE flyout hides them
    }

    ws.getAllBlocks(false).forEach(function(b) { addIcon(b); addDefaultInputs(b); });
    cleanParamVars();

    ws.addChangeListener(function(ev) {
      if (ev.type === Blockly.Events.BLOCK_CREATE) {
        var b = ws.getBlockById(ev.blockId);
        if (b) setTimeout(function() { addIcon(b); addDefaultInputs(b); }, 10);
      } else if (ev.type === Blockly.Events.BLOCK_CHANGE && ev.name === 'params') {
        var b2 = ws.getBlockById(ev.blockId);
        if (b2) setTimeout(function() { addDefaultInputs(b2); }, 50);
      }
    });

    console.log('[LocalVars] Icon listener set up');
  };
  setTimeout(trySetup, 300);
}
