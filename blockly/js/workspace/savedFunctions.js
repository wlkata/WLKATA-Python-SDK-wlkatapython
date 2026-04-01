/**
 * Saved Functions Module
 *
 * Lets users save function definitions (procedures_defreturn /
 * procedures_defnoreturn) to a per-workspace library on disk.
 * The "Saved Functions" tab groups functions by workspace with
 * fold/expand, current workspace always on top.
 */

// Track which workspace groups are collapsed (by name)
var _collapsedGroups = {};

// ── Public API ──────────────────────────────────────────────────

/**
 * Save a procedure definition block to the current workspace's library.
 */
function saveFunction(procBlock) {
  if (!procBlock) return;
  var funcName = procBlock.getFieldValue('NAME');
  if (!funcName) return;
  var wsPath = getCurrentWorkspacePath ? getCurrentWorkspacePath() : null;
  var wsName = getCurrentWorkspaceName ? getCurrentWorkspaceName() : null;
  if (!wsPath) { console.warn('[SavedFunctions] No active workspace'); return; }

  // Serialize the block tree
  var xml = Blockly.Xml.blockToDom(procBlock, true);
  var wrapper = document.createElement('xml');
  wrapper.setAttribute('xmlns', 'https://developers.google.com/blockly/xml');
  wrapper.appendChild(xml);
  var xmlText = Blockly.Xml.domToText(wrapper);

  var entry = {
    name: funcName,
    params: (procBlock.arguments_ || []).slice(),
    xml: xmlText
  };

  saveFunctionToWorkspace(wsPath, entry);
  renderSavedFunctionsList();
  console.log('[SavedFunctions] Saved "' + funcName + '" to workspace "' + wsName + '"');
}

/**
 * Delete a saved function.
 * @param {string} wsPath - workspace folder path
 * @param {string} funcName
 */
function deleteSavedFunction(wsPath, funcName) {
  deleteFunctionFromWorkspace(wsPath, funcName);
  renderSavedFunctionsList();
}

/**
 * Get all procedure names currently in the workspace.
 * @returns {string[]}
 */
function _getExistingProcedureNames(workspace) {
  var names = [];
  var blocks = workspace.getAllBlocks(false);
  for (var i = 0; i < blocks.length; i++) {
    if (blocks[i].type === 'procedures_defnoreturn' ||
        blocks[i].type === 'procedures_defreturn') {
      var name = blocks[i].getFieldValue('NAME');
      if (name) names.push(name);
    }
  }
  return names;
}

/**
 * Show a conflict resolution dialog when a function with the same name exists.
 * Returns a Promise that resolves with:
 *   { action: 'rename-new', newName: '...' }
 *   { action: 'rename-existing', newName: '...' }
 *   { action: 'cancel' }
 */
