/**
 * Electron Preload Script
 *
 * Safely exposes IPC methods to the renderer process via contextBridge.
 * This creates the window.electronAPI interface used by the platform layer.
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

  // Server URL (synchronous for platform layer compatibility)
  getServerURLSync: () => ipcRenderer.sendSync('server:getURLSync'),

  // Storage operations (for Vuex persistence)
  storageGet: (key) => ipcRenderer.invoke('storage:get', key),
  storageSet: (key, value) => ipcRenderer.invoke('storage:set', key, value),
  storageDelete: (key) => ipcRenderer.invoke('storage:delete', key),
  storageClear: () => ipcRenderer.invoke('storage:clear'),

  // App information
  getAppVersion: () => ipcRenderer.invoke('app:getVersion'),

  // Future: Version checking (Phase 3)
  checkVersion: (serverUrl) => ipcRenderer.invoke('version:check', serverUrl),

  // Future: mDNS discovery (Phase 3)
  discoverServers: () => ipcRenderer.invoke('mdns:discover'),
});
