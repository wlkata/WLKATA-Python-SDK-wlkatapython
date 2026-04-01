/**
 * Workspace Manager Module
 *
 * Manages project workspaces stored on disk.
 * A workspace is any user-chosen folder. Inside it we store:
 *   <folder>/blocks.xml       - the Blockly workspace state
 *   <folder>/functions/       - saved function JSON files
 *
 * The user picks (or creates) the folder using the native OS file picker
 * (Finder on macOS, Explorer on Windows) via Electron's dialog API.
 *
 * Uses Node.js fs/path (available because nodeIntegration is enabled).
 */

var _fs = require('fs');
var _path = require('path');
var _ipcRenderer = require('electron').ipcRenderer;

// ── State ───────────────────────────────────────────────────────

var _currentWorkspacePath = null;  // full folder path
var _currentWorkspaceName = null;  // folder basename (display name)

// ── Helpers ─────────────────────────────────────────────────────

function _ensureDir(dirPath) {
  if (!_fs.existsSync(dirPath)) {
    _fs.mkdirSync(dirPath, { recursive: true });
  }
}

function _getBlocksFile(wsPath) {
  return _path.join(wsPath, 'blocks.xml');
}

function _getFunctionsDir(wsPath) {
  return _path.join(wsPath, 'functions');
}

function _getFunctionFile(wsPath, funcName) {
  var safeName = funcName.replace(/[^a-zA-Z0-9_\-]/g, '_');
  return _path.join(_getFunctionsDir(wsPath), safeName + '.json');
}

// ── Workspace registry ──────────────────────────────────────────
//
// Two lists in localStorage:
//   recentWorkspaces  — capped at MAX_RECENT, shown in the startup dialog
//   allWorkspaces     — every workspace ever opened, used to scan saved functions

var RECENT_KEY = 'recentWorkspaces';
var ALL_KEY = 'allWorkspaces';
var MAX_RECENT = 10;