function _showConflictDialog(funcName, existingNames) {
  return new Promise(function(resolve) {
    var overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:flex;justify-content:center;align-items:center;z-index:20000;';

    var dialog = document.createElement('div');
    dialog.style.cssText = 'background:#fff;border-radius:10px;padding:24px;min-width:400px;max-width:480px;box-shadow:0 6px 24px rgba(0,0,0,0.3);';

    // Warning icon + title
    var title = document.createElement('div');
    title.style.cssText = 'font-size:16px;font-weight:600;color:#e65100;margin-bottom:12px;';
    title.textContent = '\u26A0\uFE0F Function "' + funcName + '" already exists';
    dialog.appendChild(title);

    var desc = document.createElement('div');
    desc.style.cssText = 'font-size:13px;color:#666;margin-bottom:16px;line-height:1.5;';
    desc.textContent = 'A function with this name is already in the workspace. Choose how to resolve the conflict:';
    dialog.appendChild(desc);

    // Helper: validate name against existing procedure names
    function _validateName(input, errorEl) {
      var name = input.value.trim();
      if (!name) {
        errorEl.textContent = 'Name cannot be empty.';
        errorEl.style.display = 'block';
        input.style.borderColor = '#f44336';
        return false;
      }
      if (existingNames.indexOf(name) >= 0) {
        errorEl.textContent = '"' + name + '" already exists. Please choose a different name.';
        errorEl.style.display = 'block';
        input.style.borderColor = '#f44336';
        return false;
      }
      errorEl.style.display = 'none';
      input.style.borderColor = '#ccc';
      return true;
    }

    var errorStyle = 'display:none;font-size:11px;color:#d32f2f;margin-top:4px;';

    // Option 1: Rename the incoming function
    var section1 = document.createElement('div');
    section1.style.cssText = 'margin-bottom:12px;padding:12px;background:#e3f2fd;border-radius:6px;';

    var label1 = document.createElement('div');
    label1.style.cssText = 'font-size:13px;font-weight:500;color:#1565c0;margin-bottom:6px;';
    label1.textContent = 'Rename the new function:';
    section1.appendChild(label1);

    var row1 = document.createElement('div');
    row1.style.cssText = 'display:flex;gap:8px;';

    var input1 = document.createElement('input');
    input1.type = 'text';
    input1.value = funcName + '_copy';
    input1.style.cssText = 'flex:1;padding:6px 10px;border:1px solid #ccc;border-radius:4px;font-size:13px;';
    row1.appendChild(input1);

    var btn1 = document.createElement('button');
    btn1.textContent = 'Add with this name';
    btn1.style.cssText = 'padding:6px 14px;background:#1976D2;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;white-space:nowrap;';

    var error1 = document.createElement('div');
    error1.style.cssText = errorStyle;

    btn1.onclick = function() {
      if (!_validateName(input1, error1)) { input1.focus(); return; }
      document.body.removeChild(overlay);
      resolve({ action: 'rename-new', newName: input1.value.trim() });
    };
    row1.appendChild(btn1);
    section1.appendChild(row1);
    section1.appendChild(error1);

    // Clear error on typing
    input1.addEventListener('input', function() {
      error1.style.display = 'none';
      input1.style.borderColor = '#ccc';
    });

    dialog.appendChild(section1);

    // Option 2: Rename the existing function
    var section2 = document.createElement('div');
    section2.style.cssText = 'margin-bottom:12px;padding:12px;background:#fff3e0;border-radius:6px;';

    var label2 = document.createElement('div');
    label2.style.cssText = 'font-size:13px;font-weight:500;color:#e65100;margin-bottom:6px;';
    label2.textContent = 'Rename the existing function in workspace:';
    section2.appendChild(label2);

    var row2 = document.createElement('div');
    row2.style.cssText = 'display:flex;gap:8px;';

    var input2 = document.createElement('input');
    input2.type = 'text';
    input2.value = funcName + '_old';
    input2.style.cssText = 'flex:1;padding:6px 10px;border:1px solid #ccc;border-radius:4px;font-size:13px;';
    row2.appendChild(input2);

    var btn2 = document.createElement('button');
    btn2.textContent = 'Rename existing';
    btn2.style.cssText = 'padding:6px 14px;background:#e65100;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;white-space:nowrap;';

    var error2 = document.createElement('div');
    error2.style.cssText = errorStyle;

    btn2.onclick = function() {
      // For "rename existing", the new name must not conflict with OTHER existing names
      // (excluding the one being renamed, since it will take the new name)
      var nameToCheck = input2.value.trim();
      if (!nameToCheck) {
        error2.textContent = 'Name cannot be empty.';
        error2.style.display = 'block';
        input2.style.borderColor = '#f44336';
        input2.focus();
        return;
      }
      var otherNames = existingNames.filter(function(n) { return n !== funcName; });
      if (otherNames.indexOf(nameToCheck) >= 0 || nameToCheck === funcName) {
        error2.textContent = '"' + nameToCheck + '" already exists. Please choose a different name.';
        error2.style.display = 'block';
        input2.style.borderColor = '#f44336';
        input2.focus();
        return;
      }
      document.body.removeChild(overlay);
      resolve({ action: 'rename-existing', newName: nameToCheck });
    };
    row2.appendChild(btn2);
    section2.appendChild(row2);
    section2.appendChild(error2);

    // Clear error on typing
    input2.addEventListener('input', function() {
      error2.style.display = 'none';
      input2.style.borderColor = '#ccc';
    });

    dialog.appendChild(section2);

    // Cancel button
    var cancelRow = document.createElement('div');
    cancelRow.style.cssText = 'text-align:right;margin-top:8px;';

    var cancelBtn = document.createElement('button');
    cancelBtn.textContent = 'Cancel';
    cancelBtn.style.cssText = 'padding:8px 20px;background:#eee;color:#555;border:1px solid #ccc;border-radius:4px;cursor:pointer;font-size:13px;';
    cancelBtn.onclick = function() {
      document.body.removeChild(overlay);
      resolve({ action: 'cancel' });
    };
    cancelRow.appendChild(cancelBtn);
    dialog.appendChild(cancelRow);

    // Enter key on inputs
    input1.addEventListener('keypress', function(e) { if (e.key === 'Enter') btn1.click(); });
    input2.addEventListener('keypress', function(e) { if (e.key === 'Enter') btn2.click(); });

    overlay.appendChild(dialog);
    document.body.appendChild(overlay);
    input1.focus();
    input1.select();
  });
}

/**
 * Insert a saved function block into the workspace, positioning it at center.
 * @param {object} entry - { name, params, xml }
 * @param {string} [overrideName] - if provided, rename the function after inserting
 */
