/**
 * Global configuration and state management for the Blockly application.
 */

// Blockly workspace reference
let workspace;

// Server URL - use 127.0.0.1 to avoid DNS resolution issues
const SERVER_URL = 'http://127.0.0.1:5000';

// Cache for function signatures to avoid repeated API calls
const functionCache = new Map();

// Cache for module function lists
const moduleFunctionCache = new Map();

// Cache for instance methods
const instanceMethodCache = new Map();

// Track imported modules to avoid duplicates in toolbox
const importedModules = new Set();

// Toolbox sync timeout reference
let syncTimeout;

/**
 * Get the current workspace instance.
 * @returns {Blockly.Workspace} The Blockly workspace
 */
function getWorkspace() {
  return workspace;
}

/**
 * Set the workspace instance.
 * @param {Blockly.Workspace} ws - The Blockly workspace to set
 */
function setWorkspace(ws) {
  workspace = ws;
}

/**
 * Get the server URL.
 * @returns {string} The server URL
 */
function getServerUrl() {
  return SERVER_URL;
}

/**
 * Get the function cache.
 * @returns {Map} The function cache map
 */
function getFunctionCache() {
  return functionCache;
}

/**
 * Get the module function cache.
 * @returns {Map} The module function cache map
 */
function getModuleFunctionCache() {
  return moduleFunctionCache;
}

/**
 * Get the instance method cache.
 * @returns {Map} The instance method cache map
 */
function getInstanceMethodCache() {
  return instanceMethodCache;
}

/**
 * Get the imported modules set.
 * @returns {Set} The imported modules set
 */
function getImportedModules() {
  return importedModules;
}

/**
 * Get the sync timeout reference.
 * @returns {number|null} The timeout ID
 */
function getSyncTimeout() {
  return syncTimeout;
}

/**
 * Set the sync timeout reference.
 * @param {number|null} timeout - The timeout ID
 */
function setSyncTimeout(timeout) {
  syncTimeout = timeout;
}
