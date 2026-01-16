/**
 * Electron Main Process
 *
 * Handles window creation, IPC communication, and app lifecycle.
 */

const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const url = require('url');

// Services
const ConnectionManager = require('./services/ConnectionManager');
const VersionChecker = require('./services/VersionChecker');
const MDNSDiscovery = require('./services/MDNSDiscovery');

// Determine if running in development mode
const isDev = process.argv.includes('--dev') || process.env.NODE_ENV === 'development';

// Keep a global reference of the window object
let mainWindow;

// Initialize services
let connectionManager;

/**
 * Create the main browser window
 */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    },
    show: false, // Don't show until ready
  });

  // Load the appropriate URL
  if (isDev) {
    // Development: Load from Vite dev server
    mainWindow.loadURL('http://localhost:5173');

    // Open DevTools in development
    mainWindow.webContents.openDevTools();
  } else {
    // Production: Load built files
    mainWindow.loadURL(
      url.format({
        pathname: path.join(__dirname, '../client/dist/index.html'),
        protocol: 'file:',
        slashes: true,
      })
    );
  }

  // Show window when ready to avoid flicker
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Emitted when the window is closed
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

/**
 * Register IPC handlers for renderer communication
 */
function registerIPCHandlers() {
  // Connection management
  ipcMain.handle('connections:getAll', async () => {
    return connectionManager.getAllConnections();
  });

  ipcMain.handle('connections:add', async (event, connection) => {
    return connectionManager.addConnection(connection);
  });

  ipcMain.handle('connections:update', async (event, id, updates) => {
    return connectionManager.updateConnection(id, updates);
  });

  ipcMain.handle('connections:delete', async (event, id) => {
    return connectionManager.deleteConnection(id);
  });

  ipcMain.handle('connections:getActive', async () => {
    return connectionManager.getActiveConnection();
  });

  ipcMain.handle('connections:setActive', async (event, id) => {
    return connectionManager.setActiveConnection(id);
  });

  // Server URL synchronous getter (for platform layer)
  ipcMain.on('server:getURLSync', (event) => {
    const activeConnection = connectionManager.getActiveConnection();
    event.returnValue = activeConnection ? activeConnection.url : null;
  });

  // Storage operations (for platform layer)
  ipcMain.handle('storage:get', async (event, key) => {
    return connectionManager.getStorageItem(key);
  });

  ipcMain.handle('storage:set', async (event, key, value) => {
    return connectionManager.setStorageItem(key, value);
  });

  ipcMain.handle('storage:delete', async (event, key) => {
    return connectionManager.deleteStorageItem(key);
  });

  ipcMain.handle('storage:clear', async () => {
    return connectionManager.clearStorage();
  });

  // App information
  ipcMain.handle('app:getVersion', async () => {
    return app.getVersion();
  });

  // Version checking
  ipcMain.handle('version:check', async (event, serverUrl) => {
    const clientVersion = app.getVersion();
    return VersionChecker.checkVersion(serverUrl, clientVersion);
  });

  // mDNS discovery
  ipcMain.handle('mdns:discover', async (event, timeout = 5000) => {
    return MDNSDiscovery.discoverServers(timeout);
  });

  ipcMain.handle('mdns:discoverWithVersionCheck', async (event, timeout = 5000) => {
    const clientVersion = app.getVersion();
    return MDNSDiscovery.discoverServersWithVersionCheck(clientVersion, timeout);
  });
}

// App lifecycle events
app.whenReady().then(() => {
  // Initialize services
  connectionManager = new ConnectionManager();

  // Register IPC handlers
  registerIPCHandlers();

  // Create window
  createWindow();

  app.on('activate', () => {
    // On macOS, re-create window when dock icon is clicked and no windows open
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Quit when all windows are closed (except on macOS)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Handle app errors
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled rejection at:', promise, 'reason:', reason);
});
