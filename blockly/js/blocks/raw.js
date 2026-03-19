/**
 * Raw (As-Is) Block Definition
 * Outputs the text exactly as typed, without any wrapping or quoting.
 * Useful for kwargs keys (e.g. speed), Python literals (None, True, False),
 * or any raw Python expression.
 */

/**
 * Initialize the raw block.
 */
function initRawBlock() {
  Blockly.Blocks['raw'] = {
    init: function() {
      this.appendDummyInput()
          .appendField(new Blockly.FieldTextInput('None'), 'VALUE');
      this.setOutput(true, null);
      this.setColour(60);
      this.setTooltip('As-is: outputs the text exactly as typed, without quotes or wrapping.');
      this.setHelpUrl('');
    }
  };
}