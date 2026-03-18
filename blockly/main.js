const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');

// Collect startup logs before the window is created so we can replay them
const startupLogs = [];

function log(msg) {
  const line = `[Main] ${msg}`;
  console.log(line);
  startupLogs.push({ level: 'log', message: line });
  // Forward to renderer if window is already open
  if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed()) {
    mainWindow.webContents.executeJavaScript(
      `console.log(${JSON.stringify(line)})`
    ).catch(() => {});
  }
}

function logError(msg) {
  const line = `[Main] ${msg}`;
  console.error(line);
  startupLogs.push({ level: 'error', message: line });
  if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed()) {
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
 */
function findPython() {
  const possibilities = [
    // In packaged app – extraResources land under process.resourcesPath
    path.join(process.resourcesPath, 'python', 'bin', 'python3.12'),
    // In development – relative to project root
    path.join(__dirname, 'python', 'bin', 'python3.12'),
  ];
  for (const p of possibilities) {
    log(`Checking for Python at: ${p}`);
    if (fs.existsSync(p)) {
      log(`Found Python at: ${p}`);
      return p;
    }
  }
  logError(`Could not find python3.12, checked: ${possibilities.join(', ')}`);
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

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
  });

  mainWindow.loadFile('index.html');

  // Open DevTools to see errors (remove this line for production)
  mainWindow.webContents.openDevTools();

  // Replay any startup logs that were collected before the window opened
  mainWindow.webContents.on('did-finish-load', () => {
    for (const entry of startupLogs) {
      const fn = entry.level === 'error' ? 'console.error' : 'console.log';
      mainWindow.webContents.executeJavaScript(
        `${fn}(${JSON.stringify(entry.message)})`
      ).catch(() => {});
    }
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
    const pythonDir = path.dirname(path.dirname(pythonCmd)); // …/python
    const pythonLibDir = path.join(pythonDir, 'lib', 'python3.12');
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

    pythonProcess = spawn(pythonCmd, ['-u', serverPath], {
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

      const req = http.get('http://127.0.0.1:5080/health', (res) => {
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