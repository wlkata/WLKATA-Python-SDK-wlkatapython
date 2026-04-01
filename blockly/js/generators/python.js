/**
 * Python Code Generators
 * Defines how custom blocks generate Python code.
 */

/**
 * Initialize Python code generators for custom blocks.
 * This function should be called after Blockly.Python is available.
 */
/**
 * Generate code with block-marker comments, then strip them out.
 *
 * Uses Blockly.Python.STATEMENT_PREFIX to inject "# __BLOCK__:blockId\n"
 * before every statement.  After generation we:
 *   1. Parse the markers to build { cleanLineNum -> blockId }
 *   2. Strip the marker lines to produce clean Python code
 *
 * Returns { code: string, lineToBlock: { lineNum: blockId } }
 *   - code has NO marker comments (safe to send to the server)
 *   - lineToBlock uses 1-based line numbers of the clean code
 */
function generateCodeWithMap(workspace) {
  if (!workspace || !Blockly.Python) return { code: '', lineToBlock: {} };

  // Temporarily set STATEMENT_PREFIX to inject markers
  var oldPrefix = Blockly.Python.STATEMENT_PREFIX;
  Blockly.Python.STATEMENT_PREFIX = '# __BLOCK__:%1\n';

  var rawCode = Blockly.Python.workspaceToCode(workspace);

  // Restore
  Blockly.Python.STATEMENT_PREFIX = oldPrefix || null;

  // Parse: split into lines, build map, strip markers
  var rawLines = rawCode.split('\n');
  var cleanLines = [];
  var lineToBlock = {};
  var currentBlockId = null;

  for (var i = 0; i < rawLines.length; i++) {
    var line = rawLines[i];
    var trimmed = line.trim();

    // Check if this is a marker line
    if (trimmed.indexOf('# __BLOCK__:') === 0) {
      currentBlockId = trimmed.substring(12).replace(/^'|'$/g, ''); // strip quotes added by injectId
      continue; // don't include marker in clean code
    }

    cleanLines.push(line);
    var cleanLineNum = cleanLines.length; // 1-based

    // Bind this line to the most recent block marker
    if (currentBlockId && trimmed !== '') {
      lineToBlock[cleanLineNum] = currentBlockId;
      currentBlockId = null; // consumed — next line needs its own marker
    }
  }

  return { code: cleanLines.join('\n'), lineToBlock: lineToBlock };
}

