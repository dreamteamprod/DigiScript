/**
 * Electron Preload Script
 *
 * Safely exposes IPC methods to the renderer process via contextBridge.
 * This creates the window.electronAPI interface used by the platform layer.
 *
 * Note: Preload scripts must use CommonJS when sandbox is enabled, as they run
 * in a special isolated context that doesn't support native ES modules.
 */

const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods to the renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  // Connection management
  getAllConnections: () => ipcRenderer.invoke('connections:getAll'),
  addConnection: (connection) => ipcRenderer.invoke('connections:add', connection),
  updateConnection: (id, updates) => ipcRenderer.invoke('connections:update', id, updates),
  deleteConnection: (id) => ipcRenderer.invoke('connections:delete', id),
  getActiveConnection: () => ipcRenderer.invoke('connections:getActive'),
  setActiveConnection: (id) => ipcRenderer.invoke('connections:setActive', id),
  clearActiveConnection: () => ipcRenderer.invoke('connections:clearActive'),

  // Server URL (synchronous for platform layer compatibility)
  getServerURLSync: () => ipcRenderer.sendSync('server:getURLSync'),

  // Storage operations (for Vuex persistence)
  storageGet: (key) => ipcRenderer.invoke('storage:get', key),
  storageSet: (key, value) => ipcRenderer.invoke('storage:set', key, value),
  storageDelete: (key) => ipcRenderer.invoke('storage:delete', key),
  storageClear: () => ipcRenderer.invoke('storage:clear'),

  // App information
  getAppVersion: () => ipcRenderer.invoke('app:getVersion'),

  // Version checking
  checkVersion: (serverUrl) => ipcRenderer.invoke('version:check', serverUrl),

  // mDNS discovery
  discoverServers: (timeout) => ipcRenderer.invoke('mdns:discover', timeout),
  discoverServersWithVersionCheck: (timeout) =>
    ipcRenderer.invoke('mdns:discoverWithVersionCheck', timeout),
});
