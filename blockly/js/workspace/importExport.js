/**
 * Import/Export Module
 * Handles saving and loading workspace blocks to/from XML files.
 */

/**
 * Export the current workspace blocks to an XML file.
 * Triggers a download of 'blockly_workspace.xml'.
 */
function exportBlocks() {
  const workspace = getWorkspace ? getWorkspace() : null;
  if (!workspace) return;

  const xml = Blockly.Xml.workspaceToDom(workspace);
  const xmlText = Blockly.Xml.domToText(xml);

  // Create a blob and download link
  const blob = new Blob([xmlText], { type: 'text/xml' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'blockly_workspace.xml';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Import blocks from an XML file.
 * Opens a file picker dialog and loads the selected file into the workspace.
 */
function importBlocks() {
  const workspace = getWorkspace ? getWorkspace() : null;
  if (!workspace) return;

  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.xml';
  input.onchange = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const xml = Blockly.utils.xml.textToDom(event.target.result);
          workspace.clear();
          Blockly.Xml.domToWorkspace(xml, workspace);
          if (typeof updateCodePreview === 'function') {
            updateCodePreview();
          }
        } catch (err) {
          alert('Error loading file: ' + err.message);
        }
      };
      reader.readAsText(file);
    }
  };
  input.click();
}
