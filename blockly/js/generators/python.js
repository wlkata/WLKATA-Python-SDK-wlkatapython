/**
 * Python Code Generators
 * Defines how custom blocks generate Python code.
 */

/**
 * Initialize Python code generators for custom blocks.
 * This function should be called after Blockly.Python is available.
 */
function initPythonGenerator() {
  if (!Blockly.Python) {
    console.error('Blockly.Python not available');
    return;
  }

  // In newer Blockly versions, generators use forBlock namespace
  // In older versions, they're directly on the generator object
  const generatorTarget = Blockly.Python.forBlock || Blockly.Python;

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
