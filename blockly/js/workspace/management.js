/**
 * Workspace Management Module
 * Handles workspace-level operations like clearing.
 */

/**
 * Clear the workspace after user confirmation.
 * Resets the workspace to an empty state and clears the output panel.
 */
function clearWorkspace() {
  const workspace = getWorkspace ? getWorkspace() : null;
  if (!workspace) return;

  if (confirm('Are you sure you want to clear the workspace?')) {
    workspace.clear();

    if (typeof updateCodePreview === 'function') {
      updateCodePreview();
    }

    const outputContent = document.getElementById('output-content');
    if (outputContent) {
      outputContent.innerHTML = '';
    }

    // Reset toolbox to initial state
    if (workspace.initialToolbox) {
      workspace.updateToolbox(workspace.initialToolbox);
      const importedModules = getImportedModules ? getImportedModules() : null;
      if (importedModules) {
        importedModules.clear();
      }
    }
  }
}
