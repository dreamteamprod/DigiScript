/**
 * Electron Main Process
 *
 * Handles window creation, IPC communication, and app lifecycle.
 */

import { app, BrowserWindow, ipcMain } from 'electron';
import path from 'path';
import url from 'url';
import { fileURLToPath } from 'url';

// ESM equivalent of __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Services
import ConnectionManager from './services/ConnectionManager.js';
import VersionChecker from './services/VersionChecker.js';
import MDNSDiscovery from './services/MDNSDiscovery.js';

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
      preload: path.join(__dirname, 'preload.cjs'),
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
    // Production: Load built files from client/dist-electron (Electron-specific build)
    // In packaged app, extraResource files are in process.resourcesPath
    const staticPath = app.isPackaged
      ? path.join(process.resourcesPath, 'dist-electron')
      : path.join(__dirname, '../client/dist-electron');

    mainWindow.loadURL(
      url.format({
        pathname: path.join(staticPath, 'index.html'),
        protocol: 'file:',
        slashes: true,
      })
    );
  }

  // Show window when ready to avoid flicker
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Enable DevTools with keyboard shortcut (Cmd/Ctrl+Shift+I) in production
  mainWindow.webContents.on('before-input-event', (event, input) => {
    if (input.key === 'I' && input.shift && (input.meta || input.control)) {
      mainWindow.webContents.toggleDevTools();
    }
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

  ipcMain.handle('connections:clearActive', async () => {
    return connectionManager.clearActiveConnection();
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