function _insertFunctionBlock(entry, overrideName) {
  var workspace = getWorkspace ? getWorkspace() : null;
  if (!workspace) return;

  try {
    var xmlDom = Blockly.utils.xml.textToDom(entry.xml);

    // If we need to rename, modify the XML before inserting so Blockly
    // doesn't auto-rename with "2" suffix
    if (overrideName && overrideName !== entry.name) {
      var blockEl = xmlDom.querySelector('block[type="procedures_defreturn"], block[type="procedures_defnoreturn"]');
      if (blockEl) {
        var fields = blockEl.querySelectorAll('field[name="NAME"]');
        for (var i = 0; i < fields.length; i++) {
          fields[i].textContent = overrideName;
        }
      }
    }

    var ids = Blockly.Xml.domToWorkspace(xmlDom, workspace);
    if (ids && ids.length > 0) {
      var block = workspace.getBlockById(ids[0]);
      if (block) {
        var metrics = workspace.getMetrics();
        var cx = (metrics.viewLeft + metrics.viewWidth / 2) / workspace.scale;
        var cy = (metrics.viewTop + metrics.viewHeight / 2) / workspace.scale;
        block.moveTo(new Blockly.utils.Coordinate(cx - 100, cy - 50));
      }
    }
    if (typeof updateCodePreview === 'function') updateCodePreview();
  } catch (e) {
    console.error('[SavedFunctions] Failed to insert block:', e);
  }
}

/**
 * Load a saved function into the Blockly workspace.
 * If a function with the same name already exists, shows a conflict dialog.
 * @param {string} wsPath - workspace folder path
 * @param {string} funcName
 */
async function loadSavedFunction(wsPath, funcName) {
  var workspace = getWorkspace ? getWorkspace() : null;
  if (!workspace) return;

  var funcs = listFunctionsInWorkspace(wsPath);
  var entry = null;
  for (var i = 0; i < funcs.length; i++) {
    if (funcs[i].name === funcName) { entry = funcs[i]; break; }
  }
  if (!entry) return;

  // Check for name conflict
  var existingNames = _getExistingProcedureNames(workspace);
  if (existingNames.indexOf(funcName) >= 0) {
    // Conflict — show dialog
    var result = await _showConflictDialog(funcName, existingNames);

    if (result.action === 'cancel') {
      return;
    } else if (result.action === 'rename-new') {
      // Insert the new function with a different name
      _insertFunctionBlock(entry, result.newName);
    } else if (result.action === 'rename-existing') {
      // Rename the existing block in the workspace first
      var blocks = workspace.getAllBlocks(false);
      for (var b = 0; b < blocks.length; b++) {
        if ((blocks[b].type === 'procedures_defnoreturn' || blocks[b].type === 'procedures_defreturn') &&
            blocks[b].getFieldValue('NAME') === funcName) {
          blocks[b].setFieldValue(result.newName, 'NAME');
          break;
        }
      }
      // Now insert the new function with its original name
      _insertFunctionBlock(entry);
    }
  } else {
    // No conflict — insert directly
    _insertFunctionBlock(entry);
  }
}

// ── UI Rendering ────────────────────────────────────────────────

function renderSavedFunctionsList() {
  var container = document.getElementById('saved-functions-list');
  if (!container) return;
  container.innerHTML = '';

  var allFuncs = listAllSavedFunctions();
  // allFuncs = { displayName: { path: wsPath, funcs: [entries] }, ... }
  var wsNames = Object.keys(allFuncs);
  var currentWs = getCurrentWorkspaceName ? getCurrentWorkspaceName() : null;

  if (wsNames.length === 0) {
    container.innerHTML =
      '<div class="saved-func-empty">' +
      '<div style="font-size:24px;margin-bottom:8px;">\uD83D\uDCE6</div>' +
      'No saved functions yet.<br>' +
      'Right-click a function definition block<br>and choose "Save to Library".' +
      '</div>';
    return;
  }

  // Sort: current workspace first, then alphabetical
  wsNames.sort(function(a, b) {
    if (a === currentWs) return -1;
    if (b === currentWs) return 1;
    return a.localeCompare(b);
  });

  for (var w = 0; w < wsNames.length; w++) {
    var wsName = wsNames[w];
    var wsInfo = allFuncs[wsName];
    var wsPath = wsInfo.path;
    var funcs = wsInfo.funcs;
    var isCurrent = wsName === currentWs;
    var isCollapsed = !!_collapsedGroups[wsName];

    var group = document.createElement('div');
    group.className = 'saved-func-group';

    // Group header (clickable to fold/expand)
    var header = document.createElement('div');
    header.className = 'saved-func-group-header' + (isCurrent ? ' current' : '');
    header.innerHTML =
      '<span class="group-toggle">' + (isCollapsed ? '\u25B6' : '\u25BC') + '</span>' +
      '<span class="group-name">' + _escHtml(wsName) + '</span>' +
      (isCurrent ? '<span class="group-badge">current</span>' : '') +
      '<span class="group-count">' + funcs.length + '</span>';

    (function(name) {
      header.onclick = function() {
        _collapsedGroups[name] = !_collapsedGroups[name];
        renderSavedFunctionsList();
      };
    })(wsName);
    group.appendChild(header);

    // Function cards (hidden if collapsed)
    if (!isCollapsed) {
      var cardsDiv = document.createElement('div');
      cardsDiv.className = 'saved-func-group-cards';
      for (var f = 0; f < funcs.length; f++) {
        cardsDiv.appendChild(_createFunctionCard(wsPath, funcs[f]));
      }
      group.appendChild(cardsDiv);
    }

    container.appendChild(group);
  }
}

