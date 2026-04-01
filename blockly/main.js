const { app, BrowserWindow, ipcMain, shell, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const net = require('net');
const fs = require('fs');

// Collect startup logs before the window is created so we can replay them.
// Only forward to renderer after did-finish-load to avoid stacking
// executeJavaScript listeners (which causes MaxListenersExceededWarning).
const startupLogs = [];
let _rendererReady = false;

function log(msg) {
  const line = `[Main] ${msg}`;
  console.log(line);
  startupLogs.push({ level: 'log', message: line });
  // Forward to renderer only after page has finished loading
  if (_rendererReady && mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed()) {
    mainWindow.webContents.executeJavaScript(
      `console.log(${JSON.stringify(line)})`
    ).catch(() => {});
  }
}

function logError(msg) {
  const line = `[Main] ${msg}`;
  console.error(line);
  startupLogs.push({ level: 'error', message: line });
  if (_rendererReady && mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed()) {
    mainWindow.webContents.executeJavaScript(
      `console.error(${JSON.stringify(line)})`
    ).catch(() => {});
  }
}

/**
 * Determine whether we are running inside a packaged (asar) app.
 */
function isPackaged() {
  return app.isPackaged;
}

/**
 * Find the embedded Python binary.
 * On macOS/Linux the layout is python/bin/python3.12
 * On Windows the layout is python/python.exe
 */
function findPython() {
  const isWin = process.platform === 'win32';
  const relativePath = isWin
    ? path.join('python', 'python.exe')
    : path.join('python', 'bin', 'python3.12');

  const possibilities = [
    // In packaged app – extraResources land under process.resourcesPath
    path.join(process.resourcesPath, relativePath),
    // In development – relative to project root
    path.join(__dirname, relativePath),
  ];
  for (const p of possibilities) {
    log(`Checking for Python at: ${p}`);
    if (fs.existsSync(p)) {
      log(`Found Python at: ${p}`);
      return p;
    }
  }
  logError(`Could not find embedded Python, checked: ${possibilities.join(', ')}`);
  return null;
}

/**
 * Find server.py – in a packaged app it lives in extraResources,
 * in development it is next to main.js.
 */
function findServerScript() {
  const possibilities = [
    // Packaged: extraResources copies server.py to resources/server.py
    path.join(process.resourcesPath, 'server.py'),
    // Development
    path.join(__dirname, 'server.py'),
  ];
  for (const p of possibilities) {
    log(`Checking for server.py at: ${p}`);
    if (fs.existsSync(p)) {
      log(`Found server.py at: ${p}`);
      return p;
    }
  }
  logError(`Could not find server.py, checked: ${possibilities.join(', ')}`);
  return null;
}

/**
 * Find the server/ package directory (needed on PYTHONPATH so
 * "from server.app import create_app" works).
 */
function findServerPackageDir() {
  const possibilities = [
    // Packaged: extraResources
    process.resourcesPath,
    // Development
    __dirname,
  ];
  for (const p of possibilities) {
    const serverInit = path.join(p, 'server', '__init__.py');
    if (fs.existsSync(serverInit)) {
      log(`Found server package in: ${p}`);
      return p;
    }
  }
  logError('Could not find server/ package directory');
  return null;
}

let mainWindow;
let pythonProcess;
let serverPort = 5080; // Will be updated to an available port

const DEFAULT_PORT = 5080;

/**
 * Check if a port is available by attempting to create a server on it.
 * @param {number} port - The port to check
 * @returns {Promise<boolean>} True if the port is available
 */
function isPortAvailable(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once('error', () => resolve(false));
    server.once('listening', () => {
      server.close(() => resolve(true));
    });
    server.listen(port, '127.0.0.1');
  });
}

/**
 * Find an available port starting from the given port.
 * Increments by 1 until an available port is found.
 * @param {number} startPort - The port to start checking from
 * @returns {Promise<number>} The first available port
 */
