/**
 * Custom Dialogs Module
 * Overrides Blockly's default dialogs with custom implementations for Electron.
 */

/**
 * Set up custom prompts, confirms, and alerts for Blockly.
 * This replaces the default browser dialogs with styled custom modals.
 */
function setupCustomPrompts() {
  // Override the default prompt function used by Blockly
  Blockly.dialog.setPrompt(function(message, defaultValue, callback) {
    // Create a custom modal dialog
    const modal = document.createElement('div');
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 10000;
    `;

    const dialog = document.createElement('div');
    dialog.style.cssText = `
      background: white;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
      min-width: 300px;
    `;

    const label = document.createElement('label');
    label.textContent = message;
    label.style.cssText = 'display: block; margin-bottom: 10px; font-weight: bold;';

    const input = document.createElement('input');
    input.type = 'text';
    input.value = defaultValue || '';
    input.style.cssText = `
      width: 100%;
      padding: 8px;
      border: 1px solid #ccc;
      border-radius: 4px;
      box-sizing: border-box;
      margin-bottom: 15px;
    `;

    const buttonContainer = document.createElement('div');
    buttonContainer.style.cssText = 'display: flex; justify-content: flex-end; gap: 10px;';

    const cancelBtn = document.createElement('button');
    cancelBtn.textContent = 'Cancel';
    cancelBtn.style.cssText = `
      padding: 8px 16px;
      background: #ccc;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    `;

    const okBtn = document.createElement('button');
    okBtn.textContent = 'OK';
    okBtn.style.cssText = `
      padding: 8px 16px;
      background: #2196F3;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    `;

    cancelBtn.onclick = () => {
      document.body.removeChild(modal);
      callback(null);
    };

    okBtn.onclick = () => {
      document.body.removeChild(modal);
      callback(input.value);
    };

    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        document.body.removeChild(modal);
        callback(input.value);
      }
    });

    buttonContainer.appendChild(cancelBtn);
    buttonContainer.appendChild(okBtn);
    dialog.appendChild(label);
    dialog.appendChild(input);
    dialog.appendChild(buttonContainer);
    modal.appendChild(dialog);
    document.body.appendChild(modal);

    input.focus();
    input.select();
  });

  // Also override confirm for delete operations
  Blockly.dialog.setConfirm(function(message, callback) {
    callback(confirm(message));
  });

  // Override alert
  Blockly.dialog.setAlert(function(message, callback) {
    alert(message);
    callback();
  });
}
