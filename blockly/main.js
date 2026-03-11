const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

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

  // Open DevTools in development to see errors
  mainWindow.webContents.openDevTools();

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
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    const serverPath = path.join(__dirname, 'server.py');

    console.log(`Starting Python server: ${pythonCmd} ${serverPath}`);

    pythonProcess = spawn(pythonCmd, [serverPath], {
      detached: false,
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe']
    });

    let resolved = false;

    pythonProcess.stdout.on('data', (data) => {
      const output = data.toString().trim();
      if (output) {
        console.log(`[Python Server] ${output}`);
      }
    });

    pythonProcess.stderr.on('data', (data) => {
      const output = data.toString().trim();
      if (output) {
        console.error(`[Python Server Error] ${output}`);
      }
    });

    pythonProcess.on('error', (error) => {
      console.error(`Failed to start Python server: ${error.message}`);
      if (!resolved) {
        resolved = true;
        reject(error);
      }
    });

    pythonProcess.on('close', (code) => {
      console.log(`Python server exited with code ${code}`);
    });

    // Resolve immediately - we'll check server readiness separately
    resolve();
  });
}

// Check if server is ready
function waitForServer(maxAttempts = 50) {
  return new Promise((resolve, reject) => {
    let attempts = 0;

    const checkServer = () => {
      attempts++;

      const req = http.get('http://127.0.0.1:5000/health', (res) => {
        if (res.statusCode === 200) {
          console.log('Python server is ready!');
          resolve();
        } else {
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
          reject(new Error(`Failed to connect to server: ${err.message}`));
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
    // Start Python server (non-blocking)
    await startPythonServer();

    // Wait for server to be ready
    await waitForServer();

    // Now create the window
    createWindow();
  } catch (error) {
    console.error('Failed to start application:', error);
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