async function findAvailablePort(startPort) {
  let port = startPort;
  while (port < startPort + 100) { // Check up to 100 ports
    if (await isPortAvailable(port)) {
      return port;
    }
    log(`Port ${port} is in use, trying ${port + 1}...`);
    port++;
  }
  throw new Error(`No available port found in range ${startPort}-${startPort + 99}`);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    icon: path.join(__dirname, 'resources', 'icons', 'icon.png'),
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
  });

  mainWindow.loadFile('index.html');

  // Open DevTools to see errors (remove this line for production)
  // mainWindow.webContents.openDevTools();

  // Replay any startup logs that were collected before the window opened,
  // and communicate the server port to the renderer.
  mainWindow.webContents.on('did-finish-load', () => {
    // Set the dynamic server port in the renderer
    mainWindow.webContents.executeJavaScript(
      `if (typeof setServerPort === 'function') { setServerPort(${serverPort}); }`
    ).catch(() => {});

    // Log the localStorage file path so users can find it
    const userDataPath = app.getPath('userData');
    const localStoragePath = path.join(userDataPath, 'Local Storage', 'leveldb');
    mainWindow.webContents.executeJavaScript(
      `console.log('[Main] Electron userData path: ${userDataPath.replace(/\\/g, '\\\\')}');` +
      `console.log('[Main] localStorage stored in: ${localStoragePath.replace(/\\/g, '\\\\')}');`
    ).catch(() => {});

    for (const entry of startupLogs) {
      const fn = entry.level === 'error' ? 'console.error' : 'console.log';
      mainWindow.webContents.executeJavaScript(
        `${fn}(${JSON.stringify(entry.message)})`
      ).catch(() => {});
    }

    _rendererReady = true;
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
    if (pythonProcess) {
      pythonProcess.kill();
    }
  });

  // Open external links in default browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http')) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });
}

function startPythonServer() {
  return new Promise((resolve, reject) => {
    const pythonCmd = findPython();
    if (!pythonCmd) {
      return reject(new Error('Python binary not found'));
    }

    const serverPath = findServerScript();
    if (!serverPath) {
      return reject(new Error('server.py not found'));
    }

    const serverPkgDir = findServerPackageDir();

    // Build the Python environment so the embedded interpreter can find
    // its own standard library, site-packages, and the server/ package.
    // On macOS/Linux the binary is at python/bin/python3.12 → pythonDir = python/
    // On Windows the binary is at python/python.exe       → pythonDir = python/
    const isWin = process.platform === 'win32';
    const pythonDir = isWin
      ? path.dirname(pythonCmd)            // …/python
      : path.dirname(path.dirname(pythonCmd)); // …/python
    const pythonLibDir = isWin
      ? path.join(pythonDir, 'Lib')        // Windows: python/Lib
      : path.join(pythonDir, 'lib', 'python3.12'); // macOS/Linux: python/lib/python3.12
    const sitePackagesDir = path.join(pythonLibDir, 'site-packages');

    const env = Object.assign({}, process.env);

    // PYTHONHOME tells the embedded Python where its prefix is
    env.PYTHONHOME = pythonDir;

    // PYTHONPATH: include site-packages + the directory containing server/
    const pythonPathParts = [sitePackagesDir];
    if (serverPkgDir) {
      pythonPathParts.push(serverPkgDir);
    }
    env.PYTHONPATH = pythonPathParts.join(path.delimiter);

    // Prevent Python from trying to write .pyc files (may fail in read-only locations)
    env.PYTHONDONTWRITEBYTECODE = '1';

    log(`Starting Python server: ${pythonCmd} ${serverPath}`);
    log(`PYTHONHOME=${env.PYTHONHOME}`);
    log(`PYTHONPATH=${env.PYTHONPATH}`);
    log(`CWD for server: ${serverPkgDir || __dirname}`);

    pythonProcess = spawn(pythonCmd, ['-u', serverPath, '--port', String(serverPort)], {
      detached: false,
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
      cwd: serverPkgDir || __dirname,
      env: env,
    });

    let resolved = false;

    pythonProcess.stdout.on('data', (data) => {
      const output = data.toString().trim();
      if (output) {
        log(`[Python stdout] ${output}`);
      }
    });

    pythonProcess.stderr.on('data', (data) => {
      const output = data.toString().trim();
      if (output) {
        logError(`[Python stderr] ${output}`);
      }
    });

    pythonProcess.on('error', (error) => {
      logError(`Failed to start Python process: ${error.message}`);
      if (!resolved) {
        resolved = true;
        reject(error);
      }
    });

    pythonProcess.on('close', (code) => {
      log(`Python server exited with code ${code}`);
    });

    // Resolve immediately – we poll for readiness separately
    resolve();
  });
}