function _getRecentWorkspaces() {
  try {
    var raw = localStorage.getItem(RECENT_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) { return []; }
}

function _getAllWorkspaces() {
  try {
    var raw = localStorage.getItem(ALL_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) { return []; }
}

function _addRecentWorkspace(wsPath) {
  // Update recent list (capped)
  var recents = _getRecentWorkspaces();
  recents = recents.filter(function(r) { return r !== wsPath; });
  recents.unshift(wsPath);
  if (recents.length > MAX_RECENT) recents = recents.slice(0, MAX_RECENT);
  try { localStorage.setItem(RECENT_KEY, JSON.stringify(recents)); } catch(e) {}

  // Update all-workspaces list (uncapped, no duplicates)
  var all = _getAllWorkspaces();
  if (all.indexOf(wsPath) === -1) {
    all.push(wsPath);
    try { localStorage.setItem(ALL_KEY, JSON.stringify(all)); } catch(e) {}
  }

  console.log('[WorkspaceManager] Recent workspaces:', recents);
  console.log('[WorkspaceManager] All workspaces:', _getAllWorkspaces());
}

// ── Public API ──────────────────────────────────────────────────

function getCurrentWorkspaceName() {
  return _currentWorkspaceName;
}

function getCurrentWorkspacePath() {
  return _currentWorkspacePath;
}

/**
 * Set the current workspace by folder path.
 * Creates the functions/ subfolder if needed.
 */
function setCurrentWorkspace(wsPath) {
  _currentWorkspacePath = wsPath;
  _currentWorkspaceName = _path.basename(wsPath);
  _ensureDir(wsPath);
  _ensureDir(_getFunctionsDir(wsPath));
  _addRecentWorkspace(wsPath);

  // Update title bar
  document.title = _currentWorkspaceName + ' - WLKATA Blockly';
  // Update toolbar indicator
  var indicator = document.getElementById('workspace-name-indicator');
  if (indicator) indicator.textContent = _currentWorkspaceName;
}

// ── Block save/load ─────────────────────────────────────────────

function saveWorkspaceBlocks() {
  var ws = getWorkspace ? getWorkspace() : null;
  if (!ws || !_currentWorkspacePath) return;

  var xml = Blockly.Xml.workspaceToDom(ws);
  var xmlText = Blockly.Xml.domToText(xml);

  _ensureDir(_currentWorkspacePath);
  _fs.writeFileSync(_getBlocksFile(_currentWorkspacePath), xmlText, 'utf8');
  console.log('[WorkspaceManager] Saved blocks to:', _currentWorkspacePath);
}

function loadWorkspaceBlocks() {
  var ws = getWorkspace ? getWorkspace() : null;
  if (!ws || !_currentWorkspacePath) return;

  var filePath = _getBlocksFile(_currentWorkspacePath);
  if (!_fs.existsSync(filePath)) {
    console.log('[WorkspaceManager] No blocks file in:', _currentWorkspacePath);
    return;
  }

  try {
    var xmlText = _fs.readFileSync(filePath, 'utf8');
    var xmlDom = Blockly.utils.xml.textToDom(xmlText);
    ws.clear();
    Blockly.Xml.domToWorkspace(xmlDom, ws);
    if (typeof updateCodePreview === 'function') updateCodePreview();
    console.log('[WorkspaceManager] Loaded blocks from:', _currentWorkspacePath);
  } catch (e) {
    console.error('[WorkspaceManager] Failed to load blocks:', e);
  }
}

// ── Saved functions (per-workspace, on disk) ────────────────────

/**
 * Save a function to a workspace's functions folder.
 * @param {string} wsPath - workspace folder path (or name for display grouping)
 * @param {object} entry - { name, params, xml }
 */
function saveFunctionToWorkspace(wsPath, entry) {
  _ensureDir(_getFunctionsDir(wsPath));
  var filePath = _getFunctionFile(wsPath, entry.name);
  var data = {
    name: entry.name,
    params: entry.params || [],
    xml: entry.xml,
    timestamp: Date.now()
  };
  _fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf8');
}

function deleteFunctionFromWorkspace(wsPath, funcName) {
  var filePath = _getFunctionFile(wsPath, funcName);
  if (_fs.existsSync(filePath)) {
    _fs.unlinkSync(filePath);
  }
}

function listFunctionsInWorkspace(wsPath) {
  var dir = _getFunctionsDir(wsPath);
  if (!_fs.existsSync(dir)) return [];

  var files = _fs.readdirSync(dir).filter(function(f) {
    return f.endsWith('.json');
  });

  var results = [];
  for (var i = 0; i < files.length; i++) {
    try {
      var raw = _fs.readFileSync(_path.join(dir, files[i]), 'utf8');
      var data = JSON.parse(raw);
      results.push(data);
    } catch (e) {
      console.warn('[WorkspaceManager] Bad function file:', files[i], e);
    }
  }
  return results.sort(function(a, b) { return a.name.localeCompare(b.name); });
}

/**
 * List all saved functions across ALL known workspaces, grouped by workspace name.
 * Scans every workspace ever opened (not just the 10 most recent).
 * @returns {object} { wsDisplayName: { path: wsPath, funcs: [entries] }, ... }
 */
function listAllSavedFunctions() {
  var all = _getAllWorkspaces();
  var result = {};
  for (var i = 0; i < all.length; i++) {
    var wsPath = all[i];
    if (!_fs.existsSync(wsPath)) continue;
    var funcs = listFunctionsInWorkspace(wsPath);
    if (funcs.length > 0) {
      var displayName = _path.basename(wsPath);
      // If two folders have the same basename, use full path to disambiguate
      if (result[displayName]) {
        // Rename the existing entry to include its full path
        var existingPath = result[displayName].path;
        var renamedKey = _path.basename(existingPath) + ' (' + existingPath + ')';
        result[renamedKey] = result[displayName];
        delete result[displayName];
        // Use full path for the new entry too
        displayName = displayName + ' (' + wsPath + ')';
      }
      result[displayName] = { path: wsPath, funcs: funcs };
    }
  }
  return result;
}

// ── Native OS folder picker ─────────────────────────────────────

/**
 * Open the native OS folder picker dialog.
 * Returns a Promise that resolves with the selected folder path, or null if cancelled.
 */
function showNativeFolderPicker() {
  return _ipcRenderer.invoke('dialog:openFolder');
}

/**
 * Show the workspace selection dialog on app startup.
 * Shows recent workspaces + buttons for Open/New using native OS dialogs.
 * Returns a Promise that resolves with the chosen folder path.
 */
function showWorkspaceDialog() {
  return new Promise(function(resolve) {
    var recents = _getRecentWorkspaces();

    // Build modal overlay
    var overlay = document.createElement('div');
    overlay.id = 'workspace-dialog-overlay';
    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);display:flex;justify-content:center;align-items:center;z-index:20000;';

    var dialog = document.createElement('div');
    dialog.style.cssText = 'background:#fff;border-radius:12px;padding:30px;min-width:440px;max-width:540px;box-shadow:0 8px 32px rgba(0,0,0,0.3);';

    // Title
    var title = document.createElement('h2');
    title.textContent = 'Open Workspace';
    title.style.cssText = 'margin:0 0 6px 0;font-size:20px;color:#333;';
    dialog.appendChild(title);

    var subtitle = document.createElement('div');
    subtitle.textContent = 'Choose a folder for your project. All blocks and saved functions will be stored there.';
    subtitle.style.cssText = 'font-size:13px;color:#888;margin-bottom:20px;line-height:1.4;';
    dialog.appendChild(subtitle);

    // Action buttons: Open Folder / New Folder
    var btnRow = document.createElement('div');
    btnRow.style.cssText = 'display:flex;gap:10px;margin-bottom:20px;';

    var openBtn = document.createElement('button');
    openBtn.textContent = '\uD83D\uDCC2 Open Existing Folder';
    openBtn.style.cssText = 'flex:1;padding:12px 16px;background:#2196F3;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:14px;font-weight:500;';
    openBtn.onclick = async function() {
      var folderPath = await showNativeFolderPicker();
      if (folderPath) {
        document.body.removeChild(overlay);
        resolve(folderPath);
      }
    };
    btnRow.appendChild(openBtn);

    var newBtn = document.createElement('button');
    newBtn.textContent = '\u2795 Create New Folder';
    newBtn.style.cssText = 'flex:1;padding:12px 16px;background:#4CAF50;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:14px;font-weight:500;';
    newBtn.onclick = async function() {
      var folderPath = await _ipcRenderer.invoke('dialog:createFolder');
      if (folderPath) {
        document.body.removeChild(overlay);
        resolve(folderPath);
      }
    };
    btnRow.appendChild(newBtn);

    dialog.appendChild(btnRow);

    // Recent workspaces list
    // Filter to only existing folders
    var validRecents = recents.filter(function(r) {
      return _fs.existsSync(r);
    });

    if (validRecents.length > 0) {
      var recentLabel = document.createElement('div');
      recentLabel.textContent = 'Recent workspaces:';
      recentLabel.style.cssText = 'font-size:13px;color:#666;margin-bottom:8px;font-weight:500;';
      dialog.appendChild(recentLabel);

      var listDiv = document.createElement('div');
      listDiv.style.cssText = 'max-height:220px;overflow-y:auto;border:1px solid #eee;border-radius:8px;';

      for (var i = 0; i < validRecents.length; i++) {
        (function(wsPath) {
          var wsName = _path.basename(wsPath);
          var wsDir = _path.dirname(wsPath);

          var item = document.createElement('div');
          item.style.cssText = 'padding:10px 14px;cursor:pointer;border-bottom:1px solid #f0f0f0;display:flex;flex-direction:column;gap:2px;';
          item.onmouseenter = function() { item.style.background = '#e3f2fd'; };
          item.onmouseleave = function() { item.style.background = ''; };

          var nameSpan = document.createElement('span');
          nameSpan.textContent = wsName;
          nameSpan.style.cssText = 'font-weight:600;font-size:14px;color:#333;';
          item.appendChild(nameSpan);

          var pathSpan = document.createElement('span');
          pathSpan.textContent = wsDir;
          pathSpan.style.cssText = 'font-size:11px;color:#999;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
          item.appendChild(pathSpan);

          item.onclick = function() {
            document.body.removeChild(overlay);
            resolve(wsPath);
          };
          listDiv.appendChild(item);
        })(validRecents[i]);
      }
      dialog.appendChild(listDiv);
    }

    overlay.appendChild(dialog);
    document.body.appendChild(overlay);
  });
}

/**
 * Switch to a different workspace (save current, show dialog, reload).
 */
async function switchWorkspace() {
  // Save current workspace first
  saveWorkspaceBlocks();

  // Show dialog
  var wsPath = await showWorkspaceDialog();
  if (wsPath === _currentWorkspacePath) return; // same workspace, no-op

  setCurrentWorkspace(wsPath);

  // Clear and reload
  var ws = getWorkspace ? getWorkspace() : null;
  if (ws) {
    ws.clear();
    loadWorkspaceBlocks();
  }

  // Refresh saved functions panel
  if (typeof renderSavedFunctionsList === 'function') {
    renderSavedFunctionsList();
  }
}
