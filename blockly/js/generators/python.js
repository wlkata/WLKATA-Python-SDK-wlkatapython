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
   * Generator for import_module block.
   * Produces: import <module_name>
   */
  generatorTarget['import_module'] = function(block) {
    const moduleName = block.getFieldValue('MODULE_NAME');
    return `import ${moduleName}\n`;
  };

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
