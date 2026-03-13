/**
 * Toolbox Module
 * Manages the Blockly toolbox configuration and dynamic updates.
 */

/**
 * Get the initial toolbox configuration.
 * @returns {Object} The toolbox configuration object
 */
function getToolboxConfig() {
  return {
    kind: 'categoryToolbox',
    contents: [
      {
        kind: 'category',
        name: 'Logic',
        colour: '#5C81A6',
        contents: [
          { kind: 'block', type: 'controls_if' },
          { kind: 'block', type: 'logic_compare' },
          { kind: 'block', type: 'logic_operation' },
          { kind: 'block', type: 'logic_negate' },
          { kind: 'block', type: 'logic_boolean' },
        ],
      },
      {
        kind: 'category',
        name: 'Loops',
        colour: '#5CA65C',
        contents: [
          { kind: 'block', type: 'controls_repeat_ext' },
          { kind: 'block', type: 'controls_whileUntil' },
          { kind: 'block', type: 'controls_for' },
          { kind: 'block', type: 'controls_forEach' },
          { kind: 'block', type: 'controls_flow_statements' },
        ],
      },
      {
        kind: 'category',
        name: 'Math',
        colour: '#5C68A6',
        contents: [
          { kind: 'block', type: 'math_number' },
          { kind: 'block', type: 'math_arithmetic' },
          { kind: 'block', type: 'math_single' },
          { kind: 'block', type: 'math_trig' },
          { kind: 'block', type: 'math_constant' },
          { kind: 'block', type: 'math_number_property' },
          { kind: 'block', type: 'math_round' },
          { kind: 'block', type: 'math_on_list' },
          { kind: 'block', type: 'math_modulo' },
          { kind: 'block', type: 'math_constrain' },
          { kind: 'block', type: 'math_random_int' },
          { kind: 'block', type: 'math_random_float' },
        ],
      },
      {
        kind: 'category',
        name: 'Text',
        colour: '#A65C81',
        contents: [
          { kind: 'block', type: 'text' },
          { kind: 'block', type: 'text_join' },
          { kind: 'block', type: 'text_append' },
          { kind: 'block', type: 'text_length' },
          { kind: 'block', type: 'text_isEmpty' },
          { kind: 'block', type: 'text_indexOf' },
          { kind: 'block', type: 'text_charAt' },
          { kind: 'block', type: 'text_getSubstring' },
          { kind: 'block', type: 'text_changeCase' },
          { kind: 'block', type: 'text_trim' },
          { kind: 'block', type: 'text_print' },
          { kind: 'block', type: 'text_prompt_ext' },
        ],
      },
      {
        kind: 'category',
        name: 'Lists',
        colour: '#A65C5C',
        contents: [
          { kind: 'block', type: 'lists_create_with' },
          { kind: 'block', type: 'lists_create_with' },
          { kind: 'block', type: 'lists_repeat' },
          { kind: 'block', type: 'lists_length' },
          { kind: 'block', type: 'lists_isEmpty' },
          { kind: 'block', type: 'lists_indexOf' },
          { kind: 'block', type: 'lists_getIndex' },
          { kind: 'block', type: 'lists_setIndex' },
          { kind: 'block', type: 'lists_getSublist' },
          { kind: 'block', type: 'lists_split' },
          { kind: 'block', type: 'lists_sort' },
        ],
      },
      {
        kind: 'category',
        name: 'Variables',
        colour: '#A65CA6',
        custom: 'VARIABLE',
      },
      {
        kind: 'category',
        name: 'Functions',
        colour: '#9A5CA6',
        custom: 'PROCEDURE',
      },
      {
        kind: 'category',
        name: 'Python',
        colour: '#4B8BBE',
        contents: [
          { kind: 'block', type: 'import_module' },
          { kind: 'block', type: 'function_call' },
          { kind: 'block', type: 'instance_function_call' },
        ],
      },
    ],
  };
}

/**
 * Synchronizes the toolbox with the current import blocks in the workspace.
 * Adds categories for imported modules and removes ones that are no longer present.
 */
async function syncToolboxWithImports() {
  const syncTimeout = getSyncTimeout ? getSyncTimeout() : null;
  if (syncTimeout) {
    clearTimeout(syncTimeout);
  }

  const newTimeout = setTimeout(async () => {
    const workspace = getWorkspace ? getWorkspace() : null;
    if (!workspace) return;

    const importedModules = getImportedModules ? getImportedModules() : new Set();
    const moduleFunctionCache = getModuleFunctionCache ? getModuleFunctionCache() : new Map();

    const blocks = workspace.getAllBlocks(false);
    const currentImports = new Set();

    for (const block of blocks) {
      if (block.type === 'import_module') {
        const moduleName = block.getFieldValue('MODULE_NAME');
        if (moduleName) {
          currentImports.add(moduleName);
        }
      }
    }

    // Check for modules to add
    for (const moduleName of currentImports) {
      if (!importedModules.has(moduleName)) {
        await loadModuleInfo(moduleName);
      }
    }

    // Check for modules to remove
    let changed = false;
    for (const moduleName of importedModules) {
      if (!currentImports.has(moduleName)) {
        importedModules.delete(moduleName);
        changed = true;
      }
    }

    if (changed || [...currentImports].some(m => !isModuleInToolbox(m))) {
      updateToolboxDisplay();
    }
  }, 100);

  if (setSyncTimeout) {
    setSyncTimeout(newTimeout);
  }
}

/**
 * Load module information from the server.
 * @param {string} moduleName - The name of the module to load
 */
async function loadModuleInfo(moduleName) {
  const moduleFunctionCache = getModuleFunctionCache ? getModuleFunctionCache() : new Map();
  const importedModules = getImportedModules ? getImportedModules() : new Set();
  const serverUrl = getServerUrl ? getServerUrl() : 'http://127.0.0.1:5000';

  if (moduleFunctionCache.has(moduleName)) {
    importedModules.add(moduleName);
    return;
  }

  try {
    const response = await fetch(`${serverUrl}/import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ module: moduleName })
    });

    const info = await response.json();
    if (info.success) {
      moduleFunctionCache.set(moduleName, info.functions);
      importedModules.add(moduleName);
    }
  } catch (error) {
    console.error(`Error loading module ${moduleName}:`, error);
  }
}

/**
 * Check if a module is already in the toolbox.
 * @param {string} moduleName - The module name to check
 * @returns {boolean} True if the module is in the toolbox
 */
function isModuleInToolbox(moduleName) {
  const workspace = getWorkspace ? getWorkspace() : null;
  if (!workspace) return false;

  const currentToolbox = workspace.options.languageTree;
  return currentToolbox.contents.some(cat => cat.kind === 'category' && cat.name === moduleName);
}

/**
 * Update the toolbox display with current imported modules.
 */
function updateToolboxDisplay() {
  const workspace = getWorkspace ? getWorkspace() : null;
  if (!workspace || !workspace.initialToolbox) return;

  const importedModules = getImportedModules ? getImportedModules() : new Set();
  const moduleFunctionCache = getModuleFunctionCache ? getModuleFunctionCache() : new Map();

  const toolbox = JSON.parse(JSON.stringify(workspace.initialToolbox));

  for (const moduleName of importedModules) {
    const functions = moduleFunctionCache.get(moduleName);
    if (functions) {
      toolbox.contents.push({
        kind: 'category',
        name: moduleName,
        colour: '#4B8BBE',
        contents: [
          {
            kind: 'block',
            type: 'library_function_call',
            extraState: {
              'func_name': functions[0],
              'options': functions
            }
          }
        ]
      });
    }
  }

  workspace.updateToolbox(toolbox);
}
