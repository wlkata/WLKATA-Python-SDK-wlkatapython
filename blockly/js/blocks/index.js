/**
 * Blocks Module Index
 * Aggregates all custom block definitions and provides initialization.
 */

/**
 * Initialize all custom blocks.
 * This function should be called after Blockly is loaded but before workspace initialization.
 */
function initCustomBlocks() {
  initImportModuleBlock();
  initRawBlock();
  initFunctionCallBlock();
  initLibraryFunctionCallBlock();
  initInstanceFunctionCallBlock();
  initFunctionParamBlock();
  initLocalVariablesIcon();
  initProcedureOverrides();
  installFilteredVariableDropdown();
  setupLocalVarIconListener();
}
