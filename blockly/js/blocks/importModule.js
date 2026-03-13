/**
 * Import Module Block Definition
 * Allows importing Python modules and adding their functions to the toolbox.
 */

/**
 * Initialize the import_module block.
 */
function initImportModuleBlock() {
  Blockly.Blocks['import_module'] = {
    init: function() {
      const block = this;
      const validator = function(newValue) {
        if (block.importTimeout_) {
          clearTimeout(block.importTimeout_);
        }
        block.importTimeout_ = setTimeout(() => {
          if (typeof syncToolboxWithImports === 'function') {
            syncToolboxWithImports();
          }
        }, 500);
        return newValue;
      };

      this.appendDummyInput()
          .appendField("import")
          .appendField(new Blockly.FieldTextInput("math", validator), "MODULE_NAME");
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setColour(230);
      this.setTooltip("Import a Python library and add its functions to the toolbox.");
      this.setHelpUrl("");
    }
  };
}