function initPythonGenerator() {
  if (!Blockly.Python) {
    console.error('Blockly.Python not available');
    return;
  }

  // In newer Blockly versions, generators use forBlock namespace
  // In older versions, they're directly on the generator object
  const generatorTarget = Blockly.Python.forBlock || Blockly.Python;

  // ── Override Blockly.Python.finish to strip "x = None" for param/local vars ──
  // The built-in init() emits "x = None" in definitions_ for every workspace
  // variable.  We don't want any of these declarations — variables should only
  // appear when explicitly assigned by the user's blocks.
  const _origPythonFinish = Blockly.Python.finish.bind(Blockly.Python);
  Blockly.Python.finish = function(code) {
    // Remove ALL "x = None" variable declarations.
    // Blockly's init() adds "varName = None" for every workspace variable
    // into definitions_['variables'].  We don't want any of these —
    // variables get their values from actual assignment blocks.
    const defs = Blockly.Python.definitions_;
    if (defs && defs.variables !== undefined) {
      delete defs.variables;
    }
    return _origPythonFinish(code);
  };

  /**
   * Generator for raw (as-is) block.
   * Outputs the text exactly as typed, without quotes or wrapping.
   */
  generatorTarget['raw'] = function(block) {
    const value = block.getFieldValue('VALUE') || '';
    return [value, Blockly.Python.ORDER_ATOMIC];
  };

  /**
   * Generator for import_module block.
   * Produces: import <module_name>
   */
  generatorTarget['import_module'] = function(block) {
    const moduleName = block.getFieldValue('MODULE_NAME');
    return `import ${moduleName}\n`;
  };

  /**
   * Collect arguments from a block's parameters, handling dynamic *args/**kwargs
   * value-input slots.  Returns an array of argument strings.
   */
  function collectArgs(block, funcInfo) {
    const args = [];

    for (const param of funcInfo.parameters) {
      if (param.is_varargs) {
        // Collect connected block values from VARARG value-input slots
        const indices = getVarargIndices(block, param.name);
        for (const idx of indices) {
          const val = Blockly.Python.valueToCode(
            block, `VARARG_${param.name}_${idx}`, Blockly.Python.ORDER_NONE);
          if (val) {
            args.push(val);
          }
        }
      } else if (param.is_varkwargs) {
        // Collect key=value pairs: both key and value are value inputs
        const indices = getVarkwIndices(block, param.name);
        for (const idx of indices) {
          const key = Blockly.Python.valueToCode(
            block, `VARKW_KEY_${param.name}_${idx}`, Blockly.Python.ORDER_NONE);
          const val = Blockly.Python.valueToCode(
            block, `VARKW_VAL_${param.name}_${idx}`, Blockly.Python.ORDER_NONE);
          if (key && val) {
            args.push(`${key}=${val}`);
          }
        }
      } else {
        const inputName = `PARAM_${param.name}`;
        const inputValue = Blockly.Python.valueToCode(block, inputName, Blockly.Python.ORDER_NONE);

        if (inputValue) {
          if (param.is_keyword_only || param.has_default) {
            args.push(`${param.name}=${inputValue}`);
          } else {
            args.push(inputValue);
          }
        } else if (!param.has_default) {
          // Required parameter without value - use None as placeholder
          args.push('None');
        }
      }
    }

    return args;
  }

  /**
   * Generator for function_param_get block.
   * Simply emits the parameter name as a Python identifier.
   */
  generatorTarget['function_param_get'] = function(block) {
    const paramName = block.getFieldValue('PARAM_NAME');
    if (!paramName || paramName === '__NONE__') {
      return ['None', Blockly.Python.ORDER_ATOMIC];
    }
    return [paramName, Blockly.Python.ORDER_ATOMIC];
  };

  /**
   * Generator for function_param_set block.
   * Produces: param_name = <value>
   */
  generatorTarget['function_param_set'] = function(block) {
    const paramName = block.getFieldValue('PARAM_NAME');
    if (!paramName || paramName === '__NONE__') return '';
    const value = Blockly.Python.valueToCode(block, 'VALUE', Blockly.Python.ORDER_NONE) || 'None';
    return paramName + ' = ' + value + '\n';
  };

  /**
   * Generator for local_instance_call block.
   * Produces: localvar.method(arg1, arg2, ...)
   */
  generatorTarget['local_instance_call'] = function(block) {
    const instanceName = block.getFieldValue('INSTANCE_NAME');
    const methodName = block.getFieldValue('METHOD_NAME');
    const isStatement = !!(block.previousConnection || block.nextConnection);

    if (!instanceName || instanceName === '__NONE__' || !methodName || methodName === '...') {
      return isStatement ? '' : ['None', Blockly.Python.ORDER_ATOMIC];
    }

    const callTarget = instanceName + '.' + methodName;
    const funcInfo = block.functionInfo_;

    if (!funcInfo || !funcInfo.parameters || funcInfo.parameters.length === 0) {
      const code = callTarget + '()';
      if (isStatement) return code + '\n';
      return [code, Blockly.Python.ORDER_FUNCTION_CALL];
    }

    const args = collectArgs(block, funcInfo);
    const code = callTarget + '(' + args.join(', ') + ')';
    if (isStatement) return code + '\n';
    return [code, Blockly.Python.ORDER_FUNCTION_CALL];
  };

  /**
   * Override the built-in procedure definition generators so that
   * parameters are NOT declared as "global" inside the function body.
   * The built-in generator adds "global x, y" for every workspace variable
   * that isn't a parameter.  Since we removed parameter variables from the
   * workspace, the built-in generator would treat them as unknown.  We
   * override to produce clean Python: def func(a, b): ...
   */
  (function overrideProcedureGenerators() {
    const procTypes = ['procedures_defnoreturn', 'procedures_defreturn'];
    for (const procType of procTypes) {
      generatorTarget[procType] = function(block) {
        const funcName = Blockly.Python.getProcedureName(
          block.getFieldValue('NAME'));

        // Build parameter list from the block's arguments_,
        // including default values from DEFAULT_<paramName> inputs.
        const params = [];
        const paramVars = block.getVars ? block.getVars() : [];
        for (let i = 0; i < paramVars.length; i++) {
          const pName = Blockly.Python.getVariableName
            ? Blockly.Python.getVariableName(paramVars[i])
            : paramVars[i];
          // Check for a DEFAULT_<paramName> input with a connected block
          const defaultInput = block.getInput('DEFAULT_' + paramVars[i]);
          if (defaultInput) {
            const defaultVal = Blockly.Python.valueToCode(
              block, 'DEFAULT_' + paramVars[i], Blockly.Python.ORDER_NONE);
            if (defaultVal) {
              params.push(pName + '=' + defaultVal);
              continue;
            }
          }
          params.push(pName);
        }

        // No global declarations in custom functions — the user wants
        // simplified code without any "global ..." lines.
        const globalDecl = '';

        // Statement prefix / suffix
        let prefix = '';
        if (Blockly.Python.STATEMENT_PREFIX) {
          prefix += Blockly.Python.injectId(Blockly.Python.STATEMENT_PREFIX, block);
        }
        if (Blockly.Python.STATEMENT_SUFFIX) {
          prefix += Blockly.Python.injectId(Blockly.Python.STATEMENT_SUFFIX, block);
        }
        if (prefix) {
          prefix = Blockly.Python.prefixLines(prefix, Blockly.Python.INDENT);
        }

        // Infinite loop trap
        let loopTrap = '';
        if (Blockly.Python.INFINITE_LOOP_TRAP) {
          loopTrap = Blockly.Python.prefixLines(
            Blockly.Python.injectId(Blockly.Python.INFINITE_LOOP_TRAP, block),
            Blockly.Python.INDENT);
        }

        // Body
        let body = '';
        if (block.getInput('STACK')) {
          body = Blockly.Python.statementToCode(block, 'STACK');
        }

        // Return value (for procedures_defreturn)
        let returnVal = '';
        if (block.getInput('RETURN')) {
          returnVal = Blockly.Python.valueToCode(block, 'RETURN',
            Blockly.Python.ORDER_NONE) || '';
        }

        let returnSuffix = '';
        if (body && returnVal) {
          returnSuffix = prefix;
        }
        if (returnVal) {
          returnVal = Blockly.Python.INDENT + 'return ' + returnVal + '\n';
        } else if (!body) {
          body = Blockly.Python.PASS || '  pass\n';
        }

        const code = 'def ' + funcName + '(' + params.join(', ') + '):\n' +
          globalDecl + prefix + loopTrap + body + returnSuffix + returnVal;

        const scrubbed = Blockly.Python.scrub_(block, code);
        Blockly.Python.definitions_['%' + funcName] = scrubbed;
        return null;
      };
    }
  })();

  /**
   * Generator for function_call block.
   * Produces: func_name(arg1, arg2, ...)
   */
  generatorTarget['function_call'] = function(block) {
    const funcName = block.getFieldValue('FUNC_NAME');
    const funcInfo = block.functionInfo_;

    if (!funcInfo || !funcInfo.parameters || funcInfo.parameters.length === 0) {
      // No parameters - just call the function
      return [`${funcName}()`, Blockly.Python.ORDER_FUNCTION_CALL];
    }

    const args = collectArgs(block, funcInfo);

    const code = `${funcName}(${args.join(', ')})`;
    if (block.isStatement_) {
      return code + '\n';
    }
    return [code, Blockly.Python.ORDER_FUNCTION_CALL];
  };

  /**
   * Generator for library_function_call block.
   * Reuses the same logic as function_call.
   */
  generatorTarget['library_function_call'] = generatorTarget['function_call'];

  /**
   * Generator for instance_function_call block.
   * Produces: instance.method(arg1, arg2, ...)
   */
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

    const args = collectArgs(block, funcInfo);

    const code = `${callTarget}(${args.join(', ')})`;
    if (isStatement) {
      return code + '\n';
    }
    return [code, Blockly.Python.ORDER_FUNCTION_CALL];
  };
}
