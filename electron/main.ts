import { app, BrowserWindow, ipcMain } from 'electron';
import path from 'path';
import url from 'url';
import { fileURLToPath } from 'url';

// ESM equivalent of __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

import ConnectionManager from './services/ConnectionManager.js';
import VersionChecker from './services/VersionChecker.js';
import MDNSDiscovery from './services/MDNSDiscovery.js';

const isDev = process.argv.includes('--dev') || process.env.NODE_ENV === 'development';

let connectionManager: ConnectionManager;

function createWindow(): void {
  const win = new BrowserWindow({
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
    show: false,
  });

  if (isDev) {
    win.loadURL('http://localhost:5173');
    win.webContents.openDevTools();
  } else {
    const staticPath = app.isPackaged
      ? path.join(process.resourcesPath, 'dist-electron')
      : path.join(__dirname, '../client/dist-electron');

    win.loadURL(
      url.format({
        pathname: path.join(staticPath, 'index.html'),
        protocol: 'file:',
        slashes: true,
      })
    );
  }

  win.once('ready-to-show', () => {
    win.show();
  });

  // Enable DevTools with keyboard shortcut (Cmd/Ctrl+Shift+I) in production
  win.webContents.on('before-input-event', (event, input) => {
    if (input.key === 'I' && input.shift && (input.meta || input.control)) {
      win.webContents.toggleDevTools();
    }
  });
}

function registerIPCHandlers(): void {
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

  ipcMain.on('server:getURLSync', (event) => {
    const activeConnection = connectionManager.getActiveConnection();
    event.returnValue = activeConnection ? activeConnection.url : null;
  });

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

  ipcMain.handle('app:getVersion', async () => {
    return app.getVersion();
  });

  ipcMain.handle('version:check', async (event, serverUrl) => {
    const clientVersion = app.getVersion();
    return VersionChecker.checkVersion(serverUrl, clientVersion);
  });

  ipcMain.handle('mdns:discover', async (event, timeout = 5000) => {
    return MDNSDiscovery.discoverServers(timeout);
  });

  ipcMain.handle('mdns:discoverWithVersionCheck', async (event, timeout = 5000) => {
    const clientVersion = app.getVersion();
    return MDNSDiscovery.discoverServersWithVersionCheck(clientVersion, timeout);
  });
}

app.whenReady().then(() => {
  connectionManager = new ConnectionManager();
  registerIPCHandlers();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled rejection at:', promise, 'reason:', reason);
});