function _createFunctionCard(wsPath, entry) {
  var card = document.createElement('div');
  card.className = 'saved-func-card';

  var nameEl = document.createElement('div');
  nameEl.className = 'func-name';
  nameEl.textContent = entry.name;
  card.appendChild(nameEl);

  var paramsEl = document.createElement('div');
  paramsEl.className = 'func-params';
  paramsEl.textContent = entry.params && entry.params.length > 0
    ? '(' + entry.params.join(', ') + ')'
    : '(no parameters)';
  card.appendChild(paramsEl);

  var actions = document.createElement('div');
  actions.className = 'func-actions';

  var loadBtn = document.createElement('button');
  loadBtn.textContent = '+ Add';
  loadBtn.title = 'Add to workspace';
  loadBtn.onclick = function(e) {
    e.stopPropagation();
    loadSavedFunction(wsPath, entry.name);
  };
  actions.appendChild(loadBtn);

  var deleteBtn = document.createElement('button');
  deleteBtn.className = 'delete-btn';
  deleteBtn.textContent = '\u2715';
  deleteBtn.title = 'Delete from library';
  deleteBtn.onclick = function(e) {
    e.stopPropagation();
    if (confirm('Delete saved function "' + entry.name + '"?')) {
      deleteSavedFunction(wsPath, entry.name);
    }
  };
  actions.appendChild(deleteBtn);

  card.appendChild(actions);

  // Drag support
  card.draggable = true;
  card.addEventListener('dragstart', function(e) {
    e.dataTransfer.setData('application/x-saved-func', JSON.stringify({ ws: wsPath, name: entry.name }));
    e.dataTransfer.effectAllowed = 'copy';
  });

  card.addEventListener('dblclick', function() {
    loadSavedFunction(wsPath, entry.name);
  });

  return card;
}

function _escHtml(str) {
  var d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

// ── Context Menu Integration ────────────────────────────────────

function initSavedFunctionsContextMenu() {
  var PROC_TYPES = ['procedures_defnoreturn', 'procedures_defreturn'];
  for (var i = 0; i < PROC_TYPES.length; i++) {
    var orig = Blockly.Blocks[PROC_TYPES[i]];
    if (!orig) continue;

    (function(blockDef) {
      var origCtx = blockDef.customContextMenu;
      blockDef.customContextMenu = function(options) {
        if (origCtx) origCtx.call(this, options);
        var block = this;
        options.push({
          text: 'Save to Library',
          enabled: true,
          callback: function() { saveFunction(block); }
        });
      };
    })(orig);
  }
}

// ── Drop zone on workspace ──────────────────────────────────────

function initSavedFunctionsDragDrop() {
  var blocklyDiv = document.getElementById('blocklyDiv');
  if (!blocklyDiv) return;

  blocklyDiv.addEventListener('dragover', function(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  });

  blocklyDiv.addEventListener('drop', function(e) {
    e.preventDefault();
    var raw = e.dataTransfer.getData('application/x-saved-func');
    if (raw) {
      try {
        var data = JSON.parse(raw);
        loadSavedFunction(data.ws, data.name);
      } catch(err) {}
    }
  });
}

// ── Panel tab switching ─────────────────────────────────────────

function initOutputPanelTabs() {
  var panelBtns = document.querySelectorAll('#output-tabs .panel-tab-btn');
  panelBtns.forEach(function(btn) {
    btn.addEventListener('click', function() {
      var panel = btn.dataset.panel;
      panelBtns.forEach(function(b) { b.classList.remove('active'); });
      btn.classList.add('active');
      var contents = document.querySelectorAll('#output-panel .panel-tab-content');
      contents.forEach(function(pc) { pc.classList.remove('active'); });
      var target = document.getElementById('panel-content-' + panel);
      if (target) target.classList.add('active');
    });
  });
}

// ── Initialization ──────────────────────────────────────────────

function initSavedFunctions() {
  initSavedFunctionsContextMenu();
  initOutputPanelTabs();
  renderSavedFunctionsList();
  setTimeout(function() { initSavedFunctionsDragDrop(); }, 500);
}