// Check if server is ready
function waitForServer(maxAttempts = 50) {
  return new Promise((resolve, reject) => {
    let attempts = 0;

    const checkServer = () => {
      attempts++;

      const req = http.get(`http://127.0.0.1:${serverPort}/health`, (res) => {
        if (res.statusCode === 200) {
          log('Python server is ready!');
          resolve();
        } else {
          log(`Health check attempt ${attempts}: status ${res.statusCode}`);
          if (attempts < maxAttempts) {
            setTimeout(checkServer, 200);
          } else {
            reject(new Error(`Server returned status ${res.statusCode}`));
          }
        }
      });

      req.on('error', (err) => {
        if (attempts < maxAttempts) {
          setTimeout(checkServer, 200);
        } else {
          reject(new Error(`Failed to connect to server after ${maxAttempts} attempts: ${err.message}`));
        }
      });

      req.setTimeout(1000, () => {
        req.destroy();
        if (attempts < maxAttempts) {
          setTimeout(checkServer, 200);
        } else {
          reject(new Error('Connection timeout'));
        }
      });
    };

    // Give the server a moment to start before checking
    setTimeout(checkServer, 500);
  });
}

app.whenReady().then(async () => {
  try {
    log(`App is packaged: ${isPackaged()}`);
    log(`__dirname: ${__dirname}`);
    log(`resourcesPath: ${process.resourcesPath}`);

    // Find an available port starting from the default
    serverPort = await findAvailablePort(DEFAULT_PORT);
    log(`Using port ${serverPort} for Python server`);

    // Start Python server (non-blocking)
    await startPythonServer();

    // Wait for server to be ready
    await waitForServer();

    // Now create the window
    createWindow();
    log('Application started successfully!');
  } catch (error) {
    logError(`Failed to start application: ${error.message}`);
    // Create window anyway to show error
    createWindow();
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (pythonProcess) {
    pythonProcess.kill();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Handle IPC messages from renderer
ipcMain.handle('execute-code', async (event, code) => {
  // The frontend will directly communicate with the Python server via HTTP
  // This is just a placeholder for any Electron-native operations if needed
  return { success: true };
});

// ── Workspace folder dialogs (native OS) ────────────────────────

/**
 * Open an existing folder using the native OS file picker.
 * Returns the selected folder path, or null if cancelled.
 */
ipcMain.handle('dialog:openFolder', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: 'Open Workspace Folder',
    properties: ['openDirectory', 'createDirectory'],
    buttonLabel: 'Open',
  });
  if (result.canceled || result.filePaths.length === 0) return null;
  return result.filePaths[0];
});

/**
 * Create a new folder using the native OS save dialog.
 * The user picks a location and types a folder name.
 * Returns the created folder path, or null if cancelled.
 */
ipcMain.handle('dialog:createFolder', async () => {
  const result = await dialog.showSaveDialog(mainWindow, {
    title: 'Create New Workspace Folder',
    buttonLabel: 'Create',
    nameFieldLabel: 'Workspace Name',
    showsTagField: false,
  });
  if (result.canceled || !result.filePath) return null;

  // Create the folder if it doesn't exist
  const folderPath = result.filePath;
  if (!fs.existsSync(folderPath)) {
    fs.mkdirSync(folderPath, { recursive: true });
    log(`Created workspace folder: ${folderPath}`);
  }
  return folderPath;
});