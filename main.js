const { app, BrowserWindow, session, desktopCapturer } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const os = require('os');

let mainWindow;
let pythonProcess;

function getPythonExecutablePath() {
  const isWindows = os.platform() === 'win32';
  return isWindows
    ? path.join(__dirname, 'venv', 'Scripts', 'python.exe')
    : path.join(__dirname, 'venv', 'bin', 'python');
}

function startBackend() {
  const pythonPath = getPythonExecutablePath();
  pythonProcess = spawn(pythonPath, ['backend/app.py']);

  pythonProcess.stdout.on('data', (data) => console.log(`[FastAPI Output]: ${data.toString()}`));
  pythonProcess.stderr.on('data', (data) => console.error(`[FastAPI Error]: ${data.toString()}`));
  pythonProcess.on('close', (code) => console.log(`FastAPI process exited with code ${code}`));
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  // Enable getDisplayMedia in Electron Renderer Process
  session.defaultSession.setDisplayMediaRequestHandler((request, callback) => {
    desktopCapturer.getSources({ types: ['screen', 'window'] }).then((sources) => {
      // Automatically select the primary full desktop screen
      callback({ video: sources[0] });
    });
  });

  // Grant microphone and screen capture permission requests automatically
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    const allowedPermissions = ['media', 'audioCapture', 'display-capture'];
    if (allowedPermissions.includes(permission)) {
      callback(true);
    } else {
      callback(false);
    }
  });

  const startUrl = process.env.ELECTRON_START_URL || 'http://localhost:5173';
  mainWindow.loadURL(startUrl);
}

app.whenReady().then(() => {
  startBackend();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (pythonProcess) pythonProcess.kill();
  if (process.platform !== 'darwin') app.quit();
});